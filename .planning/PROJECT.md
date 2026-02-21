# OpenClawPack

## What This Is

A Python middleware layer that gives AI agents (primarily OpenClaw) full programmatic control over the Get Shit Done (GSD) framework through a CLI and importable library. It translates non-interactive CLI commands into Claude Code subprocess calls that execute GSD skills, returning structured JSON output that agents can parse and act on — enabling fully autonomous project lifecycle management from idea to working code.

## Core Value

An AI agent can go from "build me a todo app" to a fully planned GSD project with roadmap, without any human interaction — by calling a single CLI command.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] CLI binary (`openclawpack`) that agents can shell out to
- [ ] Python library core that the CLI wraps
- [ ] Non-interactive `new-project` command (idea in, PROJECT.md + roadmap out)
- [ ] Non-interactive `plan-phase` command
- [ ] Non-interactive `execute-phase` command
- [ ] Structured JSON output from every command
- [ ] Project state querying (current phase, progress, blockers)
- [ ] Event hooks / callbacks (phase complete, error, decision needed)
- [ ] Multi-project management (run multiple GSD projects simultaneously)
- [ ] Claude CLI subprocess orchestration (spawn `claude` processes, pipe input, parse output)
- [ ] GSD artifact parsing (read/write .planning/ files programmatically)
- [ ] Error handling and retry logic for subprocess failures

### Out of Scope

- Reimplementing GSD logic in Python — we delegate to GSD via Claude Code
- GUI or web interface — this is CLI/library only
- Replacing GSD's planning intelligence — we orchestrate, not replicate
- Supporting non-Claude AI backends — Claude Code is the execution engine

## Context

- **GSD** (github.com/gsd-build/get-shit-done) is a Claude Code skill set that manages software projects through phases: questioning → research → requirements → roadmap → planning → execution → verification. It's interactive — uses AskUserQuestion prompts that block automation.
- **OpenClaw** (github.com/openclaw/openclaw) is an AI agent framework. It needs to drive GSD programmatically to handle complex multi-step software engineering tasks.
- **Claude Code CLI** (`claude`) supports `--print` mode and piped input, which can be leveraged to run GSD skills non-interactively by pre-filling answers.
- GSD stores all state in `.planning/` directory (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, config.json) — these are the integration surface.
- GSD's existing `gsd-tools.cjs` handles commits, config, and state management — we can read its artifacts but delegate mutation to GSD.

## Constraints

- **Runtime**: Python 3.10+ — matches OpenClaw's ecosystem
- **Dependency**: Requires Claude Code CLI (`claude`) installed and authenticated
- **Dependency**: Requires GSD skills installed in Claude Code (`~/.claude/get-shit-done/`)
- **Subprocess model**: Must handle Claude Code's output format (markdown, tool calls, structured text)
- **State**: All project state lives in `.planning/` — no separate database

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Matches OpenClaw ecosystem, despite GSD being JS-based | — Pending |
| Claude CLI subprocess over direct API | Preserves GSD skill execution without reimplementation | — Pending |
| CLI-first with library backing | Any agent can shell out; Python agents can also import | — Pending |
| Middleware layer, not fork | GSD evolves independently; we adapt at the integration boundary | — Pending |
| JSON output for all commands | Agents need structured data, not markdown for humans | — Pending |

---
*Last updated: 2026-02-21 after initialization*
