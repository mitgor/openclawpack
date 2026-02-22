# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** An AI agent can go from "build me a todo app" to a fully planned GSD project with roadmap, without any human interaction.
**Current focus:** Phase 5: Multi-Project Management

## Current Position

Phase: 5 of 5 (Multi-Project Management)
Plan: 1 of 2 complete
Status: In progress
Last activity: 2026-02-22 -- Plan 05-01 registry data layer complete

Progress: [██████████] 97%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 4min
- Total execution time: 0.94 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1-Foundation | 01-01, 01-02, 01-03 | 12min | 4min |
| 2-Core Commands | 02-01, 02-02, 02-03, 02-04 | 14min | 4min |
| 2.1-Integration Fixes | 02.1-01, 02.1-02 | 8min | 4min |
| 3-Reliability | 03-01, 03-02 | 8min | 4min |
| 4-Library API and Events | 04-01, 04-02 | 10min | 5min |
| 5-Multi-Project Management | 05-01 | 4min | 4min |

**Recent Trend:**
- Last 5 plans: 03-01 (4min), 03-02 (4min), 04-01 (5min), 04-02 (5min), 05-01 (4min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Claude Agent SDK (v0.1.x) identified as potential transport foundation but alpha-status risk noted. Adapter interface recommended to isolate SDK calls.
- [Roadmap]: Read-only principle for .planning/ files -- all mutations flow through GSD via Claude subprocess.
- [01-01]: Used src/ layout to prevent test import confusion (research pitfall 5)
- [01-01]: Lazy import of _version in CLI callback for PKG-04 compliance
- [01-01]: CommandResult uses factory classmethods (ok/error) for ergonomic creation
- [01-02]: STATE.md and PROJECT.md required; config.json, ROADMAP.md, REQUIREMENTS.md optional with defaults
- [01-02]: Progress table in ROADMAP.md overrides inferred phase status from checkbox counts
- [01-02]: Section-based markdown parsing with extract_section() regex for heading-delimited content
- [01-03]: Flat exception hierarchy (5 subclasses of TransportError) for simple catch patterns
- [01-03]: client.py is the ONLY file importing claude_agent_sdk (adapter facade pattern)
- [01-03]: TransportConfig is a dataclass (not Pydantic) -- configuration, not validated data
- [02-01]: can_use_tool and hooks are per-call kwargs (not config-level) since they vary per invocation
- [02-01]: Answer matching uses 3-tier strategy: exact -> substring (case-insensitive) -> fallback to first option
- [02-01]: WorkflowEngine uses SystemPromptPreset dict with 'claude_code' preset and append for non-interactive instruction
- [02-01]: CLI commands use lazy imports inside function bodies to maintain PKG-04 independence
- [02-01]: DEFAULT_TIMEOUTS dict at module level allows per-command timeout defaults (900/600/1200s)
- [02-02]: status_workflow is synchronous (no async needed for local file reads)
- [02-02]: NEW_PROJECT_DEFAULTS uses substring keys for fuzzy matching against GSD question text
- [02-02]: new_project_workflow auto-detects file paths via Path.is_file() check on idea parameter
- [02-02]: CLI status command refactored from inline to thin dispatch through status_workflow()
- [02-03]: PLAN_PHASE_DEFAULTS uses 4 keys (context/confirm/approve/proceed) for top-level GSD confirmations
- [02-03]: EXECUTE_PHASE_DEFAULTS uses 6 keys with checkpoint approval, wave continuation, and decision selection
- [02-03]: Default timeouts: plan-phase=600s, execute-phase=1200s (2x for multi-wave subagent execution)
- [02-03]: Tests patch WorkflowEngine at source module due to lazy imports preventing module-level patching
- [02-04]: --idea option takes precedence over positional argument when both provided
- [02-04]: _resolve_options() centralizes per-command/global option fallback to avoid duplication
- [02-04]: Per-command --project-dir/--verbose/--quiet on all commands for post-subcommand placement
- [02.1-01]: can_use_tool/hooks set as ClaudeAgentOptions fields, not sdk_query() kwargs
- [02.1-01]: Prompt wrapped as AsyncIterable when can_use_tool is set (SDK streaming requirement)
- [02.1-01]: Hook callback uses 3-param signature (input, tool_use_id, context) -> dict
- [02.1-01]: build_hooks_dict() lazy-imports HookMatcher to preserve PKG-04 compliance
- [02.1-01]: quiet takes precedence over verbose when both set
- [02.1-02]: Engine catches TransportError specifically for structured error handling
- [02.1-02]: Workflow functions use broad Exception catch as outermost CLI defense
- [02.1-02]: build_hooks_dict() replaces bare dict hooks in engine for correct SDK structure
- [03-01]: Retry logic lives at transport level (ClaudeTransport.run wrapping _run_once) -- every workflow benefits
- [03-01]: is_retryable() returns False for CLINotFound, JSONDecodeError, TransportTimeout; True for ConnectionError_, ProcessError
- [03-01]: Exponential backoff with jitter: min(base * 2^attempt, max) + uniform(-jitter, +jitter), clamped to >= 0
- [03-01]: RetryPolicy is a dataclass (consistent with TransportConfig convention)
- [03-01]: resume_session_id is per-call (not config-level) -- flows CLI -> workflow -> engine -> transport -> SDK
- [03-02]: format_text() uses comma-formatted numbers and $0.0000 cost display
- [03-02]: --output-format is a global CLI option on app callback, read from ctx.obj
- [03-02]: Status command fills usage with zeros when None (prevents downstream KeyError)
- [04-01]: EventType is a str, Enum with 5 lowercase string values for JSON serialization
- [04-01]: EventBus uses defaultdict(list) for _handlers, supports both sync and async handlers
- [04-01]: Handler exceptions are logged (not propagated) -- emit never crashes the caller
- [04-01]: emit() skips async handlers with a warning; emit_async() handles both
- [04-01]: cli_json_handler writes "event: {json}" to stderr (not stdout) to avoid conflicting with structured output
- [04-01]: ProjectStatus model added to output/schema.py alongside CommandResult
- [04-02]: api.py functions use lazy imports inside bodies to preserve PKG-04
- [04-02]: Each API function accepts optional event_bus and creates a default EventBus if None
- [04-02]: get_status converts raw dict result to ProjectStatus model via try/except (graceful fallback)
- [04-02]: __init__.py uses __getattr__ for lazy re-exports -- imports don't trigger SDK loading
- [04-02]: _make_cli_bus() creates EventBus with cli_json_handler on all 5 event types
- [04-02]: CLI commands (new-project, plan-phase, execute-phase) call api.py functions with _make_cli_bus() when not quiet
- [04-02]: Status command unchanged -- local-only, no event emission needed
- [05-01]: ProjectRegistry uses classmethod load() factory instead of __init__ for clean empty-or-file construction
- [05-01]: Atomic write uses tempfile.mkstemp + os.replace (not NamedTemporaryFile) for explicit fd control and fsync
- [05-01]: State snapshot in add() gracefully falls back to None if get_project_summary() fails
- [05-01]: _user_data_dir() uses stdlib only (sys.platform + os.environ) to respect PKG-03 zero-dep constraint

### Pending Todos

None yet.

### Blockers/Concerns

- Claude Agent SDK is alpha (v0.1.x) -- adapter facade pattern in client.py isolates this risk (resolved by Phase 1 design).
- State parser doesn't handle decimal phase numbers (e.g., "2.1") -- fragile tests fail when STATE.md references sub-phases.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 05-01-PLAN.md (registry data layer)
Resume file: None
