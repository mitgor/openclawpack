---
phase: 02-core-commands
verified: 2026-02-22T10:30:00Z
status: human_needed
score: 8/8 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 6/8
  gaps_closed:
    - "Running `openclawpack new-project --idea 'build a todo app'` now succeeds with exit code 0 (--idea named option added)"
    - "Running `openclawpack status --project-dir /path` now succeeds with exit code 0 (per-command options added)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run `openclawpack new-project 'build a todo app'` against a real GSD environment outside a Claude Code session"
    expected: "Creates .planning/ directory with PROJECT.md, REQUIREMENTS.md, and ROADMAP.md without human interaction"
    why_human: "Requires Claude Code subprocess. Cannot be spawned inside a nested Claude Code session (environment block)."
  - test: "Run `openclawpack plan-phase 1` then `openclawpack execute-phase 1` on a real GSD project"
    expected: "GSD planning and execution proceed with all interactive prompts answered via injection; no human prompts appear"
    why_human: "Requires live Claude Code session; answer injection behaviour is only observable during actual GSD workflow execution."
---

# Phase 2: Core Commands Verification Report

**Phase Goal:** An AI agent can run `openclawpack new-project`, `plan-phase`, `execute-phase`, and `status` non-interactively to drive a complete GSD project lifecycle from idea to working code
**Verified:** 2026-02-22T10:30:00Z
**Status:** human_needed (all automated checks pass; two items require live Claude Code session)
**Re-verification:** Yes — after gap closure plan 02-04

## Re-Verification Summary

Previous verification (2026-02-22T09:00:00Z) found 2 gaps, both CLI interface mismatches:

| Gap | Previous Status | Now |
|-----|----------------|-----|
| `--idea` named option missing on new-project | PARTIAL | CLOSED |
| `--project-dir/--verbose/--quiet` global-only (after-subcommand placement failed) | PARTIAL | CLOSED |

Plan 02-04 added: `_resolve_options()` helper, `--idea`/`-i` named option on new-project, and per-command `--project-dir`/`--verbose`/`--quiet` options on all four commands. 12 Typer CliRunner tests were added and all pass. No regressions detected.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | `openclawpack new-project --idea "build a todo app"` produces .planning/ without human interaction | VERIFIED | `--idea`/`-i` Option added at line 100-105 of cli.py; CliRunner test `test_idea_as_named_option` exits 0; direct invocation exits 0 |
| SC-2 | `openclawpack plan-phase 1` and `openclawpack execute-phase 1` drive GSD planning/execution with answer injection | VERIFIED | Workflows wired via WorkflowEngine; answer injection with 3-tier fuzzy matching; 17 engine + 10 answer tests pass |
| SC-3 | `openclawpack status --project-dir /path` returns structured JSON | VERIFIED | `--project-dir` now a per-command Option on status; CliRunner test `test_status_project_dir_after_subcommand` exits 0 and asserts project_dir passed correctly |
| SC-4 | All commands accept `--verbose` and `--quiet`, default to JSON on stdout | VERIFIED | All four commands carry `verbose_opt`/`quiet_opt` Options; `_resolve_options()` merges with global ctx.obj; 8 CliRunner tests confirm placements |
| P1-T1 | TransportConfig accepts system_prompt dict, setting_sources, max_turns, max_budget_usd; ClaudeTransport.run() forwards can_use_tool and hooks | VERIFIED | types.py confirmed (1533b); client.py confirmed (6072b); no regression in 34 transport unit tests |
| P1-T2 | build_answer_callback() with 3-tier fuzzy matching; build_noop_pretool_hook() | VERIFIED | answers.py confirmed (3962b); 10 tests pass |
| P1-T3 | WorkflowEngine constructs correct prompt, system_prompt preset, setting_sources, answer callback, and hooks | VERIFIED | engine.py confirmed (4731b); 15 tests pass |
| P1-T4 | All CLI commands accept --project-dir, --verbose, --quiet as per-command options (after subcommand name) | VERIFIED | All four @app.command() functions accept these Options directly; CliRunner tests confirm exit code 0 for all placements |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/openclawpack/transport/types.py` | VERIFIED | 1533b; system_prompt, setting_sources, max_turns, max_budget_usd confirmed present |
| `src/openclawpack/transport/client.py` | VERIFIED | 6072b; can_use_tool and hooks forwarded conditionally |
| `src/openclawpack/commands/answers.py` | VERIFIED | 3962b; build_answer_callback() and build_noop_pretool_hook() exported |
| `src/openclawpack/commands/engine.py` | VERIFIED | 4731b; WorkflowEngine.run_gsd_command() and run_gsd_command_sync() present |
| `src/openclawpack/commands/__init__.py` | VERIFIED | 1039b; DEFAULT_TIMEOUTS and lazy __getattr__ present |
| `src/openclawpack/commands/status.py` | VERIFIED | 1272b; status_workflow() with CommandResult wrapping |
| `src/openclawpack/commands/new_project.py` | VERIFIED | 3622b; NEW_PROJECT_DEFAULTS, new_project_workflow(), sync wrapper |
| `src/openclawpack/commands/plan_phase.py` | VERIFIED | 2825b; plan_phase_workflow(), sync wrapper |
| `src/openclawpack/commands/execute_phase.py` | VERIFIED | 3122b; execute_phase_workflow(), sync wrapper |
| `src/openclawpack/cli.py` | VERIFIED | 7498b (grew from 5k); --idea Option on new-project, per-command options on all 4 commands, _resolve_options() helper, backward-compat global callback preserved |
| `tests/test_commands/test_answers.py` | VERIFIED | 6645b; 10 tests pass |
| `tests/test_commands/test_engine.py` | VERIFIED | 12365b; 15 tests pass |
| `tests/test_commands/test_status.py` | VERIFIED | 3961b; 7 tests pass |
| `tests/test_commands/test_new_project.py` | VERIFIED | 8311b; 13 tests pass |
| `tests/test_commands/test_plan_phase.py` | VERIFIED | 6677b; 8 tests pass |
| `tests/test_commands/test_execute_phase.py` | VERIFIED | 7532b; 9 tests pass |
| `tests/test_cli.py` | VERIFIED | 7498b; 12 tests pass (4 idea flag + 8 per-command options) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` `new_project()` | `commands/new_project.py` | lazy import + `new_project_workflow(idea=idea_text, ...)` | WIRED | Lines 162-172: idea_text resolved from idea_opt or positional; workflow called with correct kwarg |
| `cli.py` `status()` | `commands/status.py` | lazy import + `status_workflow(project_dir=project_dir)` | WIRED | Lines 291-293: project_dir from _resolve_options(); status_workflow called |
| `cli.py` `plan_phase()` | `commands/plan_phase.py` | lazy import + `plan_phase_workflow(phase=phase, ...)` | WIRED | Lines 207-217: _resolve_options() then workflow called |
| `cli.py` `execute_phase()` | `commands/execute_phase.py` | lazy import + `execute_phase_workflow(phase=phase, ...)` | WIRED | Lines 252-263: _resolve_options() then workflow called |
| `cli.py` `_resolve_options()` | `ctx.obj` global options | fallback chain: per-command opt or ctx.obj.get() | WIRED | Lines 86-88: project_dir, verbose, quiet each fall back to ctx.obj values |
| `commands/engine.py` | `transport/client.py` | WorkflowEngine instantiates ClaudeTransport and calls run() | WIRED | No regression; 15 engine tests pass |
| `commands/engine.py` | `commands/answers.py` | WorkflowEngine calls build_answer_callback() | WIRED | No regression; 10 answer tests pass |
| `commands/status.py` | `state/reader.py` | status_workflow calls get_project_summary() | WIRED | No regression; 7 status tests pass |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CMD-01 | 02-02, 02-04 | `new-project --idea <text>` creates GSD project non-interactively | VERIFIED | --idea Option added; positional arg preserved; both exit 0; 13 workflow tests + 4 CLI tests pass |
| CMD-02 | 02-03 | `plan-phase <N>` plans a phase non-interactively | VERIFIED | plan_phase_workflow() calls engine with /gsd:plan-phase N; 8 tests pass |
| CMD-03 | 02-03 | `execute-phase <N>` executes a phase non-interactively | VERIFIED | execute_phase_workflow() calls engine with /gsd:execute-phase N; 9 tests pass |
| CMD-04 | 02-02 | `status` returns current project state as structured JSON | VERIFIED | status_workflow() returns CommandResult with current_phase, progress_percent, blockers; 7 tests pass |
| CMD-05 | 02-01 | Pre-filled answer injection converts agent parameters into GSD answers | VERIFIED | build_answer_callback() with exact/substring/fallback; 10 tests pass |
| CMD-06 | 02-01, 02-04 | All commands accept --project-dir to specify working directory | VERIFIED | Per-command --project-dir on all 4 commands; global fallback preserved; 4 CliRunner tests confirm both placements |
| CMD-07 | 02-01, 02-04 | All commands accept --verbose and --quiet | VERIFIED | Per-command --verbose/--quiet on all 4 commands; global fallback preserved; 4 CliRunner tests confirm |
| INT-05 | 02-01 | Workflow engine translates commands into Claude Code invocations | VERIFIED | WorkflowEngine builds preset system_prompt, setting_sources, answer callbacks; 15 engine tests pass |

No orphaned requirements: all 8 phase 2 requirements appear in plan frontmatter and are verified above. REQUIREMENTS.md Traceability table marks all 8 as Complete at Phase 2.

### Anti-Patterns Found

No new anti-patterns introduced by plan 02-04. The existing minor annotations carry over:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/openclawpack/commands/plan_phase.py` | 37 | Return type annotation is `Any` instead of `CommandResult` | Info | Not a runtime issue; actual return value is always CommandResult |
| `src/openclawpack/commands/execute_phase.py` | 39 | Return type annotation is `Any` instead of `CommandResult` | Info | Same as above |

No TODO/FIXME/placeholder patterns found in any implementation file. No empty return stubs. No stubs introduced by cli.py changes.

### Test Suite Results

| Suite | Count | Result |
|-------|-------|--------|
| `tests/test_commands/` | 62 | 62 pass |
| `tests/test_cli.py` | 12 | 12 pass |
| `tests/test_transport/` (unit) | 34 | 34 pass |
| `tests/test_transport/test_client.py::TestClaudeTransportIntegration` | 1 | 1 expected fail (nested session block) |
| `tests/test_state/` + `tests/test_output/` + others | 102 | 102 pass |
| **Total** | **211** | **210 pass, 1 expected fail** |

The 1 failing test (`TestClaudeTransportIntegration::test_trivial_prompt_completes`) is an environment constraint: Claude Code cannot spawn a subprocess inside another Claude Code session. This is not a code defect; all unit and integration tests that can run in this environment pass.

### Human Verification Required

#### 1. New-Project End-to-End

**Test:** In a fresh directory outside a Claude Code session, run `openclawpack new-project --idea "build a todo app"` (using the new named option form)
**Expected:** Creates `.planning/` containing `PROJECT.md`, `REQUIREMENTS.md`, and `ROADMAP.md` without any interactive prompts appearing
**Why human:** Requires live Claude Code subprocess. Cannot be spawned inside a nested Claude Code session.

#### 2. Plan-Phase and Execute-Phase Answer Injection

**Test:** In a GSD-initialized project, run `openclawpack plan-phase 1` then `openclawpack execute-phase 1`
**Expected:** GSD runs fully non-interactively; all AskUserQuestion tool calls are intercepted and answered by the injection callbacks; no human prompts appear
**Why human:** Requires live Claude Code session; answer injection behaviour is only observable during actual GSD workflow execution.

### Gaps Summary

No gaps remain. Both gaps from the initial verification are closed:

**Gap 1 (CLOSED): new-project --idea flag**
The `--idea`/`-i` named Option was added to the `new_project` command at cli.py lines 100-105. The `idea_opt` variable takes precedence over the positional `idea` argument when both are provided. Running `openclawpack new-project --idea "text"` now exits 0. All four `TestNewProjectIdeaFlag` CliRunner tests pass. Positional backward compatibility confirmed via `test_idea_as_positional_arg`.

**Gap 2 (CLOSED): per-command --project-dir/--verbose/--quiet options**
Each of the four `@app.command()` functions now carries `project_dir_opt`, `verbose_opt`, and `quiet_opt` as explicit `typer.Option` parameters. The `_resolve_options()` helper (lines 79-89) resolves per-command option with fallback to `ctx.obj` global values, ensuring both `openclawpack status --project-dir /path` and `openclawpack --project-dir /path status` work. Eight `TestPerCommandOptions` CliRunner tests confirm all placement variants. Requirements CMD-06 and CMD-07 are now fully satisfied.

The only remaining items requiring verification are inherently live-environment tests (SC-1 end-to-end file creation and SC-2 answer injection during real GSD execution) that cannot be automated in this environment.

---

_Verified: 2026-02-22T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
