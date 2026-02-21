# Roadmap: OpenClawPack

## Overview

OpenClawPack delivers AI agent control over the GSD framework through five phases: first building reliable subprocess transport and typed data models as the foundation everything depends on, then layering the GSD-semantic CLI commands that make the tool useful, hardening with retry logic and session management, exposing a Python library API with event hooks for deeper agent integration, and finally adding multi-project management. After Phase 2, the tool is usable end-to-end. Each subsequent phase increases reliability and integration depth.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Transport layer, typed models, state parsing, and installable package skeleton
- [ ] **Phase 2: Core Commands** - Non-interactive GSD commands with workflow engine and answer injection
- [ ] **Phase 3: Reliability** - Retry logic, session continuity, output formats, and cost tracking
- [ ] **Phase 4: Library API and Events** - Async Python API and lifecycle event hook system
- [ ] **Phase 5: Multi-Project Management** - Project registry with add/list/remove commands

## Phase Details

### Phase 1: Foundation
**Goal**: A developer can install the package, spawn a Claude Code subprocess, parse .planning/ files into typed Python objects, and get structured JSON output with proper error handling
**Depends on**: Nothing (first phase)
**Requirements**: TRNS-01, TRNS-02, TRNS-03, TRNS-04, STATE-01, STATE-02, OUT-01, OUT-02, PKG-01, PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):
  1. Running `pip install .` in the repo installs `openclawpack` CLI binary, and `openclawpack --version` and `openclawpack --help` work without Claude Code installed
  2. The transport layer can spawn a Claude Code subprocess, stream stdout/stderr concurrently without deadlocks, and terminate gracefully on timeout
  3. Subprocess failures produce typed exceptions (CLINotFound, ProcessError, TimeoutError, JSONDecodeError) that callers can distinguish programmatically
  4. Calling the state parser on a .planning/ directory returns Pydantic models for config.json, STATE.md, ROADMAP.md, REQUIREMENTS.md, and PROJECT.md
  5. All transport and state operations return JSON matching the standard output schema: {success, result, errors, session_id, usage, duration_ms}
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Package skeleton, CLI entry point, and CommandResult output schema
- [ ] 01-02-PLAN.md — State parser: Pydantic models and .planning/ file readers
- [ ] 01-03-PLAN.md — Transport layer: claude-agent-sdk adapter with typed exceptions

### Phase 2: Core Commands
**Goal**: An AI agent can run `openclawpack new-project`, `plan-phase`, `execute-phase`, and `status` non-interactively to drive a complete GSD project lifecycle from idea to working code
**Depends on**: Phase 1
**Requirements**: CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07, INT-05
**Success Criteria** (what must be TRUE):
  1. Running `openclawpack new-project --idea "build a todo app"` produces a .planning/ directory with PROJECT.md, REQUIREMENTS.md, and ROADMAP.md -- without any human interaction
  2. Running `openclawpack plan-phase 1` and `openclawpack execute-phase 1` on a project drives GSD planning and execution for that phase, with all interactive prompts handled via pre-filled answer injection
  3. Running `openclawpack status --project-dir /path/to/project` returns structured JSON showing current phase, progress, and requirement completion
  4. All commands accept `--verbose` for detailed subprocess output and `--quiet` for minimal output, and default to structured JSON on stdout
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Reliability
**Goal**: Commands survive transient failures, maintain conversation context across multi-step workflows, and report cost/token usage to enable agent budget management
**Depends on**: Phase 2
**Requirements**: TRNS-05, TRNS-06, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. When a Claude Code subprocess fails due to rate limits or transient errors, the command retries with exponential backoff and eventually succeeds or reports a clear final failure
  2. A multi-step workflow (new-project followed by plan-phase) can resume the same Claude session via captured session ID, maintaining conversation context
  3. Running any command with `--output-format text` produces human-readable output instead of JSON
  4. Every command response includes token count and estimated cost in the usage metadata field
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Library API and Events
**Goal**: Python agents (OpenClaw) can import openclawpack as a library, call async functions that return typed models, and subscribe to lifecycle events for reactive behavior
**Depends on**: Phase 3
**Requirements**: INT-01, INT-02, INT-03, INT-04
**Success Criteria** (what must be TRUE):
  1. A Python script can `from openclawpack import create_project, plan_phase, execute_phase, get_status` and call them as async functions that return typed Pydantic models
  2. Library consumers can register callbacks for phase_complete, plan_complete, error, decision_needed, and progress_update events
  3. Event hooks fire in both library mode (Python callbacks) and CLI mode (JSON event lines to stdout)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Multi-Project Management
**Goal**: An agent can register, track, and manage multiple GSD projects simultaneously through a persistent project registry
**Depends on**: Phase 2
**Requirements**: STATE-03, STATE-04
**Success Criteria** (what must be TRUE):
  1. Running `openclawpack projects add /path/to/project` registers a project, and `openclawpack projects list` shows all registered projects with their paths and last-known state
  2. Running `openclawpack projects remove <name>` deregisters a project, and the registry persists across CLI invocations
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/3 | In Progress | - |
| 2. Core Commands | 0/3 | Not started | - |
| 3. Reliability | 0/2 | Not started | - |
| 4. Library API and Events | 0/2 | Not started | - |
| 5. Multi-Project Management | 0/1 | Not started | - |
