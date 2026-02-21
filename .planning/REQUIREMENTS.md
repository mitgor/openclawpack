# Requirements: OpenClawPack

**Defined:** 2026-02-21
**Core Value:** An AI agent can go from "build me a todo app" to a fully planned GSD project with roadmap, without any human interaction.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Transport

- [x] **TRNS-01**: CLI can spawn Claude Code subprocess with piped stdin/stdout and capture structured output
- [x] **TRNS-02**: Subprocess has configurable timeout with graceful termination (SIGTERM then SIGKILL)
- [x] **TRNS-03**: Concurrent stdout/stderr reading prevents pipe buffer deadlocks
- [x] **TRNS-04**: Typed exception hierarchy distinguishes CLINotFound, ProcessError, TimeoutError, JSONDecodeError, and GSD-specific errors
- [ ] **TRNS-05**: Retry logic with exponential backoff handles rate limits and transient subprocess failures
- [ ] **TRNS-06**: Session ID captured from Claude output and reusable across commands via --resume flag

### Commands

- [ ] **CMD-01**: `openclawpack new-project --idea <text_or_file>` creates a GSD project non-interactively (PROJECT.md through ROADMAP.md)
- [ ] **CMD-02**: `openclawpack plan-phase <N>` plans a phase non-interactively
- [ ] **CMD-03**: `openclawpack execute-phase <N>` executes a phase non-interactively
- [ ] **CMD-04**: `openclawpack status` returns current project state as structured JSON
- [ ] **CMD-05**: Pre-filled answer injection converts agent-supplied parameters into GSD --auto mode document format
- [ ] **CMD-06**: All commands accept `--project-dir` to specify working directory (defaults to cwd)
- [ ] **CMD-07**: All commands accept `--verbose` for detailed subprocess output and `--quiet` for minimal output

### Output

- [x] **OUT-01**: Every command returns JSON with schema: `{success, result, errors, session_id, usage, duration_ms}`
- [x] **OUT-02**: JSON output validated against Pydantic models with consistent schema across all commands
- [ ] **OUT-03**: `--output-format` flag supports `json` (default) and `text` (human-readable)
- [ ] **OUT-04**: Usage metadata includes token count and estimated cost per command invocation

### State

- [x] **STATE-01**: Parse .planning/config.json, STATE.md, ROADMAP.md, REQUIREMENTS.md, and PROJECT.md without subprocess
- [x] **STATE-02**: State queries return structured data: current phase, progress percentage, blocker list, requirement completion
- [ ] **STATE-03**: Multi-project registry tracks registered projects with paths and last-known state
- [ ] **STATE-04**: Projects can be registered, listed, and removed via `openclawpack projects add/list/remove`

### Integration

- [ ] **INT-01**: Python library API exposes async functions: `create_project()`, `plan_phase()`, `execute_phase()`, `get_status()`
- [ ] **INT-02**: Library returns typed Pydantic models, not raw dicts
- [ ] **INT-03**: Event hook system fires callbacks on: phase_complete, plan_complete, error, decision_needed, progress_update
- [ ] **INT-04**: Hooks work in both library mode (Python callbacks) and CLI mode (JSON events to stdout)
- [ ] **INT-05**: GSD workflow engine translates high-level commands into correct sequence of Claude Code invocations with proper GSD skill triggers

### Packaging

- [x] **PKG-01**: `pip install openclawpack` provides `openclawpack` CLI binary
- [x] **PKG-02**: Requires Python 3.10+ and Claude Code CLI installed
- [x] **PKG-03**: Zero required runtime dependencies beyond standard library + Pydantic + Typer + anyio
- [x] **PKG-04**: `openclawpack --version` and `openclawpack --help` work without Claude Code installed

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Orchestration

- **ADV-01**: Idempotent command design -- re-running a command detects partial completion and resumes
- **ADV-02**: Streaming progress via JSONL for long-running operations
- **ADV-03**: Verify-phase command for post-execution validation

### Scalability

- **SCALE-01**: Concurrent execution of multiple projects with per-project process isolation
- **SCALE-02**: Rate limit-aware scheduling across concurrent Claude sessions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reimplementing GSD logic in Python | GSD evolves independently; we delegate via Claude Code subprocess |
| GUI / web dashboard | Primary consumers are AI agents, not humans |
| Multi-LLM provider support | GSD is Claude Code-specific; adapting for GPT/Gemini is a different product |
| Swarm/multi-agent coordination | Let claude-flow handle intra-project parallelism |
| Plugin/extension system | Python library API is the extension surface |
| Database-backed state | GSD's .planning/ files are the source of truth |
| WebSocket API | CLI stdout streaming is sufficient for agents |
| Built-in scheduling/cron | Agents have their own schedulers |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRNS-01 | Phase 1 | Complete |
| TRNS-02 | Phase 1 | Complete |
| TRNS-03 | Phase 1 | Complete |
| TRNS-04 | Phase 1 | Complete |
| TRNS-05 | Phase 3 | Pending |
| TRNS-06 | Phase 3 | Pending |
| CMD-01 | Phase 2 | Pending |
| CMD-02 | Phase 2 | Pending |
| CMD-03 | Phase 2 | Pending |
| CMD-04 | Phase 2 | Pending |
| CMD-05 | Phase 2 | Pending |
| CMD-06 | Phase 2 | Pending |
| CMD-07 | Phase 2 | Pending |
| OUT-01 | Phase 1 | Complete |
| OUT-02 | Phase 1 | Complete |
| OUT-03 | Phase 3 | Pending |
| OUT-04 | Phase 3 | Pending |
| STATE-01 | Phase 1 | Complete |
| STATE-02 | Phase 1 | Complete |
| STATE-03 | Phase 5 | Pending |
| STATE-04 | Phase 5 | Pending |
| INT-01 | Phase 4 | Pending |
| INT-02 | Phase 4 | Pending |
| INT-03 | Phase 4 | Pending |
| INT-04 | Phase 4 | Pending |
| INT-05 | Phase 2 | Pending |
| PKG-01 | Phase 1 | Complete |
| PKG-02 | Phase 1 | Complete |
| PKG-03 | Phase 1 | Complete |
| PKG-04 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation*
