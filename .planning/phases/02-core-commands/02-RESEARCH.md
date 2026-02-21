# Phase 2 Research: Core Commands

## Summary

Phase 2 transforms openclawpack from a foundation layer into a usable tool by implementing four CLI commands (`new-project`, `plan-phase`, `execute-phase`, `status`) that drive GSD workflows non-interactively. The central challenge is **answer injection**: GSD workflows use the `AskUserQuestion` tool for interactive prompts, and the claude-agent-sdk's `can_use_tool` callback is the mechanism to intercept these and supply pre-determined answers. However, a critical limitation exists -- `AskUserQuestion` is not available in subagents spawned via the Task tool, meaning the main GSD workflow orchestrator is the only touchpoint for question interception. The transport layer (Phase 1) needs extension to support `system_prompt` presets, `setting_sources`, `can_use_tool`, `hooks`, `max_turns`, and `max_budget_usd`. Each command maps to a specific GSD skill invocation, with a workflow engine translating high-level parameters into correct GSD invocations.

## Phase Requirements

| Requirement | Description | Research Findings |
|---|---|---|
| CMD-01 | `new-project --idea <text_or_file>` creates GSD project non-interactively | GSD's `/gsd:new-project` has `--auto` mode that skips deep questioning but still asks config questions (depth, parallelization, git tracking, etc.) via AskUserQuestion. Auto mode requires an idea document, creates all 5 .planning/ files, spawns 4 parallel researcher subagents + synthesizer + roadmapper via Task tool, then auto-advances to discuss-phase. Answer injection via `can_use_tool` intercepts config questions at the top-level agent; subagent questions cannot be intercepted (SDK limitation). |
| CMD-02 | `plan-phase <N>` plans a phase non-interactively | GSD's `/gsd:plan-phase` initializes via `gsd-tools.cjs init plan-phase "$PHASE"`, loads CONTEXT.md, asks AskUserQuestion if missing, spawns researcher/planner/checker subagents via Task, has up to 3 revision iterations. Questions at top level can be intercepted; subagent operations run autonomously. |
| CMD-03 | `execute-phase <N>` executes a phase non-interactively | GSD's `/gsd:execute-phase` initializes via `gsd-tools.cjs init execute-phase "${PHASE_ARG}"`, uses wave-based parallel execution with plan grouping, spawns executor subagents via Task, handles checkpoints. Auto-mode auto-approves checkpoints and selects first option. |
| CMD-04 | `status` returns structured JSON | Already has `get_project_summary()` from Phase 1 state layer. Needs wiring: parse `--project-dir` path, call `read_project_state()`, format as `CommandResult.ok()` envelope. No transport/subprocess needed. |
| CMD-05 | Pre-filled answer injection via GSD --auto mode | SDK `can_use_tool` callback intercepts `AskUserQuestion` calls. Return `PermissionResultAllow(updated_input={"questions": input_data["questions"], "answers": {"question text": "selected label"}})`. Multi-select joins labels with `", "`. Free-text uses custom text as value. Python SDK requires streaming mode + dummy PreToolUse hook for `can_use_tool` to fire. |
| CMD-06 | `--project-dir` flag on all commands | Typer option with default to `os.getcwd()`. Passed as `cwd` to TransportConfig and as working directory for state reader. Must validate directory exists before invoking transport. |
| CMD-07 | `--verbose`/`--quiet` flags on all commands | `--verbose` streams subprocess output to stderr. `--quiet` suppresses all non-JSON output. Default: structured JSON only on stdout. Can use Typer callback or app-level option with context. |
| INT-05 | Workflow engine translates commands to GSD invocations | Each command maps to a GSD skill: `new-project` -> `/gsd:new-project --auto`, `plan-phase N` -> `/gsd:plan-phase N`, `execute-phase N` -> `/gsd:execute-phase N`. Engine constructs the prompt string, configures `system_prompt` preset with append, sets `setting_sources=["project"]`, wires `can_use_tool` callback, and invokes transport. |

## Standard Stack

These are the established tools and patterns from Phase 1 that Phase 2 builds on:

| Component | Choice | Rationale |
|---|---|---|
| CLI framework | Typer >= 0.24 | Already used in Phase 1 cli.py. Add commands via `@app.command()` decorators |
| Data models | Pydantic v2 >= 2.12 | Already used for CommandResult and state models. Use for command parameter validation |
| Transport | claude-agent-sdk >= 0.1.39 | Already wrapped by ClaudeTransport. Extend for new SDK options |
| Async runtime | anyio >= 4.8 | Already used for sync-to-async bridge in `run_sync()` |
| Output envelope | CommandResult | Already provides `{success, result, errors, session_id, usage, duration_ms}` schema |
| State reading | read_project_state() / get_project_summary() | Phase 1 state layer, ready for CMD-04 wiring |
| Exception handling | TransportError hierarchy | Phase 1 typed exceptions for transport failures |

## Architecture Patterns

### 1. Workflow Engine Pattern (INT-05)

The workflow engine is the core new abstraction for Phase 2. It translates high-level command parameters into SDK invocations:

```
CLI Command -> Workflow Engine -> Transport (SDK) -> Claude Code -> GSD Skill
```

Each command has a workflow class or function that:
1. Constructs the prompt string (e.g., `/gsd:new-project --auto` with idea content)
2. Configures SDK options (system_prompt, setting_sources, can_use_tool, etc.)
3. Defines the answer map for expected AskUserQuestion prompts
4. Invokes `ClaudeTransport.run()` with the configured options
5. Parses the result into a typed response model

**Key design decision**: The workflow engine should be a separate module (e.g., `src/openclawpack/commands/` or `src/openclawpack/workflows/`) that CLI commands delegate to. CLI functions stay thin -- they parse args via Typer and call the workflow engine.

### 2. Answer Injection via can_use_tool (CMD-05)

This is the most technically complex pattern in Phase 2. The SDK's `can_use_tool` callback intercepts tool calls before they execute:

```python
async def can_use_tool(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResult:
    if tool_name == "AskUserQuestion":
        answers = build_answers(tool_input["questions"], answer_map)
        return PermissionResultAllow(
            updated_input={
                "questions": tool_input["questions"],
                "answers": answers,
            }
        )
    # Allow all other tools
    return PermissionResultAllow()
```

**Critical SDK requirement**: In Python, `can_use_tool` only fires when using streaming mode AND a `PreToolUse` hook is registered. The hook can be a no-op but must exist:

```python
async def pre_tool_use(session, event):
    pass  # Required for can_use_tool to fire in Python SDK

hooks = {"PreToolUse": pre_tool_use}
```

### 3. System Prompt Preset with Append

GSD skills are part of Claude Code's system prompt. To preserve them while adding custom instructions:

```python
system_prompt = {
    "type": "preset",
    "preset": "claude_code",
    "append": "Execute the following command non-interactively. Do not ask clarifying questions.",
}
```

Combined with `setting_sources=["project"]` to load the project's CLAUDE.md file, which contains GSD skill definitions.

### 4. Transport Extension Pattern

ClaudeTransport.run() needs new parameters. The established per-call override pattern (`**kwargs`) should be extended:

```python
# New TransportConfig fields needed:
system_prompt: str | dict | None = None  # str or SystemPromptPreset dict
setting_sources: list[str] | None = None
max_turns: int | None = None
max_budget_usd: float | None = None
# can_use_tool and hooks are per-call, not config-level
```

ClaudeAgentOptions construction in `run()` must pass these through to the SDK.

### 5. Thin CLI / Fat Workflow Pattern

CLI functions should be thin dispatchers:

```python
@app.command()
def new_project(
    idea: str = typer.Argument(...),
    project_dir: str = typer.Option(None, "--project-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    quiet: bool = typer.Option(False, "--quiet"),
) -> None:
    result = new_project_workflow(idea=idea, project_dir=project_dir, verbose=verbose)
    output(result, quiet=quiet)
```

This keeps CLI testable (mock the workflow) and workflow testable (no Typer dependency).

## Don't Hand-Roll

| Capability | Use This | Not This |
|---|---|---|
| Answer injection | SDK `can_use_tool` + `PermissionResultAllow(updated_input=...)` | Parsing stdout for question patterns |
| GSD skill invocation | Prompt string with `/gsd:new-project --auto` | Reimplementing GSD logic in Python |
| System prompt preservation | `SystemPromptPreset` with append | Raw system_prompt string replacing Claude Code's prompt |
| CLAUDE.md loading | `setting_sources=["project"]` | Reading and injecting CLAUDE.md content manually |
| Question-answer mapping | `AskUserQuestion` tool input schema | Regex matching on subprocess output |
| Status data | `get_project_summary()` from state layer | Re-parsing .planning/ files in the CLI |
| JSON output envelope | `CommandResult.ok()` / `CommandResult.error()` | Custom dict construction |
| Async-to-sync | `anyio.from_thread.run()` (already in transport) | Threading or subprocess for async bridging |

## Common Pitfalls

### 1. can_use_tool Requires Streaming + PreToolUse Hook (Python SDK)

**Pitfall**: `can_use_tool` callback silently does nothing without streaming mode and a registered PreToolUse hook.

**Mitigation**: Always register a no-op `PreToolUse` hook when using `can_use_tool`. Validate this in integration tests.

**Evidence**: Claude Agent SDK Python documentation explicitly states this requirement. The hooks parameter and streaming are co-required.

### 2. AskUserQuestion Not Available in Subagents

**Pitfall**: GSD workflows heavily use the Task tool to spawn subagents (researchers, planners, executors, checkers). `AskUserQuestion` is NOT available in these subagents. Only the top-level agent can present questions.

**Mitigation**: This is actually favorable for non-interactive use -- subagents run autonomously without prompting. The answer injection only needs to handle top-level questions. However, if a GSD workflow update adds questions to subagents, they would fail silently or error. Monitor GSD updates.

**Evidence**: SDK documentation on user-input handling: "Note: AskUserQuestion is not available in subagents spawned via the Task tool."

### 3. GSD --auto Mode Still Asks Config Questions

**Pitfall**: `--auto` mode for new-project skips the deep questioning phase but STILL asks configuration questions (depth level, parallelization, git tracking, research preference, plan checking, verifier, AI model config) via AskUserQuestion.

**Mitigation**: Build a comprehensive answer map for all known config questions. The answer map should have sensible defaults (e.g., depth=3, parallelization=true, git_tracking=true). Allow users to override defaults via CLI options or a config file.

**Evidence**: `/gsd:new-project` workflow source shows Step 2 (config questions) always executes regardless of --auto flag.

### 4. Question Text Matching is Fragile

**Pitfall**: Answer injection maps question text strings to answer values. GSD updates may change question wording, breaking the mapping.

**Mitigation**: Use fuzzy/partial matching (e.g., key substring matching) rather than exact string equality. Log unmatched questions as warnings. Provide a fallback strategy (e.g., select first option for multiple-choice, use a default for free-text).

### 5. Long-Running Workflows May Exceed Timeout

**Pitfall**: `new-project` spawns 4+ parallel researcher subagents. `execute-phase` runs multiple executor subagents in waves. These can run for 10+ minutes.

**Mitigation**: Set generous timeouts per command type. TransportConfig already supports `timeout_seconds` (default 300s). New-project and execute-phase may need 600-1200s. Consider making timeout configurable per command via CLI option.

### 6. session_id and usage Extraction from SDK Response

**Pitfall**: `ResultMessage` from the SDK contains `session_id`, `duration_ms`, `total_cost_usd`, `usage` (with `input_tokens`, `output_tokens`). These must be mapped to the CommandResult envelope fields. Current transport adapter may not extract all of these.

**Mitigation**: Extend the transport result mapping to capture all ResultMessage fields. Map `total_cost_usd` and token counts into CommandResult's `usage` field.

### 7. --project-dir Must Be Passed to Both Transport and State

**Pitfall**: The `--project-dir` flag affects two separate subsystems: transport (as `cwd` for the Claude subprocess) and state (as the directory to read .planning/ files from). Forgetting to pass it to one causes silent incorrect behavior.

**Mitigation**: The workflow engine should accept `project_dir` once and propagate it to both transport config and state reader calls.

### 8. Verbose Output and Streaming

**Pitfall**: `--verbose` should show subprocess output as it streams, but the SDK may buffer output until completion.

**Mitigation**: The SDK supports streaming mode (required for `can_use_tool` anyway). Use stream events to pipe output to stderr in verbose mode. In quiet mode, suppress all non-JSON output.

## Code Examples

### Transport Extension (ClaudeAgentOptions Construction)

Current `client.py` constructs minimal options. Phase 2 needs:

```python
options = ClaudeAgentOptions(
    cwd=cwd,
    allowed_tools=allowed_tools or [],
    permission_mode=permission_mode,
    cli_path=cli_path,
    # New for Phase 2:
    system_prompt=kwargs.get("system_prompt", self.config.system_prompt),
    setting_sources=kwargs.get("setting_sources", self.config.setting_sources),
    max_turns=kwargs.get("max_turns", self.config.max_turns),
    max_budget_usd=kwargs.get("max_budget_usd", self.config.max_budget_usd),
    can_use_tool=kwargs.get("can_use_tool"),
    hooks=kwargs.get("hooks"),
)
```

### Answer Map Pattern

```python
# Default answer map for new-project config questions
NEW_PROJECT_DEFAULTS = {
    "depth": "3",           # Standard depth
    "parallelization": "Yes",
    "git_tracking": "Yes",
    "research": "Standard",
    "plan_check": "Yes",
    "verifier": "Yes",
}

def build_answer_callback(answer_map: dict[str, str]):
    """Create a can_use_tool callback that injects answers for AskUserQuestion."""
    async def can_use_tool(tool_name, tool_input, context):
        if tool_name == "AskUserQuestion":
            questions = tool_input.get("questions", [])
            answers = {}
            for q in questions:
                question_text = q.get("question", "")
                # Try exact match first, then substring match
                for key, value in answer_map.items():
                    if key in question_text:
                        answers[question_text] = value
                        break
                else:
                    # Fallback: select first option if available
                    options = q.get("options", [])
                    if options:
                        answers[question_text] = options[0].get("label", "")
            return PermissionResultAllow(
                updated_input={"questions": questions, "answers": answers}
            )
        return PermissionResultAllow()
    return can_use_tool
```

### Workflow Engine Invocation

```python
async def new_project_workflow(idea: str, project_dir: str | None = None, **overrides) -> CommandResult:
    """Execute new-project workflow via GSD."""
    cwd = project_dir or os.getcwd()

    # Build prompt
    prompt = f"/gsd:new-project --auto\n\n{idea}"

    # Build answer callback
    answer_map = {**NEW_PROJECT_DEFAULTS, **overrides.get("answers", {})}
    can_use_tool = build_answer_callback(answer_map)

    # No-op hook required for can_use_tool to fire in Python SDK
    async def pre_tool_use(session, event):
        pass

    transport = ClaudeTransport(TransportConfig(
        cwd=cwd,
        timeout_seconds=overrides.get("timeout", 900),
        system_prompt={"type": "preset", "preset": "claude_code", "append": "Execute non-interactively."},
        setting_sources=["project"],
    ))

    return await transport.run(
        prompt,
        can_use_tool=can_use_tool,
        hooks={"PreToolUse": pre_tool_use},
    )
```

### Status Command Wiring (CMD-04)

```python
@app.command()
def status(
    project_dir: str = typer.Option(None, "--project-dir", help="Project directory"),
    quiet: bool = typer.Option(False, "--quiet"),
) -> None:
    """Show project state as structured JSON."""
    import time
    start = time.monotonic()

    target = project_dir or os.getcwd()
    planning_dir = Path(target) / ".planning"

    try:
        summary = get_project_summary(planning_dir)
        duration_ms = int((time.monotonic() - start) * 1000)
        result = CommandResult.ok(result=summary, duration_ms=duration_ms)
    except FileNotFoundError as e:
        result = CommandResult.error(errors=[str(e)])

    if not quiet:
        typer.echo(result.model_dump_json(indent=2))
```

## State of the Art

### Claude Agent SDK (v0.1.39+) Capabilities Relevant to Phase 2

The SDK provides all primitives needed for non-interactive GSD invocation:

1. **`query()` function**: One-shot invocations, creates new session each call. Suitable for independent commands.
2. **`ClaudeSDKClient`**: Multi-turn client maintaining conversation across exchanges. Potentially useful for plan-phase -> execute-phase continuity (Phase 3, TRNS-06).
3. **`can_use_tool` callback**: Intercepts any tool call before execution. Returns `PermissionResultAllow` (optionally with `updated_input`) or `PermissionResultDeny`.
4. **`SystemPromptPreset`**: `{"type": "preset", "preset": "claude_code", "append": "..."}` preserves Claude Code's full system prompt including GSD skills.
5. **`setting_sources`**: `["project"]` loads CLAUDE.md from the project directory.
6. **`ResultMessage`**: Contains `session_id`, `duration_ms`, `total_cost_usd`, `usage` (input/output tokens), `is_error`, `result`, `num_turns`.
7. **`hooks`**: `PreToolUse` and `PostToolUse` hooks for tool lifecycle events. `PreToolUse` required for `can_use_tool` to fire in Python.
8. **`max_turns`**: Limits conversation turns, useful for bounding long workflows.
9. **`max_budget_usd`**: Limits spending per invocation.

### GSD Workflow Mechanics

GSD workflows operate as Claude Code skills (markdown files in `~/.claude/get-shit-done/workflows/`). Key mechanics:

1. **Initialization**: Each workflow calls `gsd-tools.cjs init <workflow> <args>` to set up state.
2. **Subagent delegation**: Workflows spawn specialized agents (researchers, planners, executors, checkers) via the Task tool. These run as independent Claude subagents.
3. **Question flow**: Top-level agent asks AskUserQuestion for config and decision points. Subagents cannot ask questions -- they run autonomously.
4. **Auto mode**: `--auto` flag on new-project skips questioning, auto-approves decisions, and auto-advances workflows.
5. **Checkpoint handling**: execute-phase pauses at checkpoints for non-autonomous plans. Auto-mode auto-approves checkpoints.

### GSD Workflow-to-Command Mapping

| openclawpack Command | GSD Skill | Key Parameters |
|---|---|---|
| `new-project --idea <text>` | `/gsd:new-project --auto` | Idea text appended to prompt, config question answers via can_use_tool |
| `plan-phase <N>` | `/gsd:plan-phase <N>` | Phase number in prompt, CONTEXT.md question handled via can_use_tool |
| `execute-phase <N>` | `/gsd:execute-phase <N>` | Phase number in prompt, checkpoint handling via can_use_tool |
| `status` | None (local only) | Uses state layer directly, no subprocess |

## Open Questions

### 1. Question Discovery and Answer Map Completeness

**Question**: How do we discover all possible AskUserQuestion prompts across GSD workflows to build comprehensive answer maps?

**Impact**: Missing answers would cause the workflow to hang or fail.

**Recommendation**: Start with known questions from workflow source analysis. Add a fallback strategy (first option for multiple-choice, configurable default for free-text). Log unmatched questions for iterative improvement. Consider an "answer map file" that users/agents can customize.

### 2. Streaming vs One-Shot for can_use_tool

**Question**: The Python SDK requires streaming mode for `can_use_tool` to fire. Does streaming mode change the return value format from `ResultMessage`?

**Impact**: May affect how results are extracted from the transport layer.

**Recommendation**: Spike test with streaming mode to confirm ResultMessage availability. The SDK docs suggest streaming returns the same ResultMessage at completion.

### 3. GSD Workflow Error Reporting

**Question**: When a GSD workflow fails mid-execution (e.g., researcher subagent errors, plan checker rejects after 3 iterations), what does the SDK return? Is it a `ResultMessage` with `is_error=True`, or does it throw an exception?

**Impact**: Error handling strategy in the workflow engine depends on this.

**Recommendation**: Integration test with a deliberately failing workflow to observe error shape. Design error handling to handle both paths (exception and error result).

### 4. idea Parameter Format for new-project

**Question**: Should `--idea` accept plain text, a file path, or both? GSD's --auto mode works with a "provided document" but the exact format expectations are unclear.

**Impact**: Affects CMD-01 CLI interface design and documentation.

**Recommendation**: Support both: if the value is a file path that exists, read the file content; otherwise treat it as plain text. This matches common CLI patterns.

### 5. Timeout Strategy Per Command

**Question**: What are appropriate default timeouts for each command? new-project with 4+ researcher subagents is much longer than status.

**Impact**: Too short causes premature termination; too long delays error detection.

**Recommendation**: `status` = no timeout (local only), `new-project` = 900s, `plan-phase` = 600s, `execute-phase` = 1200s. Make all configurable via `--timeout` CLI option.

### 6. Multi-Select and Free-Text Question Handling

**Question**: Some AskUserQuestion prompts use `multiSelect: true` or expect free-text input. How should the answer map express these?

**Impact**: Affects answer map data structure and the can_use_tool callback logic.

**Recommendation**: Answer map values should be strings. For multi-select, join with `", "` per SDK docs. For free-text, use the string directly. The callback logic handles formatting based on question type.

### 7. Verbose Streaming Implementation

**Question**: How should `--verbose` mode surface streaming output? Should it show all tool calls, just text responses, or raw event data?

**Impact**: Affects developer experience and debugging capability.

**Recommendation**: Verbose mode should stream text responses to stderr. Tool call events could be logged at debug level. Use the SDK's streaming events to selectively surface relevant output.

## Sources

| Source | What It Provided |
|---|---|
| `.planning/REQUIREMENTS.md` | CMD-01 through CMD-07, INT-05 requirement definitions |
| `.planning/ROADMAP.md` | Phase 2 goal, success criteria, dependencies |
| `.planning/PROJECT.md` | Core value, constraints, architecture principles |
| `.planning/STATE.md` | Current position, blockers, accumulated decisions |
| `.planning/phases/01-foundation/01-RESEARCH.md` | Phase 1 technology choices and patterns |
| `.planning/phases/01-foundation/01-01-SUMMARY.md` | Package skeleton, CLI, CommandResult patterns |
| `.planning/phases/01-foundation/01-02-SUMMARY.md` | State parser models and reader functions |
| `.planning/phases/01-foundation/01-03-SUMMARY.md` | Transport adapter, exceptions, lazy import |
| `.planning/research/ARCHITECTURE.md` | Workflow engine architecture pattern |
| `.planning/research/FEATURES.md` | Answer injection as HIGH complexity differentiator |
| `.planning/research/PITFALLS.md` | Non-interactive mode pitfall (Pitfall 5) |
| `~/.claude/get-shit-done/workflows/new-project.md` | Full new-project workflow with --auto mode |
| `~/.claude/get-shit-done/workflows/plan-phase.md` | Full plan-phase workflow with subagent spawning |
| `~/.claude/get-shit-done/workflows/execute-phase.md` | Full execute-phase workflow with wave execution |
| `~/.claude/get-shit-done/references/questioning.md` | GSD questioning guide for interactive prompts |
| `~/.claude/get-shit-done/references/planning-config.md` | Config schema for .planning/config.json |
| `src/openclawpack/cli.py` | Current CLI with stub status command |
| `src/openclawpack/transport/client.py` | ClaudeTransport adapter, current SDK usage |
| `src/openclawpack/transport/types.py` | TransportConfig dataclass |
| `src/openclawpack/output/schema.py` | CommandResult model |
| `src/openclawpack/state/reader.py` | read_project_state() and get_project_summary() |
| `platform.claude.com/docs/en/agent-sdk/python` | Full Claude Agent SDK Python reference |
| `platform.claude.com/docs/en/agent-sdk/user-input` | AskUserQuestion handling and answer injection |
| `platform.claude.com/docs/en/agent-sdk/modifying-system-prompts` | SystemPromptPreset and setting_sources |

## Metadata

```yaml
phase: 02-core-commands
researcher: gsd-phase-researcher
date: 2026-02-21
duration: ~25min
requirements_covered: [CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07, INT-05]
open_questions: 7
sources_consulted: 24
confidence: high
key_risk: AskUserQuestion question text matching fragility across GSD updates
```
