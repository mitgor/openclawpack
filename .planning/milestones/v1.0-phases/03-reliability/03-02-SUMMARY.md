---
phase: 03-reliability
plan: 02
subsystem: output
tags: [text-format, output-format, usage-metadata, cost-tracking, formatter]

requires:
  - phase: 03-reliability
    plan: 01
    provides: "Retry logic, _run_once() with usage enrichment"
provides:
  - "format_text() function converting CommandResult to human-readable string"
  - "CommandResult.to_text() convenience method"
  - "--output-format text|json CLI flag with dispatch in _output() helper"
  - "Status command returns zero usage instead of None for local-only commands"
affects: [library-api, all-commands]

tech-stack:
  added: []
  patterns: ["output format dispatch", "zero-usage for local commands"]

key-files:
  created:
    - "src/openclawpack/output/formatter.py"
    - "tests/test_output/test_formatter.py"
  modified:
    - "src/openclawpack/output/schema.py"
    - "src/openclawpack/output/__init__.py"
    - "src/openclawpack/cli.py"
    - "tests/test_cli.py"

key-decisions:
  - "format_text() uses comma-formatted numbers for tokens and duration"
  - "Long results truncated at 2000 chars with '... (truncated)' suffix"
  - "Cost displayed as $0.0000 format (4 decimal places)"
  - "--output-format is a global option on app callback, read from ctx.obj in each command"
  - "Status command fills usage with zeros when None (prevents downstream KeyError)"
  - "to_text() method uses lazy import of format_text to avoid circular imports"

patterns-established:
  - "Output format dispatch: _output() helper takes output_format string"
  - "Local command zero-usage: always provide usage dict, even for file-only commands"

requirements-completed: [OUT-03, OUT-04]

duration: 4min
completed: 2026-02-22
---

# Plan 03-02: Text Formatter and Output Format Summary

**Added --output-format text|json CLI flag with format_text() formatter and usage metadata enrichment**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 4

## Accomplishments
- Created formatter.py with format_text() for human-readable CommandResult display
- Added to_text() convenience method to CommandResult
- Exported format_text from output package __init__.py
- Added --output-format text|json global CLI flag on app callback
- Updated _output() helper to dispatch between JSON and text format
- Updated status command to fill usage with zeros when None (Pitfall 4 prevention)
- Added 15 formatter tests + 9 CLI tests (output format + zero usage + resume flags)

## Files Created/Modified
- `src/openclawpack/output/formatter.py` - NEW: format_text() function
- `src/openclawpack/output/schema.py` - Added to_text() method
- `src/openclawpack/output/__init__.py` - Exported format_text
- `src/openclawpack/cli.py` - --output-format flag, updated _output() dispatch, status zero usage
- `tests/test_output/test_formatter.py` - NEW: 15 tests for format_text
- `tests/test_cli.py` - 9 tests for output format and resume flags

## Decisions Made
- --output-format is global (not per-command) since all commands share the same output dispatch
- Zero usage dict for status avoids breaking agents that expect usage.total_cost_usd
- Comma formatting (1,500) for tokens and duration for better readability

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Text output format available for all commands
- Usage metadata always includes token counts and cost from SDK
- Ready for Phase 4: Library API and Events

---
*Phase: 03-reliability*
*Completed: 2026-02-22*
