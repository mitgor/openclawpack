# Plan 04-02 Summary: Library API Facade and CLI Event Integration

## What Was Done
- Created `src/openclawpack/api.py` with four async functions:
  - `create_project()`: wraps new_project_workflow, emits PROGRESS_UPDATE/ERROR events
  - `plan_phase()`: wraps plan_phase_workflow, emits PLAN_COMPLETE/ERROR events
  - `execute_phase()`: wraps execute_phase_workflow, emits PHASE_COMPLETE/ERROR events
  - `get_status()`: wraps status_workflow, converts dict to ProjectStatus, emits PROGRESS_UPDATE/ERROR events
- Updated `src/openclawpack/__init__.py` with lazy `__getattr__` re-exports for all 4 API functions + 3 event types
- Added `_make_cli_bus()` helper to `src/openclawpack/cli.py`
- Refactored CLI commands (new-project, plan-phase, execute-phase) to call api.py functions with EventBus

## Key Decisions
- All API functions accept optional `event_bus: EventBus | None` -- creates default (no-op) bus if None
- `__getattr__` pattern in __init__.py ensures lazy loading -- `openclawpack --version` still works without SDK
- `get_status()` wraps sync status_workflow in an async function for API consistency
- `get_status()` converts dict result to ProjectStatus via try/except (graceful fallback if dict doesn't match)
- CLI status command stays unchanged -- local-only, no event emission needed
- Tests patch workflow functions at source module paths (not on api.py) due to lazy imports inside function bodies

## Tests Added
- 19 tests in tests/test_api.py (4 functions x ~4-5 tests each)
- 8 tests in TestPackageImports (import verification, __all__, PKG-04)
- 2 tests in TestMakeCliBus (returns EventBus, all event types registered)
- 2 tests in TestCliEventBusWiring (quiet mode skips bus, normal mode creates bus)

## Files Created/Modified
- Created: `src/openclawpack/api.py`
- Created: `tests/test_api.py`
- Modified: `src/openclawpack/__init__.py` (lazy __getattr__ re-exports)
- Modified: `src/openclawpack/cli.py` (_make_cli_bus helper, CLI commands refactored to use api.py)
- Modified: `tests/test_cli.py` (added import, bus, and wiring tests)

## Requirements Satisfied
- INT-01: Four async library functions importable from openclawpack top level
- INT-02: get_status returns CommandResult with ProjectStatus typed model
- INT-03: Events emitted via EventBus in all API functions
- INT-04: CLI commands wire _make_cli_bus() for stderr event output when not quiet
