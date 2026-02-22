---
phase: 02-core-commands
plan: 01
subsystem: commands
tags: [can_use_tool, answer-injection, workflow-engine, typer, cli, system-prompt-preset]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: TransportConfig, ClaudeTransport, CommandResult, state reader
provides:
  - Extended TransportConfig with system_prompt dict, setting_sources, max_turns, max_budget_usd
  - ClaudeTransport.run() forwarding can_use_tool and hooks to sdk_query
  - build_answer_callback() for AskUserQuestion interception with fuzzy matching
  - build_noop_pretool_hook() required for can_use_tool in Python SDK
  - WorkflowEngine translating commands to GSD skill invocations
  - CLI with 4 commands (new-project, plan-phase, execute-phase, status)
  - Shared --project-dir, --verbose, --quiet options
affects: [02-02-new-project-plan-phase, 02-03-execute-phase-status]

# Tech tracking
tech-stack:
  added: []
  patterns: [answer-injection-callback, system-prompt-preset, workflow-engine-pattern, lazy-import-commands]

key-files:
  created:
    - src/openclawpack/commands/__init__.py
    - src/openclawpack/commands/answers.py
    - src/openclawpack/commands/engine.py
    - tests/test_commands/__init__.py
    - tests/test_commands/test_answers.py
    - tests/test_commands/test_engine.py
  modified:
    - src/openclawpack/transport/types.py
    - src/openclawpack/transport/client.py
    - src/openclawpack/cli.py
    - tests/test_transport/test_client.py

key-decisions:
  - "can_use_tool and hooks are per-call kwargs (not config-level) since they vary per invocation"
  - "Answer matching uses 3-tier strategy: exact -> substring (case-insensitive) -> fallback to first option"
  - "Workflow engine uses SystemPromptPreset dict with 'claude_code' preset and append for non-interactive instruction"
  - "CLI commands use lazy imports inside function bodies to maintain PKG-04 independence"
  - "DEFAULT_TIMEOUTS dict at module level allows per-command timeout defaults (900/600/1200s)"

patterns-established:
  - "Answer injection pattern: build_answer_callback(map) -> can_use_tool async callable"
  - "Noop pretool hook pattern: required for can_use_tool to fire in Python SDK"
  - "Thin CLI / fat workflow pattern: CLI parses args, workflow module does the work"
  - "Binding contract pattern: CLI stubs import from not-yet-created workflow modules"

requirements-completed: [CMD-05, CMD-06, CMD-07, INT-05]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 2 Plan 1: Command Infrastructure Summary

**Answer injection via can_use_tool callbacks with fuzzy matching, WorkflowEngine translating GSD commands to transport invocations, and 4 CLI commands with shared project-dir/verbose/quiet options**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T07:13:02Z
- **Completed:** 2026-02-22T07:18:13Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Extended TransportConfig with system_prompt dict support, setting_sources, max_turns, max_budget_usd; ClaudeTransport.run() now forwards can_use_tool and hooks to sdk_query
- Built answer injection module with 3-tier matching (exact, substring, fallback) and noop pretool hook required by Python SDK
- Created WorkflowEngine assembling prompt, system_prompt preset, setting_sources, timeouts, and answer callbacks per command
- Wired 4 CLI commands with shared options; status command works end-to-end reading real project state

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend TransportConfig and ClaudeTransport for Phase 2 SDK options** - `7144f57` (feat)
2. **Task 2: Build answer injection, workflow engine, and CLI command dispatchers** - `31f5498` (feat)

## Files Created/Modified
- `src/openclawpack/transport/types.py` - Added setting_sources, max_turns, max_budget_usd; widened system_prompt to str|dict|None
- `src/openclawpack/transport/client.py` - Extended run() to pop can_use_tool/hooks and forward to sdk_query; pass new config fields to options
- `src/openclawpack/commands/__init__.py` - Module init with DEFAULT_TIMEOUTS and lazy imports for WorkflowEngine/answers
- `src/openclawpack/commands/answers.py` - build_answer_callback() and build_noop_pretool_hook() with lazy SDK import
- `src/openclawpack/commands/engine.py` - WorkflowEngine with run_gsd_command() and sync wrapper
- `src/openclawpack/cli.py` - Full CLI with new-project, plan-phase, execute-phase, status commands and shared options
- `tests/test_transport/test_client.py` - 15 new tests for config fields and run() forwarding
- `tests/test_commands/__init__.py` - Test package init
- `tests/test_commands/test_answers.py` - 10 tests for answer callback (exact/fuzzy/fallback/passthrough)
- `tests/test_commands/test_engine.py` - 15 tests for prompt construction, timeouts, config, answer map wiring

## Decisions Made
- can_use_tool and hooks are per-call kwargs rather than config-level fields, since they vary per invocation and are not serializable config
- Answer matching uses 3-tier strategy (exact -> substring case-insensitive -> first option fallback) to handle GSD question text fragility
- WorkflowEngine uses SystemPromptPreset dict `{"type": "preset", "preset": "claude_code", "append": "..."}` to preserve Claude Code's built-in prompt
- CLI commands use lazy imports inside function bodies (not at module level) to maintain PKG-04 independence
- DEFAULT_TIMEOUTS dict provides per-command defaults: new-project=900s, plan-phase=600s, execute-phase=1200s, unknown=600s
- Established binding contract: CLI stubs import from workflow modules (new_project, plan_phase, execute_phase, status) that Plans 02-02 and 02-03 must create

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed mock patch path for engine tests**
- **Found during:** Task 2 (test_engine.py)
- **Issue:** Tests patched `openclawpack.commands.engine.ClaudeTransport` but engine uses local import from `openclawpack.transport.client`, so the attribute doesn't exist at module level
- **Fix:** Changed patch target to `openclawpack.transport.client.ClaudeTransport` (the source module)
- **Files modified:** tests/test_commands/test_engine.py
- **Verification:** All 15 engine tests pass
- **Committed in:** 31f5498 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test infrastructure fix only, no scope change.

## Issues Encountered
None beyond the mock path fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Command infrastructure complete; Plans 02-02 and 02-03 can build workflow modules
- Binding contract established: workflow modules must match the import paths and signatures defined in cli.py
- Plans 02-02 and 02-03 must add cli.py to their files_modified for end-to-end wiring verification
- Answer maps for specific GSD questions (new-project config, plan-phase CONTEXT.md) to be defined in workflow modules

## Self-Check: PASSED

- All 10 created/modified files verified present on disk
- Commit 7144f57 (Task 1) verified in git log
- Commit 31f5498 (Task 2) verified in git log
- 161 tests pass (excluding 1 slow integration test)
- CLI --help shows all 4 commands
- CLI --version works without SDK (lazy imports preserved)
- `openclawpack status` returns valid JSON from real project state

---
*Phase: 02-core-commands*
*Completed: 2026-02-22*
