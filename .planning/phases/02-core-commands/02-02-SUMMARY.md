---
phase: 02-core-commands
plan: 02
subsystem: commands
tags: [status, new-project, workflow, answer-map, command-result, lazy-import]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: CommandResult, state reader (get_project_summary), PlanningDirectory models
  - phase: 02-core-commands/01
    provides: WorkflowEngine, build_answer_callback, CLI command dispatchers, DEFAULT_TIMEOUTS
provides:
  - status_workflow() returning CommandResult with structured project summary
  - new_project_workflow() constructing /gsd:new-project --auto prompt with answer injection
  - NEW_PROJECT_DEFAULTS dict with 7 substring keys for GSD config question answers
  - Auto-detection of file paths as idea input with transparent content reading
  - new_project_workflow_sync() sync wrapper via anyio
  - CLI status command refactored to thin dispatch via status_workflow()
affects: [02-03-plan-execute-phase]

# Tech tracking
tech-stack:
  added: []
  patterns: [thin-cli-fat-workflow, file-path-auto-detection, answer-map-defaults-with-overrides]

key-files:
  created:
    - src/openclawpack/commands/status.py
    - src/openclawpack/commands/new_project.py
    - tests/test_commands/test_status.py
    - tests/test_commands/test_new_project.py
  modified:
    - src/openclawpack/cli.py

key-decisions:
  - "status_workflow is synchronous (no async needed for local file reads)"
  - "NEW_PROJECT_DEFAULTS uses substring keys for fuzzy matching against GSD question text"
  - "new_project_workflow auto-detects file paths via Path.is_file() check on idea parameter"
  - "CLI status command refactored from inline to thin dispatch through status_workflow()"

patterns-established:
  - "Workflow module pattern: each command has a dedicated module in commands/ with async workflow function"
  - "Mock patch at source pattern: WorkflowEngine patched at openclawpack.commands.engine.WorkflowEngine for lazy import testing"
  - "Answer defaults with overrides: {**DEFAULTS, **(overrides or {})} for customizable answer maps"

requirements-completed: [CMD-01, CMD-04]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 2 Plan 2: Status and New-Project Workflows Summary

**Status workflow reading local .planning/ state into CommandResult JSON, and new-project workflow constructing /gsd:new-project --auto prompt with 7-key answer map for GSD config questions**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T07:20:45Z
- **Completed:** 2026-02-22T07:24:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Built status_workflow() that wraps get_project_summary() in CommandResult with duration tracking and graceful FileNotFoundError handling
- Built new_project_workflow() with /gsd:new-project --auto prompt construction, file-path auto-detection, and answer map defaults merged with overrides
- Refactored CLI status command from inline implementation to thin dispatch through status_workflow() module
- 20 new tests covering both workflows without requiring Claude Code

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement status workflow with tests** - `960e1df` (feat)
2. **Task 2: Implement new-project workflow with answer map and tests** - `2247a6d` (feat)

## Files Created/Modified
- `src/openclawpack/commands/status.py` - status_workflow() wrapping get_project_summary in CommandResult with duration and error handling
- `src/openclawpack/commands/new_project.py` - new_project_workflow() with prompt construction, file detection, NEW_PROJECT_DEFAULTS, and sync wrapper
- `src/openclawpack/cli.py` - Status command refactored to lazy import and dispatch to status_workflow()
- `tests/test_commands/test_status.py` - 7 tests: success, error, default cwd, duration, all fields, error duration, real project
- `tests/test_commands/test_new_project.py` - 13 tests: prompt, file/text detection, defaults, overrides, timeout, project_dir, verbose, quiet, cwd, command name, result type

## Decisions Made
- status_workflow is synchronous (no async needed) since it only reads local files -- avoids unnecessary async overhead
- NEW_PROJECT_DEFAULTS uses substring keys ("depth", "parallelization", "git", "research", "plan check", "verif", "model") for fuzzy matching against GSD question text, matching the 3-tier strategy from answers.py
- new_project_workflow auto-detects file paths via Path(idea).is_file() -- if the idea string happens to be a valid file path, its content is read transparently
- CLI status command refactored from inline implementation to thin dispatch pattern, completing the "thin CLI / fat workflow" contract from Plan 02-01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed mock patch path for new-project tests**
- **Found during:** Task 2 (test_new_project.py)
- **Issue:** Tests patched `openclawpack.commands.new_project.WorkflowEngine` but the import is lazy (inside function body), so the attribute doesn't exist at module level
- **Fix:** Changed patch target to `openclawpack.commands.engine.WorkflowEngine` (the source module), matching the pattern documented in 02-01-SUMMARY
- **Files modified:** tests/test_commands/test_new_project.py
- **Verification:** All 13 new-project tests pass
- **Committed in:** 2247a6d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test infrastructure fix only, no scope change. Same pattern as 02-01 deviation.

## Issues Encountered
None beyond the mock path fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Status and new-project workflows complete; Plan 02-03 can now build plan-phase and execute-phase workflows
- Binding contract from cli.py fully satisfied for status and new-project imports
- Pattern established: workflow modules use lazy imports, tests patch at source module

## Self-Check: PASSED

- All 5 created/modified files verified present on disk
- Commit 960e1df (Task 1) verified in git log
- Commit 2247a6d (Task 2) verified in git log
- 198 tests pass (excluding 1 nested-session integration test)
- CLI status returns valid JSON from real project state
- CLI new-project --help shows expected interface
- Import paths verified: status_workflow and new_project_workflow importable

---
*Phase: 02-core-commands*
*Completed: 2026-02-22*
