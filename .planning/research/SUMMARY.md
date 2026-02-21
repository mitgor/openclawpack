# Project Research Summary

**Project:** OpenClawPack
**Domain:** Python CLI middleware for AI agent orchestration (Claude Code / GSD framework)
**Researched:** 2026-02-21
**Confidence:** HIGH

## Executive Summary

OpenClawPack is a Python middleware that gives AI agents programmatic control over the Get Shit Done (GSD) framework by wrapping Claude Code CLI subprocess calls in a typed, non-interactive interface. The single most consequential research finding is the existence of the **Claude Agent SDK** (`claude-agent-sdk` v0.1.39), an official Anthropic Python package that eliminates roughly 60% of the planned build by providing subprocess lifecycle management, NDJSON streaming, typed message objects, hook callbacks, and session management out of the box. This SDK should be the foundation of OpenClawPack's transport layer, not raw subprocess calls. The recommended stack (Python 3.10+, Typer, Pydantic v2, anyio, pluggy) is mature, well-documented, and carries HIGH confidence across all sources.

The architecture follows a clean four-layer design: Public API (CLI + library), Workflow Engine (GSD-semantic orchestration), Subprocess Transport (Claude Agent SDK or raw async subprocess), and State Layer (read-only `.planning/` file parsing). The critical differentiator is not better subprocess management -- competitors (claude-flow, claude-mpm, CLI Agent Orchestrator) already do that. The differentiator is **GSD-native intelligence**: understanding GSD's specific phase lifecycle, artifact structure, and interactive questioning model well enough to translate a single agent command into the correct multi-step Claude Code invocation sequence. Pre-filled answer injection (bypassing GSD's interactive `AskUserQuestion` prompts) is the core innovation that makes autonomous project creation possible.

The primary risks are subprocess deadlocks from pipe buffer saturation, output format fragility as Claude Code CLI evolves (still v0.x alpha), error amplification cascades in multi-agent pipelines, and `.planning/` file race conditions in concurrent operations. All six critical pitfalls map to Phase 1 or Phase 2 of the build, meaning the foundation must be rock-solid before adding features. The strongest mitigation is architectural: OpenClawPack should be **read-only** for `.planning/` files, delegating all state mutations to GSD via Claude subprocess. This eliminates an entire class of race conditions and state drift bugs.

## Key Findings

### Recommended Stack

The stack is anchored by the Claude Agent SDK for Claude Code integration and modern Python best practices. Every library was chosen with a clear "why not the alternative" rationale. Confidence is HIGH across the board -- these are all production-grade, actively maintained packages.

**Core technologies:**
- **claude-agent-sdk** (0.1.39): Claude Code integration -- provides subprocess lifecycle, typed messages, hooks, session management. Eliminates custom transport layer build.
- **Typer** (0.24.0): CLI framework -- type-hint-driven command definitions, auto-completion, Rich output. Built on Click.
- **Pydantic** (2.12.5): Data models and validation -- GSD artifact models, command I/O schemas, config management. JSON Schema generation built-in.
- **Rich** (14.3.3): Terminal output -- tables, progress bars, markdown rendering. Already a Typer dependency.
- **anyio** (4.12.1): Async abstraction -- structured concurrency for managing concurrent Claude sessions with proper cancellation.
- **pluggy** (1.6.0): Plugin/hook system -- user extensibility for lifecycle events beyond Claude-level hooks.
- **orjson** (3.11.7): Fast JSON -- 2-10x faster than stdlib. Critical for parsing high-volume NDJSON streams.

**Critical version concern:** claude-agent-sdk is at v0.1.x (alpha). Expect breaking changes. Mitigate by pinning version, wrapping SDK calls behind an internal adapter interface, and running integration tests that catch API changes early.

**Dev tooling:** uv (package manager), ruff (linter/formatter), mypy (type checking), pytest + pytest-asyncio (testing). All HIGH confidence, industry-standard 2026 choices.

### Expected Features

**Must have (table stakes -- agents cannot use the tool without these):**
- Non-interactive CLI execution (the entire reason the middleware exists)
- Structured JSON output from every command
- Subprocess lifecycle management (spawn, stream, timeout, kill)
- Error handling with typed exceptions (retry vs abort decisions)
- GSD artifact reading (parse `.planning/` without spawning Claude)
- Project state querying (`openclawpack status` as JSON)
- CLI binary entry point (`pip install openclawpack`)
- Pre-filled answer injection (bypass GSD's interactive prompts)
- Retry logic for transient failures (rate limits, timeouts)

**Should have (differentiators -- what makes this better than raw subprocess calls):**
- GSD workflow semantics (translate "new-project" into correct multi-step sequence)
- Session management (multi-step workflows with conversation continuity)
- Python library API (importable async functions, not just CLI)
- Event hooks/callbacks (phase complete, error, decision needed)
- Cost/token tracking (budget-aware agent decision-making)

**Defer (v2+):**
- Multi-project management (get single-project right first)
- Idempotent command design (add per-command as issues surface)
- Streaming progress (defer until timeout issues appear)

**Anti-features (explicitly avoid):**
- Reimplementing GSD logic in Python (maintain a wrapper, not a fork)
- GUI/web dashboard (agents are the consumer, not humans)
- Multi-LLM provider support (GSD is Claude-specific by design)
- Swarm/multi-agent coordination (let claude-flow handle that)
- Database-backed state (`.planning/` flat files are the contract)

### Architecture Approach

The architecture is a layered system with clear boundaries: Public API (CLI + library dual interface), Command Router, Workflow Engine (GSD-semantic orchestrators), Subprocess Transport (process lifecycle + NDJSON stream parsing + error/retry), and State Layer (read-only `.planning/` parsing + project registry). The critical design decision is the **read-only principle**: OpenClawPack reads `.planning/` files for status queries but never writes them directly -- all mutations flow through GSD via Claude Code subprocess calls. This preserves GSD as the single source of truth and eliminates state synchronization bugs.

**Major components:**
1. **Public API Layer** (CLI + Library) -- Dual interface: Typer CLI for shell-out agents, async Python API for importable use. CLI is a thin wrapper over the library.
2. **Workflow Engine** -- Encodes multi-step GSD operations (new-project, plan-phase, execute-phase) as sequences of subprocess calls + state reads + hook dispatches. One workflow class per GSD command.
3. **Subprocess Transport** -- Wraps Claude Agent SDK (or raw async subprocess). Manages process lifecycle, NDJSON stream parsing, timeout handling, and retry logic. Isolated behind an interface for testability and future SDK migration.
4. **State Layer** -- Parses `.planning/` files into Pydantic models. Read-only for GSD artifacts. Manages its own state (project registry, session IDs) in `~/.openclawpack/`.
5. **Event Hook System** -- Lightweight pub/sub for lifecycle events. Workflows emit; consumers subscribe. Supports sync and async callbacks.

**Key architectural pattern:** Transport and State layers are independent of each other and can be built in parallel. Workflows depend on both. CLI depends on workflows through the API layer.

### Critical Pitfalls

1. **Subprocess deadlock from pipe buffer saturation** -- Use async subprocess with concurrent stdout/stderr readers. Never call `wait()` without draining both pipes. Set `--max-turns` and `--max-budget-usd` as hard safety rails. Must be correct in Phase 1.

2. **Output format fragility** -- Claude Code CLI is v0.x alpha; output format is not a versioned API. Build a parsing abstraction with Pydantic validation that fails loudly on unexpected fields. Design parsers to be forward-compatible (ignore unknown fields, require only essential fields). Pin CLI version in CI.

3. **Error amplification cascade in multi-step pipelines** -- GSD's long pipeline (research -> requirements -> roadmap -> planning -> execution -> verification) means early errors propagate to every downstream step. Validate output at every handoff boundary. Implement checkpoint/rollback at each phase boundary. Prefer single orchestrating session over separate agents per phase.

4. **Non-interactive mode missing GSD's interactive prompts** -- GSD's `AskUserQuestion` blocks automation. Pre-fill all answers by composing comprehensive prompts with `--append-system-prompt`. Build question-answer mappings per GSD phase. Test each phase thoroughly in non-interactive mode.

5. **Subprocess lifecycle leaks (zombies)** -- Claude Code spawns child Node.js processes; killing the parent does not kill grandchildren. Use process groups (`start_new_session=True`), `try/finally` cleanup, process registry, and `atexit`/signal handlers. Validate with stress tests.

6. **`.planning/` race conditions** -- Multiple concurrent operations can corrupt flat-file state. Primary mitigation: be read-only for `.planning/` files. Secondary: enforce single-writer-per-project at the workflow level.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation -- Transport, Types, and State Reading
**Rationale:** Everything depends on reliable subprocess I/O and typed data models. The architecture research identifies transport and state as independent layers that can be built in parallel. Four of six critical pitfalls (deadlock, output fragility, lifecycle leaks, race conditions) must be addressed here.
**Delivers:** Working subprocess transport that can spawn Claude Code, stream NDJSON output, and return typed Python objects. Working state reader that parses `.planning/` files into Pydantic models. Error hierarchy. Event emitter skeleton.
**Addresses features:** Subprocess lifecycle management, error handling with typed exceptions, GSD artifact reading, project state querying.
**Avoids pitfalls:** Subprocess deadlock (async I/O from day one), output fragility (Pydantic parsing layer), lifecycle leaks (process group cleanup), race conditions (read-only design decision).
**Stack focus:** claude-agent-sdk (or raw asyncio subprocess behind adapter), Pydantic, orjson, anyio.

### Phase 2: Core Commands -- new-project, plan-phase, execute-phase
**Rationale:** With transport and state layers working, build the GSD-semantic workflow orchestrators. This is where the differentiator (GSD workflow intelligence) takes shape. Pre-filled answer injection is the hardest unsolved problem.
**Delivers:** Working CLI commands that can create a new GSD project, plan a phase, and execute a phase -- all non-interactively with structured JSON output.
**Addresses features:** Non-interactive CLI execution, structured JSON output, CLI binary entry point, pre-filled answer injection, GSD workflow semantics.
**Avoids pitfalls:** Error amplification (validate at every handoff), missing interactive prompts (question-answer mappings per phase).
**Stack focus:** Typer (CLI), Pydantic (output schemas), workflows module.

### Phase 3: Reliability and Session Management
**Rationale:** Once core commands work end-to-end, harden them for real-world use. Retry logic and session management are the features agents hit immediately after initial success.
**Delivers:** Retry with exponential backoff, session continuity across multi-step workflows, cost/token tracking.
**Addresses features:** Retry logic, session management, cost/token tracking.
**Avoids pitfalls:** Rate limit handling (backoff + queueing), error amplification (checkpoint/rollback at phase boundaries).
**Stack focus:** anyio (structured concurrency for retry), pydantic-settings (config for retry policies).

### Phase 4: Library API and Event Hooks
**Rationale:** Python agents (OpenClaw) need richer integration than shelling out. Event hooks enable reactive agent behavior. Both require the core commands to be stable first.
**Delivers:** Importable async Python API (`from openclawpack import new_project`), event hook system for lifecycle callbacks.
**Addresses features:** Python library API, event hooks/callbacks, streaming progress.
**Stack focus:** anyio (async generators), pluggy (extensibility hooks).

### Phase 5: Multi-Project and Production Hardening
**Rationale:** Defer multi-project until single-project is solid. This phase adds the project registry, concurrent execution with semaphore limiting, and idempotent command design.
**Delivers:** Multi-project management, concurrent phase execution across projects, idempotent operations.
**Addresses features:** Multi-project management, idempotent command design.
**Avoids pitfalls:** Race conditions (per-project isolation), rate limiting (semaphore + queue).
**Stack focus:** anyio task groups (concurrent projects), structlog (per-project logging context).

### Phase Ordering Rationale

- **Phase 1 before everything:** Four of six critical pitfalls live here. Transport and state are the foundation every other component builds on. Architecture research confirms these layers are independent and can be developed in parallel within the phase.
- **Phase 2 is the value phase:** This is where OpenClawPack becomes useful. The GSD workflow intelligence and pre-filled answer injection are the differentiators. Ship MVP after Phase 2.
- **Phase 3 before Phase 4:** Reliability (retry, sessions) matters more than API richness. An unreliable library API is worse than no library API.
- **Phase 5 last:** Multi-project is a v2 feature. Getting single-project right is the priority. Multi-project introduces concurrency complexity that amplifies every unresolved bug.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Transport):** The Claude Agent SDK is alpha (v0.1.x) and has documented issues (Windows hangs, lock contention, OOM in concurrent runs). Needs hands-on spike to validate SDK vs. raw subprocess decision before committing.
- **Phase 2 (Pre-filled answer injection):** GSD's interactive questioning model is not documented for non-interactive use. Needs empirical testing of each GSD phase in `-p` mode to map all question points and build answer templates.
- **Phase 5 (Multi-project concurrency):** Rate limiting behavior with concurrent Claude sessions is not well-documented. Needs load testing to determine practical concurrency limits.

Phases with standard patterns (skip research-phase):
- **Phase 3 (Retry/Sessions):** Well-documented patterns for exponential backoff, session management. Claude Code's `--continue`/`--resume` flags are documented in official docs.
- **Phase 4 (Library API/Hooks):** Dual CLI/library interface and pub/sub event systems are standard Python patterns. Typer + async API wrapping is straightforward.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI with current versions. Claude Agent SDK is the only risk (alpha status), but it is an official Anthropic package. |
| Features | MEDIUM-HIGH | Feature landscape is well-mapped from competitor analysis and GSD requirements. Pre-filled answer injection complexity is the least certain -- GSD's interactive model needs empirical testing. |
| Architecture | HIGH | Layered architecture with transport abstraction is a well-established pattern. Claude Agent SDK and multiple competitor projects validate the approach. Build order is clear from dependency analysis. |
| Pitfalls | HIGH | All critical pitfalls verified against official docs, SDK issue trackers, and peer-reviewed multi-agent research. Subprocess deadlock and output fragility are well-documented failure modes. |

**Overall confidence:** HIGH

### Gaps to Address

- **Claude Agent SDK stability:** v0.1.x alpha status means the API could change. Plan for an adapter interface that isolates SDK calls. Run integration tests against SDK on every release.
- **GSD non-interactive question mapping:** No documentation exists for running GSD phases without human interaction. Must be discovered empirically by testing each GSD skill in `-p` mode and cataloging all `AskUserQuestion` prompts.
- **Windows support:** Multiple pitfalls and SDK issues reference Windows-specific problems (process groups, pipe buffering, encoding, SDK initialization hangs). If Windows is a target, add cross-platform CI early.
- **Claude Code CLI version compatibility:** No formal versioning contract for output format. Need a compatibility matrix and version-pinning strategy.
- **Rate limit thresholds:** Practical limits for concurrent Claude Code subprocesses hitting the Anthropic API are not documented. Must be discovered through load testing.

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK Python (PyPI)](https://pypi.org/project/claude-agent-sdk/) -- v0.1.39, API surface, typed messages, hooks
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- Full API documentation
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) -- CLI flags, output formats, session management
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- All CLI flags and modes
- [GSD Framework (GitHub)](https://github.com/glittercowboy/get-shit-done) -- Skills, state management, `.planning/` structure
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) -- Deadlock warnings, async subprocess patterns

### Secondary (MEDIUM confidence)
- [Claude Agent SDK GitHub Issues](https://github.com/anthropics/claude-agent-sdk-python/issues/) -- Real-world failure modes (lock contention, OOM, Windows hangs)
- [claude-flow (ruvnet)](https://github.com/ruvnet/claude-flow) -- Multi-agent orchestration patterns
- [claude-mpm (bobmatnyc)](https://github.com/bobmatnyc/claude-mpm) -- Subprocess orchestration with event hooks
- [CLI Agent Orchestrator (AWS)](https://github.com/awslabs/cli-agent-orchestrator) -- Multi-agent CLI framework
- [Multi-Agent Error Amplification Research](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/) -- 17x error amplification in unstructured topologies
- [AI Agent Design Patterns (Azure)](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- Checkpoint/recovery patterns
- PyPI package pages for all stack components (Typer, Pydantic, Rich, orjson, structlog, pluggy, anyio, uv, ruff, mypy, pytest)

### Tertiary (LOW confidence)
- [Error Recovery in AI Agent Development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development) -- Retry patterns (general, not Claude-specific)
- [Cascading Failures in Agentic AI (OWASP)](https://adversa.ai/blog/cascading-failures-in-agentic-ai-complete-owasp-asi08-security-guide-2026/) -- Security-focused cascade analysis

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
