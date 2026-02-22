---
phase: 03-reliability
plan: 01
subsystem: transport
tags: [retry, exponential-backoff, jitter, session-resume, error-classification]

requires:
  - phase: 02.1-integration-fixes
    provides: "Fixed ClaudeTransport adapter with correct SDK wiring"
provides:
  - "RetryPolicy dataclass for configurable retry behavior"
  - "is_retryable() error classifier: CLINotFound/JSONDecodeError/TransportTimeout are fatal; ConnectionError_/ProcessError are retryable"
  - "calculate_backoff() with exponential growth, max cap, and jitter"
  - "Transport-level retry loop in ClaudeTransport.run() wrapping _run_once()"
  - "Session resume via resume_session_id -> ClaudeAgentOptions.resume passthrough"
  - "--resume CLI flag on new-project, plan-phase, execute-phase commands"
affects: [03-02, all-commands, library-api]

tech-stack:
  added: []
  patterns: ["transport-level retry with error classification", "session ID passthrough"]

key-files:
  created:
    - "src/openclawpack/transport/retry.py"
    - "tests/test_transport/test_retry.py"
  modified:
    - "src/openclawpack/transport/types.py"
    - "src/openclawpack/transport/__init__.py"
    - "src/openclawpack/transport/client.py"
    - "src/openclawpack/commands/engine.py"
    - "src/openclawpack/commands/new_project.py"
    - "src/openclawpack/commands/plan_phase.py"
    - "src/openclawpack/commands/execute_phase.py"
    - "src/openclawpack/cli.py"
    - "tests/test_transport/test_client.py"
    - "tests/test_commands/test_engine.py"
    - "tests/test_cli.py"

key-decisions:
  - "Retry logic lives at transport level (ClaudeTransport.run) -- every workflow benefits without duplication"
  - "is_retryable() returns False for CLINotFound, JSONDecodeError, TransportTimeout; True for ConnectionError_, ProcessError"
  - "Exponential backoff with jitter: min(base * 2^attempt, max) + uniform(-jitter, +jitter), clamped to >= 0"
  - "RetryPolicy is a dataclass (consistent with TransportConfig convention, not Pydantic)"
  - "run() refactored to retry wrapper calling _run_once(); existing logic moved intact to _run_once()"
  - "resume_session_id is per-call (not config-level) -- flows CLI -> workflow -> engine -> transport -> SDK"
  - "--resume flag NOT on status command (local-only, no Claude session)"

patterns-established:
  - "Transport-level retry: single retry site wrapping SDK calls, error-type-aware"
  - "Session ID passthrough: CLI flag -> workflow param -> engine init -> transport kwarg -> SDK options.resume"

requirements-completed: [TRNS-05, TRNS-06]

duration: 4min
completed: 2026-02-22
---

# Plan 03-01: Retry Logic and Session Resume Summary

**Added transport-level retry with exponential backoff and session resume via --resume CLI flag**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 11

## Accomplishments
- Created retry.py module with RetryPolicy dataclass, is_retryable() error classifier, and calculate_backoff() with jitter
- Added retry_policy field to TransportConfig with sensible defaults (3 retries, 2s base, 60s max, 0.5 jitter)
- Refactored ClaudeTransport.run() into retry wrapper calling _run_once()
- Added resume_session_id passthrough from CLI through workflow/engine/transport to ClaudeAgentOptions.resume
- Added --resume flag to new-project, plan-phase, and execute-phase CLI commands
- Added 19 retry unit tests + 8 retry integration tests + 3 engine resume tests + 4 CLI resume tests
- Exported RetryPolicy from transport package __init__.py

## Files Created/Modified
- `src/openclawpack/transport/retry.py` - NEW: RetryPolicy, is_retryable(), calculate_backoff()
- `src/openclawpack/transport/types.py` - Added retry_policy field to TransportConfig
- `src/openclawpack/transport/__init__.py` - Exported RetryPolicy
- `src/openclawpack/transport/client.py` - Retry loop in run(), _run_once() with resume, usage enrichment
- `src/openclawpack/commands/engine.py` - resume_session_id parameter on init and run_gsd_command
- `src/openclawpack/commands/new_project.py` - resume_session_id parameter
- `src/openclawpack/commands/plan_phase.py` - resume_session_id parameter
- `src/openclawpack/commands/execute_phase.py` - resume_session_id parameter
- `src/openclawpack/cli.py` - --resume flag on three commands
- `tests/test_transport/test_retry.py` - NEW: 19 tests for retry module
- `tests/test_transport/test_client.py` - 8 tests for retry and resume in transport
- `tests/test_commands/test_engine.py` - 3 tests for resume forwarding
- `tests/test_cli.py` - 4 tests for --resume flag

## Decisions Made
- Hand-rolled retry (no tenacity dependency) -- only 1 retry site with 3 error types
- Each retry attempt gets the full per-call timeout (not a shared total timeout)
- Per-call resume_session_id parameter overrides instance-level default in engine

## Deviations from Plan
- Also included usage enrichment with total_cost_usd in _run_once() (from Plan 03-02) since it was a natural fit during the refactor

## Issues Encountered
None.

## Next Phase Readiness
- Transport retry loop and session resume ready for all commands
- Usage enrichment with total_cost_usd ready for text formatter (Plan 03-02)

---
*Phase: 03-reliability*
*Completed: 2026-02-22*
