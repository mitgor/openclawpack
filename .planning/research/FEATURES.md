# Feature Research

**Domain:** CLI middleware for AI agent orchestration (wrapping GSD framework via Claude Code subprocess)
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features agents assume exist. Missing these means the middleware is unusable for programmatic automation.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Non-interactive CLI execution** | Agents cannot answer interactive prompts. Every GSD command must accept all inputs upfront and run without TTY. This is the entire reason the middleware exists. | MEDIUM | Claude Code's `-p` / `--print` flag enables this. The hard part is pre-filling GSD's `AskUserQuestion` prompts with agent-supplied answers. |
| **Structured JSON output** | Agents parse structured data, not markdown prose. Every command must return JSON with a predictable schema (result, errors, session_id, metadata). | MEDIUM | Claude Code supports `--output-format json` and `--json-schema`. Use Pydantic models to define and validate output schemas. The Claude Agent SDK already streams JSONL. |
| **Subprocess lifecycle management** | Spawning `claude -p` processes, piping prompts, capturing stdout/stderr, handling timeouts, and terminating hung processes. This is the core mechanical requirement. | HIGH | Reference implementation exists in `claude-agent-sdk-python` (`SubprocessCLITransport`): uses `anyio.open_process`, 5s termination grace period, 1MB JSON buffer, 10MB stderr limit. We should build on these proven patterns rather than inventing our own. |
| **Error handling with typed exceptions** | Agents need machine-readable error categories to decide retry vs abort vs escalate. Raw stderr strings are useless for programmatic decision-making. | MEDIUM | Follow the Claude Agent SDK's exception hierarchy: base error, CLI not found, connection error, process error (with exit code), JSON decode error. Add GSD-specific errors: phase not found, state invalid, planning directory missing. |
| **Session management (continue/resume)** | Multi-step GSD workflows (plan then execute then verify) require conversation continuity. Without session tracking, each command loses context. | MEDIUM | Claude Code provides `--resume <session_id>` and `--continue` flags. Capture `session_id` from JSON output, store per-project, pass on subsequent calls. |
| **GSD artifact reading** | The middleware must parse `.planning/` files (PROJECT.md, STATE.md, ROADMAP.md, config.json) to report project status, current phase, blockers, and progress without spawning Claude. | LOW | These are plain text/JSON/markdown files. Parse with standard Python libraries. `config.json` is already JSON. Markdown files follow predictable GSD templates. |
| **Project state querying** | "What phase am I on? What's the progress? What are the blockers?" Agents need this constantly for decision-making without burning Claude API tokens. | LOW | Read STATE.md + ROADMAP.md + config.json directly. Parse the structured sections. Return as JSON. No subprocess needed. |
| **CLI binary entry point** | Any agent (not just Python) must be able to shell out to `openclawpack <command>`. A pip-installable CLI binary is the universal integration surface. | LOW | Standard Python packaging with `[project.scripts]` entry point. Click or Typer for CLI framework. |
| **Retry logic for transient failures** | Claude API rate limits, network blips, and subprocess crashes happen. Without automatic retry with backoff, agents hit failures they cannot recover from. | MEDIUM | Exponential backoff with jitter. Configurable max retries. Distinguish retryable (rate limit, timeout, connection) from fatal (auth failure, invalid input). |

### Differentiators (Competitive Advantage)

Features that set OpenClawPack apart from raw subprocess calls or existing tools like claude-flow/claude-mpm.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **GSD workflow semantics** | Unlike generic agent orchestrators (claude-flow, CAO), we understand GSD's specific workflow: questioning -> research -> requirements -> roadmap -> planning -> execution -> verification. This means `openclawpack new-project --idea "build a todo app"` does the right thing without the agent needing to know GSD internals. | HIGH | This is the core differentiator. We translate high-level intent ("create project", "execute next phase") into the correct sequence of Claude Code subprocess calls with GSD skill invocations. Competitors wrap generic Claude; we wrap a specific methodology. |
| **Pre-filled answer injection** | GSD's interactive questioning phase uses `AskUserQuestion` which blocks automation. We solve this by accepting a structured document or answer set upfront and injecting them into the Claude prompt context, enabling GSD's `--auto` mode programmatically. | HIGH | GSD already has `--auto` mode that accepts a document. We formalize this: accept a JSON spec of project parameters, convert to the document format GSD expects, pass via `--append-system-prompt` or stdin pipe. |
| **Event hooks / callbacks** | Notify the calling agent when: phase completes, error occurs, decision needed, progress updates. This enables reactive agent behavior (e.g., agent starts next phase immediately when current one finishes). | MEDIUM | The Claude Agent SDK has `PreToolUse` and `PostToolResult` hooks. We add GSD-semantic hooks: `on_phase_complete`, `on_plan_complete`, `on_blocker_found`, `on_decision_needed`. Implement as Python callbacks (for library use) and webhook/stdout events (for CLI use). |
| **Multi-project management** | Run multiple GSD projects simultaneously with isolated state. An orchestrating agent managing a microservices system needs parallel project lifecycles. | MEDIUM | Each project is a directory with its own `.planning/`. Track active projects in a registry (JSON file or SQLite). Provide `openclawpack projects list/add/remove/status`. Subprocess isolation is natural since each `claude -p` call gets its own `--cwd`. |
| **Python library API (importable)** | Python agents (like OpenClaw) can `from openclawpack import create_project` instead of shelling out. Typed return values, async generators, context managers. Richer than CLI. | MEDIUM | The CLI is a thin wrapper over the library. Library uses async/await throughout. Return Pydantic models, not dicts. Stream events via async generators. This is how the Claude Agent SDK works and it's the right pattern. |
| **Idempotent command design** | Running the same command twice should not corrupt state. If `execute-phase` is interrupted and re-run, it should detect partial completion and resume. Agents retry aggressively; non-idempotent commands break. | HIGH | Read STATE.md before each operation. Detect "already completed" vs "in progress" vs "not started". For in-progress operations, offer resume (pass `--resume` with saved session_id). This requires careful state machine design per command. |
| **Cost/token tracking** | Report how many tokens/dollars each operation consumed. Agents managing budgets need this for cost-aware decision-making. | LOW | Claude Code's JSON output includes usage metadata. Aggregate per-command, per-phase, per-project. Store in project state. |
| **Streaming progress** | Real-time progress updates via `stream-json` output format. Agents can monitor long-running operations (e.g., research phase) without polling. | MEDIUM | Use `--output-format stream-json --verbose --include-partial-messages`. Parse the JSONL stream. Emit filtered, GSD-semantic progress events (not raw Claude token deltas). |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create maintenance burden, architectural complexity, or scope creep without proportional value.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Reimplementing GSD logic in Python** | "We could skip the subprocess overhead and run GSD natively" | GSD is 40+ workflow files, 50+ templates, and a tool CLI written for Claude Code's skill system. Reimplementing means maintaining a fork that drifts from upstream. GSD evolves independently; a fork becomes a dead end. The Claude Code subprocess is the execution engine by design. | Delegate to GSD via Claude Code subprocess. Optimize the integration boundary (faster parsing, session reuse), not the engine. |
| **GUI / web dashboard** | "Visualize project state, progress, and agent activity" | Doubles the surface area. Adds frontend dependencies, server process, auth. The primary consumer is an AI agent, not a human staring at a dashboard. | Expose state via structured JSON queries. If humans want a dashboard, a separate tool reads our JSON output. Keep the middleware headless. |
| **Multi-LLM provider support** | "Support GPT, Gemini, local models alongside Claude" | GSD is Claude Code-specific. Its prompts, tool usage patterns, and skill system are designed for Claude's capabilities. Multi-provider would require rewriting or abstracting every GSD interaction. | Stay Claude-only. This is a Claude Code middleware, not a generic AI orchestrator. If someone wants GPT, they need a different framework, not an adapter layer bolted onto ours. |
| **Swarm/multi-agent coordination** | "Multiple Claude instances working in parallel on the same project" | Claude-flow and CAO already solve this (tmux sessions, MCP coordination). Building it into the middleware conflates orchestration (our job) with coordination (a different layer). Also, concurrent writes to `.planning/` files cause corruption. | Single-agent-per-project model. For parallelism, the orchestrating agent (OpenClaw) spawns multiple OpenClawPack instances on different projects. Let claude-flow handle intra-project parallelism if needed. |
| **Plugin/extension system** | "Let users add custom workflow steps, custom output formats, custom hooks" | Plugin systems are maintenance black holes. They require stable APIs, versioning, documentation, and debugging of third-party code. The user base (AI agents) doesn't write plugins. | Expose clean Python API. Users extend by importing the library and composing functions. Unix philosophy: do one thing well, pipe output to other tools. |
| **Database-backed state** | "SQLite or PostgreSQL for project state instead of flat files" | GSD stores state in `.planning/` directory by design. Introducing a database creates a second source of truth, requires migrations, adds a dependency, and breaks GSD's git-based state model. | Read `.planning/` files directly. For derived data (multi-project registry, usage tracking), a lightweight JSON file or SQLite is acceptable but never as the primary state store. |
| **Real-time WebSocket API** | "Stream events to connected clients over WebSocket" | Adds a server process, connection management, reconnection logic, and a client SDK. For a CLI tool consumed by agents that shell out, this is massive over-engineering. | Streaming JSON to stdout (`stream-json` format). Agents read the stream. If a persistent connection is needed later, it's a separate service that wraps our CLI. |
| **Built-in scheduling / cron** | "Schedule phase execution at specific times" | Agents already have their own scheduling. Adding scheduling to the middleware duplicates capability that belongs in the orchestration layer (OpenClaw), not the execution layer (OpenClawPack). | Expose a `--dry-run` flag so agents can plan commands ahead of time. Let the agent's scheduler invoke `openclawpack` at the right moment. |

## Feature Dependencies

```
[Non-interactive CLI execution]
    |-- requires --> [Subprocess lifecycle management]
    |                    |-- requires --> [Error handling with typed exceptions]
    |                    |-- requires --> [Retry logic for transient failures]
    |
    |-- requires --> [Structured JSON output]
    |                    |-- enhances --> [Session management]
    |                    |-- enhances --> [Cost/token tracking]
    |
    |-- requires --> [GSD artifact reading]
                         |-- enables --> [Project state querying]
                         |-- enables --> [Multi-project management]
                         |-- enables --> [Idempotent command design]

[Pre-filled answer injection]
    |-- requires --> [Non-interactive CLI execution]
    |-- requires --> [Structured JSON output]

[Event hooks / callbacks]
    |-- requires --> [Streaming progress]
    |-- requires --> [Subprocess lifecycle management]

[Python library API]
    |-- wraps --> [All CLI features]
    |-- enhances --> [Event hooks / callbacks] (native async callbacks)

[CLI binary entry point]
    |-- wraps --> [Python library API]
```

### Dependency Notes

- **Subprocess lifecycle is the foundation:** Everything else depends on being able to reliably spawn, communicate with, and terminate Claude Code processes. Build this first and build it well.
- **GSD artifact reading is independent of subprocess:** Can be built and tested without Claude Code installed. Provides value immediately (state queries without API cost).
- **Event hooks require streaming:** Cannot emit events without parsing the stream-json output. Build streaming first, then layer hooks on top.
- **Idempotent design requires state reading:** Must read current state to detect "already done" vs "needs work". GSD artifact reading is prerequisite.
- **Multi-project management requires state querying:** Cannot list project statuses without being able to read individual project states.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to validate that an agent can drive GSD programmatically.

- [ ] **Subprocess lifecycle management** -- The core mechanical requirement. Spawn claude, pipe input, capture output, handle errors and timeouts.
- [ ] **Non-interactive CLI execution** -- `openclawpack new-project`, `plan-phase`, `execute-phase`, `verify-phase` commands that run without TTY.
- [ ] **Structured JSON output** -- Every command returns parseable JSON with result, errors, session_id.
- [ ] **Error handling with typed exceptions** -- Machine-readable error categories for retry/abort decisions.
- [ ] **GSD artifact reading** -- Parse `.planning/` files for state without subprocess.
- [ ] **Project state querying** -- `openclawpack status` returns current phase, progress, blockers as JSON.
- [ ] **CLI binary entry point** -- `pip install openclawpack` gives agents a binary to call.
- [ ] **Pre-filled answer injection** -- Support `--auto` with idea document for fully autonomous project creation.

### Add After Validation (v1.x)

Features to add once core is working and agents are successfully driving GSD.

- [ ] **Session management** -- When agents need multi-step workflows with conversation continuity.
- [ ] **Retry logic** -- When real-world reliability becomes the bottleneck (it will quickly).
- [ ] **Python library API** -- When Python agents (OpenClaw) want richer integration than shelling out.
- [ ] **Event hooks** -- When agents need reactive behavior (start next phase when current completes).
- [ ] **Cost tracking** -- When agents managing budgets need visibility into token consumption.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Multi-project management** -- Defer until single-project workflow is solid and agents demonstrate need for parallel projects.
- [ ] **Idempotent command design** -- Defer until agents hitting idempotency issues in practice. Add per-command as issues surface.
- [ ] **Streaming progress** -- Defer until long-running operations (research, execution) cause timeout issues for agents.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Subprocess lifecycle management | HIGH | HIGH | P1 |
| Non-interactive CLI execution | HIGH | MEDIUM | P1 |
| Structured JSON output | HIGH | MEDIUM | P1 |
| Error handling (typed exceptions) | HIGH | LOW | P1 |
| GSD artifact reading | HIGH | LOW | P1 |
| Project state querying | HIGH | LOW | P1 |
| CLI binary entry point | HIGH | LOW | P1 |
| Pre-filled answer injection | HIGH | HIGH | P1 |
| Retry logic | HIGH | MEDIUM | P2 |
| Session management | MEDIUM | MEDIUM | P2 |
| Python library API | MEDIUM | MEDIUM | P2 |
| Event hooks / callbacks | MEDIUM | MEDIUM | P2 |
| Cost/token tracking | LOW | LOW | P2 |
| Multi-project management | MEDIUM | MEDIUM | P3 |
| Idempotent command design | MEDIUM | HIGH | P3 |
| Streaming progress | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch -- agents cannot use the tool without these
- P2: Should have, add when possible -- agents work better with these
- P3: Nice to have, future consideration -- valuable but not blocking

## Competitor Feature Analysis

| Feature | claude-flow (ruvnet) | claude-mpm (bobmatnyc) | CLI Agent Orchestrator (AWS) | Claude Agent SDK (Anthropic) | OpenClawPack (Ours) |
|---------|---------------------|----------------------|---------------------------|---------------------------|-------------------|
| **Subprocess management** | tmux sessions, multi-agent swarm | Custom process manager, isolated environments | tmux sessions, hierarchical | `anyio.open_process`, PIPE-based | Build on Agent SDK pattern, PIPE-based |
| **Structured output** | MCP protocol (JSON-RPC 2.0) | Event bus, structured summaries | REST API on localhost:9889 | JSONL stream, typed message objects | JSON output with Pydantic schemas |
| **State management** | Agent memory (project/local/user scopes) | Session resume with 10k-token summaries | Terminal status tracking (IDLE/BUSY/ERROR) | Session ID capture and resume | `.planning/` directory (GSD native) |
| **Multi-project** | Swarm coordination across projects | Not primary focus | Flows for multi-project scheduling | Per-directory working directory | Project registry, per-directory isolation |
| **Event hooks** | 12 context-triggered workers | 15+ event hooks via event bus | Cron-based Flows | PreToolUse / PostToolResult hooks | GSD-semantic hooks (phase_complete, etc.) |
| **Error recovery** | Anti-drift protection, checkpoints | Health diagnostics, auto-fix, fail-fast | Message queuing, graceful shutdown | Typed exception hierarchy | Typed exceptions + GSD-specific errors + retry |
| **GSD awareness** | None (generic Claude orchestrator) | None (generic PM framework) | None (generic CLI orchestrator) | None (generic SDK) | Full GSD workflow understanding |
| **Primary user** | Developers running multi-agent systems | Developers managing Claude projects | Enterprise multi-tool orchestration | Developers building Claude agents | AI agents driving GSD autonomously |

**Key insight:** Every competitor is a *generic* Claude orchestrator. None understand GSD's specific methodology, state model, or workflow semantics. Our differentiator is not better subprocess management -- it is GSD-native intelligence that translates agent intent into the correct GSD operations. The mechanical layer (subprocess, JSON, errors) is table stakes we must match. The semantic layer (GSD workflows, `.planning/` state, phase lifecycle) is where we win.

## Sources

- [Claude Code Headless Mode Docs](https://code.claude.com/docs/en/headless) -- Official CLI automation reference (HIGH confidence)
- [Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python) -- Subprocess transport implementation, hooks, typed errors (HIGH confidence)
- [claude-flow](https://github.com/ruvnet/claude-flow) -- Multi-agent orchestration platform for Claude (MEDIUM confidence)
- [claude-mpm](https://github.com/bobmatnyc/claude-mpm) -- Subprocess orchestration layer with event hooks (MEDIUM confidence)
- [CLI Agent Orchestrator (AWS)](https://github.com/awslabs/cli-agent-orchestrator) -- Multi-agent CLI framework (MEDIUM confidence)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) -- Handoff patterns, guardrails, structured output, tracing (MEDIUM confidence)
- [Error Recovery Patterns](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development) -- Retry logic, validation patterns (LOW confidence)
- [AI Agent Anti-Patterns](https://zircon.tech/blog/agentic-frameworks-in-2026-what-actually-works-in-production/) -- Over-engineering pitfalls (MEDIUM confidence)
- [Event-Driven Multi-Agent Design Patterns](https://www.confluent.io/blog/event-driven-multi-agent-systems/) -- Event architecture patterns (MEDIUM confidence)

---
*Feature research for: CLI middleware / AI agent orchestration*
*Researched: 2026-02-21*
