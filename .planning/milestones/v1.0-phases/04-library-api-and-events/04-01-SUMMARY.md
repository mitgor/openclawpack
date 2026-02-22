# Plan 04-01 Summary: Event System and ProjectStatus Model

## What Was Done
- Created `src/openclawpack/events/` package with three modules:
  - `types.py`: EventType enum (5 members: PHASE_COMPLETE, PLAN_COMPLETE, ERROR, DECISION_NEEDED, PROGRESS_UPDATE) and Event Pydantic model with to_json_line()
  - `bus.py`: EventBus class with on/off/emit/emit_async supporting both sync and async handlers, with exception logging (never propagation)
  - `cli_handler.py`: cli_json_handler that writes "event: {json}" to stderr
  - `__init__.py`: Re-exports EventBus, Event, EventType
- Added ProjectStatus Pydantic model to `src/openclawpack/output/schema.py` with typed fields for current_phase, progress_percent, blockers, requirements counts
- Created comprehensive test suite: `tests/test_events/` with test_types.py, test_bus.py, test_cli_handler.py

## Key Decisions
- EventType is `str, Enum` for direct JSON serialization without custom encoders
- EventBus.emit() (sync) skips async handlers with a warning log rather than crashing
- Handler exceptions logged via `logging.getLogger(__name__)` -- never propagated to callers
- cli_json_handler writes to stderr (not stdout) to avoid conflicting with structured JSON output
- ProjectStatus placed in output/schema.py alongside CommandResult (same module, cohesive)

## Tests Added
- 29 event system tests (types, bus, CLI handler)
- 6 ProjectStatus tests in test_output/test_schema.py

## Files Created/Modified
- Created: `src/openclawpack/events/__init__.py`, `types.py`, `bus.py`, `cli_handler.py`
- Created: `tests/test_events/__init__.py`, `test_types.py`, `test_bus.py`, `test_cli_handler.py`
- Modified: `src/openclawpack/output/schema.py` (added ProjectStatus)
- Modified: `src/openclawpack/output/__init__.py` (added ProjectStatus export)
- Modified: `tests/test_output/test_schema.py` (added ProjectStatus tests)

## Requirements Satisfied
- INT-02: ProjectStatus typed model exists
- INT-03: EventBus with on/off/emit/emit_async works
- INT-04: cli_json_handler writes JSON event lines to stderr
