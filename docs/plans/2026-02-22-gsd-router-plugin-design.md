# Design: `@openclawpack/gsd-router` OpenClaw Plugin

**Date:** 2026-02-22
**Status:** Approved

## Purpose

An OpenClaw plugin that forces the agent to evaluate every incoming task by complexity (simple / medium / hard) and routes medium and hard tasks through GSD via OpenClawPack, while letting simple tasks proceed directly.

## Architecture

Two-part plugin using OpenClaw's `agent:bootstrap` hook and `api.registerTool()`:

1. **Bootstrap Injection** — Injects `GSD-ROUTER.md` into the agent's system prompt every turn, containing mandatory task evaluation rubric and routing instructions.
2. **Tool Registration** — Exposes 4 tools wrapping the `openclawpack` CLI so the agent can call GSD commands.

## Task Evaluation Rubric

**SIMPLE** (do directly):
- Single-file changes (typo, bug fix, small tweak)
- Adding a function or method to existing code
- Config changes, dependency updates
- Quick research questions
- Estimated < 30 min of focused work

**MEDIUM** (use GSD):
- Multi-file feature additions
- New API endpoints with tests
- Refactoring across 3+ files
- Integration work between components
- Estimated 30 min - 2 hours

**HARD** (use GSD):
- New subsystem or module from scratch
- Architectural changes
- Cross-cutting concerns (auth, logging, etc.)
- Multi-phase projects with dependencies
- Estimated 2+ hours

## Tools

| Tool | CLI Command | Input | Output |
|------|-------------|-------|--------|
| `gsd_new_project` | `openclawpack new-project -i <idea>` | `idea: string`, `project_dir?: string` | `CommandResult` JSON |
| `gsd_plan_phase` | `openclawpack plan-phase <phase>` | `phase: number`, `project_dir?: string` | `CommandResult` JSON |
| `gsd_execute_phase` | `openclawpack execute-phase <phase>` | `phase: number`, `project_dir?: string` | `CommandResult` JSON |
| `gsd_status` | `openclawpack status` | `project_dir?: string` | `CommandResult` JSON |

## Plugin Config Schema

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `openclawpack_path` | string | `"openclawpack"` | Path to CLI binary |
| `default_timeout` | number | `300` | Subprocess timeout in seconds |
| `evaluation_enabled` | boolean | `true` | Toggle forced task evaluation |

## File Structure

```
openclawpack-plugin/
├── openclaw.plugin.json          # Plugin manifest
├── package.json                  # npm package
├── tsconfig.json                 # TypeScript config
├── src/
│   ├── index.ts                  # Plugin entry: registers hooks + tools
│   ├── tools.ts                  # 4 tool registrations
│   ├── exec.ts                   # Subprocess helper (runs openclawpack CLI)
│   └── bootstrap/
│       └── GSD-ROUTER.md         # Evaluation rubric + routing instructions
```

## Agent Flow

1. Agent receives task via message
2. Reads `GSD-ROUTER.md` from bootstrap (injected every turn)
3. Evaluates task against rubric: simple / medium / hard
4. **Simple** -> executes directly without GSD tools
5. **Medium** -> `gsd_new_project(idea)` -> `gsd_plan_phase(1)` -> `gsd_execute_phase(1)`
6. **Hard** -> same start, but expects multi-phase: iterates plan/execute for each phase, uses `gsd_status` to track progress

## Installation

```bash
# Local development
openclaw plugins install -l ./openclawpack-plugin

# Global extensions
cp -r openclawpack-plugin ~/.openclaw/extensions/
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Bootstrap injection over skill | Forces evaluation on every task, not opt-in |
| CLI subprocess over library import | OpenClawPack is Python, plugin is TypeScript. CLI is the cross-language bridge. |
| Agent does classification, not LLM-task | No extra LLM call. Agent reasons about complexity naturally as part of its response. |
| 4 discrete tools over 1 generic | Clear tool boundaries, better schema descriptions for the LLM |
