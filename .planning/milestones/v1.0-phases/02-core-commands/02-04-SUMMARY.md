---
phase: 02-core-commands
plan: 04
subsystem: cli
tags: [typer, cli, options, argument-parsing]

# Dependency graph
requires:
  - phase: 02-core-commands
    provides: "CLI app with global options and 4 subcommands (new-project, plan-phase, execute-phase, status)"
provides:
  - "--idea named option on new-project command"
  - "per-command --project-dir/--verbose/--quiet options on all 4 commands"
  - "_resolve_options() helper for global/per-command option fallback"
  - "12 CLI argument parsing tests via Typer CliRunner"
affects: [03-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["per-command options with global fallback via _resolve_options()", "dual positional/named argument with precedence resolution"]

key-files:
  created: [tests/test_cli.py]
  modified: [src/openclawpack/cli.py]

key-decisions:
  - "--idea option takes precedence over positional argument when both provided"
  - "_resolve_options() centralizes per-command/global option fallback logic"
  - "idea_file (--idea-file) still overrides both --idea and positional when provided"

patterns-established:
  - "Per-command options: each @app.command() function accepts --project-dir/--verbose/--quiet directly"
  - "Option resolution: per-command option or-fallback to ctx.obj global value"

requirements-completed: [CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07, INT-05]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 2 Plan 4: CLI Gap Closure Summary

**Per-command --project-dir/--verbose/--quiet options and --idea named flag on new-project for full ROADMAP success criteria compliance**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T07:55:26Z
- **Completed:** 2026-02-22T07:58:20Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `--idea`/`-i` named option on new-project command with positional backward compatibility
- Added `--project-dir`, `--verbose`, `--quiet` as per-command options on all 4 commands
- Created `_resolve_options()` helper for clean per-command/global fallback resolution
- Added 12 Typer CliRunner tests covering both gap fixes and backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix CLI interface -- add --idea option and per-command shared options** - `94c60ec` (feat)
2. **Task 2: Add Typer CliRunner tests for flag placement and --idea option** - `6ce4380` (test)

## Files Created/Modified
- `src/openclawpack/cli.py` - Added --idea option, per-command --project-dir/--verbose/--quiet, _resolve_options() helper
- `tests/test_cli.py` - 12 tests for CLI argument parsing (4 idea flag + 8 per-command options)

## Decisions Made
- `--idea` option takes precedence over positional argument when both are provided
- `_resolve_options()` centralizes the per-command/global option fallback pattern to avoid duplication
- `--idea-file` still overrides both `--idea` and positional argument when provided (existing behavior preserved)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All CLI interface gaps from 02-VERIFICATION.md are resolved
- Both global and per-command option placement work for all commands
- Phase 2 core commands fully complete; ready for Phase 3 integration

## Self-Check: PASSED

- [x] src/openclawpack/cli.py exists
- [x] tests/test_cli.py exists
- [x] 02-04-SUMMARY.md exists
- [x] Commit 94c60ec found
- [x] Commit 6ce4380 found

---
*Phase: 02-core-commands*
*Completed: 2026-02-22*
