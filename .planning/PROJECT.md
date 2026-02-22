# OpenClawPack

## What This Is

A Python middleware layer that gives AI agents (primarily OpenClaw) full programmatic control over the Get Shit Done (GSD) framework through a CLI and importable library. It translates non-interactive CLI commands into Claude Code subprocess calls that execute GSD skills, returning structured JSON output that agents can parse and act on — enabling fully autonomous project lifecycle management from idea to working code.

## Core Value

An AI agent can go from "build me a todo app" to a fully planned GSD project with roadmap, without any human interaction — by calling a single CLI command.

## Requirements

### Validated

- ✓ CLI binary (`openclawpack`) that agents can shell out to — v1.0
- ✓ Python library core that the CLI wraps — v1.0
- ✓ Non-interactive `new-project` command (idea in, PROJECT.md + roadmap out) — v1.0
- ✓ Non-interactive `plan-phase` command — v1.0
- ✓ Non-interactive `execute-phase` command — v1.0
- ✓ Structured JSON output from every command — v1.0
- ✓ Project state querying (current phase, progress, blockers) — v1.0
- ✓ Event hooks / callbacks (phase complete, error, decision needed) — v1.0
- ✓ Multi-project management (run multiple GSD projects simultaneously) — v1.0
- ✓ Claude CLI subprocess orchestration (spawn `claude` processes, pipe input, parse output) — v1.0
- ✓ GSD artifact parsing (read/write .planning/ files programmatically) — v1.0
- ✓ Error handling and retry logic for subprocess failures — v1.0

### Active

(None yet — define in next milestone)

### Out of Scope

- Reimplementing GSD logic in Python — we delegate to GSD via Claude Code
- GUI or web interface — this is CLI/library only
- Replacing GSD's planning intelligence — we orchestrate, not replicate
- Supporting non-Claude AI backends — Claude Code is the execution engine
- Mobile app — agents are the primary consumers
- Database-backed state — GSD's .planning/ files are the source of truth
- WebSocket API — CLI stdout streaming is sufficient for agents
- Built-in scheduling/cron — agents have their own schedulers

## Context

- **GSD** (github.com/gsd-build/get-shit-done) is a Claude Code skill set that manages software projects through phases: questioning → research → requirements → roadmap → planning → execution → verification. It's interactive — uses AskUserQuestion prompts that block automation.
- **OpenClaw** (github.com/openclaw/openclaw) is an AI agent framework. It needs to drive GSD programmatically to handle complex multi-step software engineering tasks.
- **Claude Code CLI** (`claude`) supports `--print` mode and piped input, which can be leveraged to run GSD skills non-interactively by pre-filling answers.
- GSD stores all state in `.planning/` directory (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, config.json) — these are the integration surface.
- GSD's existing `gsd-tools.cjs` handles commits, config, and state management — we can read its artifacts but delegate mutation to GSD.

### Current State (after v1.0)

- **Source:** 3,410 LOC Python across 15 modules in `src/openclawpack/`
- **Tests:** 6,001 LOC Python, 382 unit tests (all passing)
- **Stack:** Python 3.10+, Pydantic, Typer, anyio, claude-agent-sdk
- **Architecture:** CLI (Typer) → API facade (async functions) → Workflow engine → Transport (Claude Agent SDK adapter) → Claude Code subprocess
- **Event system:** EventBus with 5 event types, sync/async handlers, CLI JSON stderr output
- **State:** .planning/ file parser with Pydantic models, multi-project registry with atomic JSON persistence

### Known Tech Debt

- 5 orphaned sync wrapper functions (superseded by async API facade)
- 2 workflow functions with `Any` return type annotation instead of `CommandResult`
- 1 stale header comment in cli.py (no functional impact)

## Constraints

- **Runtime**: Python 3.10+ — matches OpenClaw's ecosystem
- **Dependency**: Requires Claude Code CLI (`claude`) installed and authenticated
- **Dependency**: Requires GSD skills installed in Claude Code (`~/.claude/get-shit-done/`)
- **Subprocess model**: Must handle Claude Code's output format (markdown, tool calls, structured text)
- **State**: All project state lives in `.planning/` — no separate database

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Matches OpenClaw ecosystem, despite GSD being JS-based | ✓ Good — clean async/await, Pydantic models, Typer CLI |
| Claude CLI subprocess over direct API | Preserves GSD skill execution without reimplementation | ✓ Good — SDK adapter isolates alpha-status risk |
| CLI-first with library backing | Any agent can shell out; Python agents can also import | ✓ Good — both surfaces work, library adds event hooks |
| Middleware layer, not fork | GSD evolves independently; we adapt at the integration boundary | ✓ Good — adapter pattern in client.py is the only SDK touchpoint |
| JSON output for all commands | Agents need structured data, not markdown for humans | ✓ Good — Pydantic CommandResult schema, text format also available |
| Lazy imports throughout | PKG-04: --version/--help must work without Claude Code | ✓ Good — zero SDK loads until command execution |
| EventBus with str,Enum types | JSON-serializable event types for both library and CLI modes | ✓ Good — 5 types cover all lifecycle events |
| Adapter facade pattern for SDK | Isolate alpha-status claude-agent-sdk behind client.py | ✓ Good — only 1 file imports SDK, easy to swap |
| Answer injection via can_use_tool | Pre-fill GSD interactive prompts without modifying GSD | ✓ Good — 3-tier matching (exact/substring/fallback) handles all prompts |
| Atomic file writes for registry | Prevent corruption on concurrent access or crash | ✓ Good — tempfile + os.replace pattern |

---
*Last updated: 2026-02-22 after v1.0 milestone*
