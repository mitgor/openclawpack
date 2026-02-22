# Phase 3: Reliability - Research

**Researched:** 2026-02-22
**Domain:** Retry logic, session continuity, output formatting, cost/token tracking
**Confidence:** HIGH

## Summary

Phase 3 adds four reliability capabilities to openclawpack: (1) retry logic with exponential backoff for transient failures and rate limits, (2) session ID capture and resume for multi-step workflows, (3) a `--output-format text` flag for human-readable output, and (4) token count and estimated cost in every command response's usage metadata.

The most significant finding is that the **Claude Agent SDK already provides all the primitives** needed for this phase. `ResultMessage` includes `session_id`, `total_cost_usd`, `usage` (with token counts), `duration_ms`, and `duration_api_ms`. `ClaudeAgentOptions` has `resume: str | None` for session resumption and `fork_session: bool` for branching. The SDK's typed exception hierarchy (`ProcessError`, `CLIConnectionError`) plus the `AssistantMessage.error` field (which includes a `"rate_limit"` literal type) provide the signals needed to decide whether to retry. Retry logic should be built at the transport adapter layer (`ClaudeTransport.run()`) rather than hand-rolling retry loops in every workflow function.

For retry implementation, the standard approach is **not** to add a new dependency like tenacity, since the project's dependency philosophy is minimal (PKG-03). Instead, a simple retry loop with exponential backoff + jitter can be implemented in ~40 lines inside the transport adapter. The retry should be error-type-aware: rate limits and connection errors are retryable; CLINotFound and JSONDecodeError are not.

For the text output format, a `CommandResult.to_text()` method and a CLI-level `--output-format` flag will format results as human-readable text. This is a thin formatting layer -- no new dependencies required.

**Primary recommendation:** Add retry logic inside `ClaudeTransport.run()` with configurable retry policy in `TransportConfig`. Capture and propagate `session_id` through `CommandResult` for resume. Enrich `usage` metadata with `total_cost_usd` from `ResultMessage`. Add `--output-format text|json` CLI flag with `CommandResult.to_text()` formatter.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRNS-05 | Retry logic with exponential backoff handles rate limits and transient subprocess failures | SDK provides `ProcessError` (with exit_code/stderr), `CLIConnectionError`, and `AssistantMessage.error` with `"rate_limit"` literal. Retry wrapper in `ClaudeTransport.run()` classifies errors as retryable vs. fatal, applies exponential backoff with jitter. `TransportConfig` gains `max_retries` and `retry_base_delay` fields. |
| TRNS-06 | Session ID captured from Claude output and reusable across commands via --resume flag | `ResultMessage.session_id` is already captured into `CommandResult.session_id`. SDK's `ClaudeAgentOptions.resume` accepts a session ID string. Transport adapter adds `resume_session_id` kwarg. CLI adds `--resume` flag. Workflow functions accept and forward `resume_session_id`. |
| OUT-03 | `--output-format` flag supports `json` (default) and `text` (human-readable) | CLI adds `--output-format` option (Typer `Annotated[str, Option]`). `CommandResult.to_text()` formats fields as human-readable lines. `_output()` helper dispatches based on format. No new dependencies needed. |
| OUT-04 | Usage metadata includes token count and estimated cost per command invocation | `ResultMessage` already provides `usage: dict` (with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`) and `total_cost_usd: float`. Currently `CommandResult.usage` stores the raw SDK usage dict. Enhancement: always include `total_cost_usd` in the usage dict, and add a `cost_usd` top-level field or ensure `usage` always contains `{"input_tokens": N, "output_tokens": N, "total_cost_usd": X}`. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| claude-agent-sdk | >=0.1.39 | Session resume, usage/cost metadata, error types for retry classification | Already a dependency. Provides `resume` option, `ResultMessage.total_cost_usd`, `ResultMessage.usage`, typed errors for retry decisions. |
| pydantic | >=2.12 | CommandResult model extension | Already a dependency. `to_text()` method, usage metadata enrichment. |
| typer | >=0.24 | `--output-format` and `--resume` CLI flags | Already a dependency. |

### Supporting

No new dependencies required. All Phase 3 features are implemented using existing dependencies.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled retry loop | `tenacity` library | Tenacity is mature and full-featured, but adds a dependency for ~40 lines of retry logic. Project policy (PKG-03) prefers minimal dependencies. Hand-rolled is sufficient for the narrow retry scope (single `run()` call, 3 error types). |
| `CommandResult.to_text()` method | `rich` library for formatted output | Rich produces beautiful terminal output but adds a heavy dependency. Simple string formatting is sufficient for agent consumption. |
| Enriching `usage` dict in CommandResult | Separate `CostInfo` Pydantic model | Over-engineering for a flat dict with 3-5 fields. Keep it simple -- enrich the existing dict. |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Changes to Project Structure

```
src/openclawpack/
├── transport/
│   ├── client.py         # Add retry wrapper around sdk_query() loop
│   ├── types.py          # Add retry config fields to TransportConfig
│   ├── errors.py         # Add RateLimitError subclass, is_retryable() helper
│   └── retry.py          # NEW: Retry policy, backoff calculator, retry decorator
├── output/
│   ├── schema.py         # Add to_text() method, enrich usage with cost
│   └── formatter.py      # NEW: Text formatter for CommandResult
├── commands/
│   ├── engine.py         # Forward resume_session_id through WorkflowEngine
│   ├── new_project.py    # Accept and return session_id for chaining
│   ├── plan_phase.py     # Accept resume_session_id parameter
│   └── execute_phase.py  # Accept resume_session_id parameter
└── cli.py                # Add --output-format and --resume flags
```

### Pattern 1: Transport-Level Retry with Error Classification

**What:** Retry logic lives inside `ClaudeTransport.run()`, wrapping the SDK call. Errors are classified as retryable or fatal before deciding whether to retry.

**When to use:** TRNS-05 -- all retry logic.

**Why at transport level:** Every workflow (new-project, plan-phase, execute-phase) benefits from retry without duplicating retry loops. The transport adapter is the single chokepoint for all SDK calls.

**Example:**
```python
# src/openclawpack/transport/retry.py
import asyncio
import random
from dataclasses import dataclass

from openclawpack.transport.errors import (
    CLINotFound,
    ConnectionError_,
    JSONDecodeError,
    ProcessError,
    TransportError,
    TransportTimeout,
)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 2.0       # seconds
    max_delay: float = 60.0       # seconds
    jitter: float = 0.5           # 0.0 to 1.0, fraction of delay to randomize
    retryable_exit_codes: frozenset[int] = frozenset({1, 2})  # generic failures


def is_retryable(error: Exception) -> bool:
    """Classify whether an error is worth retrying.

    Retryable: rate limits, transient connection failures, generic process errors.
    Fatal: CLI not found, JSON decode errors, timeouts (already have their own timeout).
    """
    if isinstance(error, CLINotFound):
        return False  # Won't fix by retrying
    if isinstance(error, JSONDecodeError):
        return False  # Corrupt output won't self-heal
    if isinstance(error, TransportTimeout):
        return False  # Already waited the full timeout
    if isinstance(error, ConnectionError_):
        return True   # Transient connection issues
    if isinstance(error, ProcessError):
        return True   # Rate limits surface as process errors
    return False


def calculate_backoff(attempt: int, policy: RetryPolicy) -> float:
    """Exponential backoff with jitter."""
    delay = min(policy.base_delay * (2 ** attempt), policy.max_delay)
    jitter_range = delay * policy.jitter
    return delay + random.uniform(-jitter_range, jitter_range)
```

### Pattern 2: Session ID Passthrough

**What:** `CommandResult.session_id` is returned from every command. Subsequent commands accept a `--resume <session_id>` flag that is forwarded through the workflow engine to the transport layer, which sets `ClaudeAgentOptions.resume`.

**When to use:** TRNS-06 -- session continuity.

**Data flow:**
```
CLI --resume <id>
  -> workflow function(resume_session_id=id)
    -> WorkflowEngine.run_gsd_command(resume_session_id=id)
      -> ClaudeTransport.run(resume_session_id=id)
        -> ClaudeAgentOptions(resume=id)
          -> SDK subprocess --resume <id>
```

**Example:**
```python
# In ClaudeTransport.run(), add resume support:
async def run(self, prompt: str, **kwargs) -> CommandResult:
    resume_session_id = kwargs.pop("resume_session_id", None)
    # ... existing option building ...
    if resume_session_id is not None:
        options.resume = resume_session_id
    # ... rest of existing code ...
```

### Pattern 3: Output Format Dispatch

**What:** CLI-level `--output-format` flag selects between JSON (default) and text output. The `_output()` helper in `cli.py` dispatches based on the format string.

**When to use:** OUT-03 -- human-readable output.

**Example:**
```python
# src/openclawpack/output/formatter.py
from openclawpack.output.schema import CommandResult


def format_text(result: CommandResult) -> str:
    """Format a CommandResult as human-readable text."""
    lines = []
    status = "SUCCESS" if result.success else "FAILED"
    lines.append(f"Status: {status}")

    if result.result:
        lines.append(f"Result: {result.result}")

    if result.errors:
        for err in result.errors:
            lines.append(f"Error: {err}")

    if result.session_id:
        lines.append(f"Session: {result.session_id}")

    if result.usage:
        input_tokens = result.usage.get("input_tokens", 0)
        output_tokens = result.usage.get("output_tokens", 0)
        cost = result.usage.get("total_cost_usd")
        lines.append(f"Tokens: {input_tokens} in / {output_tokens} out")
        if cost is not None:
            lines.append(f"Cost: ${cost:.4f}")

    if result.duration_ms:
        lines.append(f"Duration: {result.duration_ms}ms")

    return "\n".join(lines)
```

### Pattern 4: Usage Metadata Enrichment

**What:** The transport adapter enriches `CommandResult.usage` with `total_cost_usd` from `ResultMessage.total_cost_usd`. The usage dict always includes token counts and cost.

**When to use:** OUT-04 -- cost tracking.

**Example:**
```python
# In ClaudeTransport.run(), enrich usage before returning:
usage = result_message.usage or {}
if result_message.total_cost_usd is not None:
    usage["total_cost_usd"] = result_message.total_cost_usd
usage.setdefault("input_tokens", 0)
usage.setdefault("output_tokens", 0)

return CommandResult(
    success=not result_message.is_error,
    result=result_message.result,
    errors=[result_message.result] if result_message.is_error else [],
    session_id=result_message.session_id,
    usage=usage,
    duration_ms=result_message.duration_ms,
)
```

### Anti-Patterns to Avoid

- **Retrying in every workflow function:** Retry once, at the transport layer. Workflow functions should NOT have their own retry loops -- that creates nested retries with unpredictable backoff.
- **Retrying CLINotFound errors:** If Claude Code CLI is not installed, no amount of retrying will fix it. Always classify errors before retrying.
- **Retrying without jitter:** Pure exponential backoff causes "thundering herd" when multiple clients hit rate limits simultaneously. Always add randomized jitter.
- **Retrying timeouts:** If a command timed out at 600 seconds, retrying will just wait another 600 seconds. Timeouts should NOT be retryable.
- **Storing session IDs in the transport config:** Session IDs are per-call, not per-config. Pass them as kwargs to `run()`, not in `TransportConfig`.
- **Adding `total_cost_usd` as a separate `CommandResult` field:** Keep cost inside `usage` dict to avoid breaking the established schema. Agents already parse `usage`.
- **Using tenacity decorator on `async for` generators:** Tenacity does not natively support retrying async generators. The retry must wrap the entire `sdk_query()` iteration, not individual yields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session resume across commands | Custom session storage/replay | `ClaudeAgentOptions.resume` + session ID passthrough | SDK handles all session state restoration, history loading, and context management internally. |
| Token counting | Custom tokenizer or API token counter | `ResultMessage.usage` dict from SDK | SDK returns exact token counts from the API response. No estimation needed. |
| Cost estimation | Price lookup table with per-model rates | `ResultMessage.total_cost_usd` from SDK | SDK computes exact cost including cache tokens, model-specific pricing, and batch discounts. Already available in the result. |
| Subprocess error classification | Parsing stderr for "rate limit" strings | `AssistantMessage.error` literal type + `ProcessError.exit_code` | SDK provides typed error classification. The `error` field is a Literal union including `"rate_limit"`, `"server_error"`, `"billing_error"`. |
| Exponential backoff calculation | Complex scheduling library | Simple `min(base * 2^attempt, max) + jitter` formula | The backoff formula is 3 lines of code. No library needed for this narrow use case. |

**Key insight:** The SDK already computes and returns `total_cost_usd` and `usage` token counts. The biggest mistake would be trying to estimate costs from token counts using a pricing table -- the SDK's value is authoritative and includes cache credits, batch discounts, and model-specific rates that a lookup table would miss.

## Common Pitfalls

### Pitfall 1: Retrying Non-Retryable Errors
**What goes wrong:** System retries CLINotFound or JSONDecodeError, wasting time and confusing error messages.
**Why it happens:** Catch-all retry without error classification.
**How to avoid:** `is_retryable()` function that returns `False` for deterministic failures. Only retry transient errors (connection drops, rate limits, generic process failures).
**Warning signs:** Retry log shows "Retry 1/3... Retry 2/3... Retry 3/3..." followed by the same CLINotFound error.

### Pitfall 2: Exponential Backoff Without Jitter
**What goes wrong:** Multiple agents hit rate limits at the same time, all back off identically, and all retry at the same time, re-triggering the rate limit.
**Why it happens:** Pure `2^n` backoff is deterministic -- all clients compute the same delay.
**How to avoid:** Add `random.uniform(-jitter, +jitter)` to the backoff delay. Standard jitter range is 25-50% of the delay.
**Warning signs:** Log timestamps show retry attempts clustered at exact same time across multiple processes.

### Pitfall 3: Session Resume Without Error Handling
**What goes wrong:** Passing an expired or invalid session ID to `--resume` causes the SDK to fail with an opaque error instead of a clear "session not found" message.
**Why it happens:** Sessions are stored in `~/.claude/projects/` and can be cleaned up. Session IDs from previous days may no longer exist.
**How to avoid:** Catch errors from resume attempts and fall back to a fresh session with a clear warning message. Consider adding a `--resume-or-new` mode that silently falls back.
**Warning signs:** "ProcessError" with unhelpful stderr when using `--resume` with old session IDs.

### Pitfall 4: Not Including Cost in Usage for Local-Only Commands
**What goes wrong:** `openclawpack status` returns `usage: null` because it never calls the SDK. Consumers that always expect `usage.total_cost_usd` crash.
**Why it happens:** Status command reads local files, no API call, no ResultMessage.
**How to avoid:** For local-only commands (status), set `usage: {"input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}` instead of `None`. Or document that `usage` is `None` for local commands and consumers must handle it.
**Warning signs:** `KeyError: 'total_cost_usd'` in downstream agents.

### Pitfall 5: Breaking the JSON Schema with New Fields
**What goes wrong:** Adding a top-level `cost_usd` field to `CommandResult` breaks agents that validate against the existing schema.
**Why it happens:** Agents may have strict schema validation. Adding fields is usually safe with Pydantic (extra fields ignored by default), but removing or renaming fields is breaking.
**How to avoid:** Enrich existing `usage` dict rather than adding new top-level fields. Keep `CommandResult` schema additive-only. Document any new fields in usage.
**Warning signs:** Agents report schema validation errors after upgrade.

### Pitfall 6: Rate Limit Detection is Ambiguous
**What goes wrong:** Rate limits from the Anthropic API surface as SDK `ProcessError` with a non-zero exit code, not as a distinct error type. The `AssistantMessage.error = "rate_limit"` field is on individual messages within the stream, not on the final exception.
**Why it happens:** The SDK subprocess may receive a rate-limit response from the API, attempt its own internal retry, and eventually fail with a generic process error.
**How to avoid:** Check multiple signals: (1) `ProcessError.stderr` for "rate limit" text, (2) `AssistantMessage.error == "rate_limit"` during message iteration, (3) specific exit codes. Err on the side of retrying ambiguous process errors.
**Warning signs:** Rate-limited requests are not retried because the error is classified as fatal ProcessError.

## Code Examples

Verified patterns from official sources and codebase analysis:

### Retry Wrapper for Transport (TRNS-05)
```python
# src/openclawpack/transport/client.py - inside ClaudeTransport.run()
# Wrap the existing sdk_query() iteration in a retry loop.

import asyncio
import random
import logging

logger = logging.getLogger(__name__)

async def run(self, prompt: str, **kwargs) -> CommandResult:
    """Execute with retry on transient failures."""
    max_retries = kwargs.pop("max_retries", self.config.max_retries)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await self._run_once(prompt, **kwargs)
        except TransportError as e:
            last_error = e
            if not is_retryable(e) or attempt == max_retries:
                raise
            delay = calculate_backoff(attempt, self.config.retry_policy)
            logger.warning(
                "Transient error on attempt %d/%d, retrying in %.1fs: %s",
                attempt + 1, max_retries, delay, e,
            )
            await asyncio.sleep(delay)

    # Should not reach here, but safety net
    raise last_error  # type: ignore[misc]
```

### Session Resume via SDK (TRNS-06)
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/sessions
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# Step 1: Run command, capture session_id
session_id = None
async for message in query(
    prompt="/gsd:new-project --auto\n\nbuild a todo app",
    options=ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        setting_sources=["project"],
    ),
):
    if isinstance(message, ResultMessage):
        session_id = message.session_id

# Step 2: Resume same session for next command
async for message in query(
    prompt="/gsd:plan-phase 1",
    options=ClaudeAgentOptions(
        resume=session_id,        # Resume previous session
        permission_mode="bypassPermissions",
        setting_sources=["project"],
    ),
):
    if isinstance(message, ResultMessage):
        print(f"Cost: ${message.total_cost_usd}")
```

### Usage Metadata Enrichment (OUT-04)
```python
# In ClaudeTransport._run_once(), enrich the usage dict:
# Source: SDK ResultMessage dataclass fields

if result_message is None:
    raise ProcessError("No result message received from Claude Code")

# Build enriched usage dict
usage = dict(result_message.usage) if result_message.usage else {}
if result_message.total_cost_usd is not None:
    usage["total_cost_usd"] = result_message.total_cost_usd
# Ensure token counts always present
usage.setdefault("input_tokens", 0)
usage.setdefault("output_tokens", 0)

return CommandResult(
    success=not result_message.is_error,
    result=result_message.result,
    errors=[result_message.result] if result_message.is_error else [],
    session_id=result_message.session_id,
    usage=usage,
    duration_ms=result_message.duration_ms,
)
```

### Text Output Formatter (OUT-03)
```python
# src/openclawpack/output/formatter.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclawpack.output.schema import CommandResult


def format_text(result: CommandResult) -> str:
    """Format a CommandResult as human-readable text."""
    lines: list[str] = []
    lines.append(f"Status: {'SUCCESS' if result.success else 'FAILED'}")

    if result.result:
        # Truncate very long results for terminal readability
        text = str(result.result)
        if len(text) > 2000:
            text = text[:2000] + "\n... (truncated)"
        lines.append(f"\n{text}")

    if result.errors:
        lines.append("\nErrors:")
        for err in result.errors:
            lines.append(f"  - {err}")

    if result.session_id:
        lines.append(f"\nSession: {result.session_id}")

    if result.usage:
        in_tok = result.usage.get("input_tokens", 0)
        out_tok = result.usage.get("output_tokens", 0)
        cost = result.usage.get("total_cost_usd")
        lines.append(f"Tokens: {in_tok:,} input / {out_tok:,} output")
        if cost is not None:
            lines.append(f"Cost: ${cost:.4f}")

    lines.append(f"Duration: {result.duration_ms:,}ms")
    return "\n".join(lines)
```

### CLI --output-format and --resume Flags
```python
# In cli.py, modify the app callback and _output helper:

@app.callback()
def main(
    version: bool = ...,
    project_dir: Optional[str] = ...,
    verbose: bool = ...,
    quiet: bool = ...,
    output_format: str = typer.Option(
        "json",
        "--output-format",
        help="Output format: json (default) or text.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["output_format"] = output_format
    # ... existing ...


def _output(result: object, quiet: bool, output_format: str = "json") -> None:
    if quiet:
        return
    if output_format == "text":
        from openclawpack.output.formatter import format_text
        typer.echo(format_text(result))
    else:
        typer.echo(result.to_json())


# Each command adds --resume flag:
@app.command("plan-phase")
def plan_phase(
    phase: int = ...,
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume a previous session by session ID.",
    ),
    # ... existing options ...
) -> None:
    # Forward resume to workflow
    result = asyncio.run(
        plan_phase_workflow(
            phase=phase,
            resume_session_id=resume,
            # ... existing ...
        )
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No retry, manual re-run on failure | Transport-level retry with error classification | Standard practice in production API clients | Transient failures recovered automatically without user intervention |
| Custom cost estimation from token counts | SDK-provided `total_cost_usd` in ResultMessage | claude-agent-sdk v0.1.x (2025-2026) | Exact cost from the API, includes cache credits and model-specific rates |
| `query()` for every call (fresh session) | `ClaudeAgentOptions.resume` for session continuity | claude-agent-sdk v0.1.x (2025-2026) | Multi-step workflows maintain conversation context, reducing redundant context loading |
| `tenacity` library for retry | Hand-rolled retry for narrow scope | N/A (both valid) | For 1 retry site with 3 error types, hand-rolled is simpler. tenacity for >5 retry sites. |

**Deprecated/outdated:**
- `ClaudeAgentOptions.continue_conversation`: Continues the *most recent* conversation, not a specific one. Use `resume` with explicit session ID for deterministic behavior.
- `debug_stderr` field on `ClaudeAgentOptions`: Deprecated in favor of `stderr` callback. Already handled in Phase 2.1.

## Open Questions

1. **What does the `usage` dict structure look like exactly?**
   - What we know: `ResultMessage.usage` is `dict[str, Any] | None`. Based on Claude API documentation, it likely contains `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`.
   - What's unclear: The exact key names in the SDK's usage dict at runtime. The SDK may pass through the raw API response format.
   - Recommendation: Log the actual `usage` dict during an integration test to confirm field names. Ensure `to_text()` handles both expected and unexpected keys gracefully.

2. **Rate limit error detection reliability**
   - What we know: `AssistantMessage.error` has a `"rate_limit"` literal type. `ProcessError` surfaces generic subprocess failures.
   - What's unclear: Whether rate limits always produce an `AssistantMessage` with `error="rate_limit"` or sometimes just crash the subprocess with a ProcessError.
   - Recommendation: Detect rate limits by checking both `AssistantMessage.error` during iteration AND by checking `ProcessError.stderr` for rate-limit keywords. Treat ambiguous ProcessErrors as retryable.

3. **Session ID lifetime and cleanup**
   - What we know: Sessions are stored in `~/.claude/projects/`. The SDK supports `resume` and `fork_session`.
   - What's unclear: How long session IDs remain valid. Whether there is a TTL or cleanup process.
   - Recommendation: Always handle session resume failure gracefully (fall back to new session with warning). Do not guarantee cross-day session continuity.

4. **Retry interaction with timeouts**
   - What we know: Each `run()` call has its own `asyncio.timeout()`. Retries add additional elapsed time.
   - What's unclear: Whether agents expect total wall-clock time to be bounded, or per-attempt time.
   - Recommendation: Each retry attempt gets the full timeout. Total wall-clock time = `(max_retries + 1) * timeout + total_backoff_delays`. Document this clearly. Consider adding an optional `total_timeout` that bounds all retries.

## Sources

### Primary (HIGH confidence)
- Claude Agent SDK types.py (local installation, v0.1.39) - `ClaudeAgentOptions.resume`, `fork_session`, `ResultMessage.total_cost_usd`, `ResultMessage.usage`, `AssistantMessageError` literal types
- Claude Agent SDK subprocess_cli.py (local installation) - `_build_command()` shows `--resume` and `--continue` CLI flag construction
- [Session Management - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/sessions) - Session resume, fork_session, session ID capture patterns
- [Agent SDK Reference - Python](https://platform.claude.com/docs/en/agent-sdk/python) - Full API reference: ClaudeAgentOptions fields, ResultMessage fields, error types
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) - CLI `--resume`, `--output-format`, session management
- Existing codebase analysis: `transport/client.py`, `transport/types.py`, `transport/errors.py`, `output/schema.py`, `commands/engine.py`, `cli.py`

### Secondary (MEDIUM confidence)
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Exponential backoff patterns, jitter strategies (used as reference for hand-rolled implementation)
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) - Model pricing: Sonnet 4.5 $3/$15/M, Opus 4.6 $5/$25/M, Haiku 4.5 $1/$5/M per million tokens
- [GitHub: claude-agent-sdk-python issues](https://github.com/anthropics/claude-agent-sdk-python/issues/109) - Session resume behavior and limitations

### Tertiary (LOW confidence)
- [Token counting - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/token-counting) - Token counting methodology (for understanding usage dict structure)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All features use existing dependencies. No new libraries needed. SDK APIs verified via local source inspection.
- Architecture: HIGH - Patterns follow established project conventions (transport adapter, lazy imports, per-call kwargs). Retry at transport level is a well-proven pattern.
- Pitfalls: HIGH - Error classification, jitter, session lifetime, and schema stability are well-documented concerns in production retry systems.

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days -- SDK API is stable at v0.1.39, retry patterns are timeless)
