# Stack Research

**Domain:** Python CLI middleware for AI agent orchestration (Claude Code / GSD)
**Researched:** 2026-02-21
**Confidence:** HIGH

## Critical Finding: Claude Agent SDK

The single most important discovery is the **Claude Agent SDK for Python** (`claude-agent-sdk` v0.1.39, released 2026-02-19). This official Anthropic package provides native Python bindings for driving Claude Code programmatically -- eliminating the need to build custom subprocess management, output parsing, or hook systems from scratch. It bundles the Claude Code CLI, provides async iterators for streaming messages, typed message/content-block models, hook callbacks, custom tool registration via MCP, permission control, and session management. **This SDK should be the foundation of OpenClawPack, not raw subprocess calls.**

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.10+ | Runtime | Matches OpenClaw ecosystem; minimum version required by claude-agent-sdk, Typer, Pydantic, and all other deps | HIGH |
| claude-agent-sdk | 0.1.39 | Claude Code integration | Official Anthropic Python SDK. Provides `query()` for one-shot tasks and `ClaudeSDKClient` for multi-turn conversations. Handles subprocess lifecycle, streaming, hooks, tool permissions, structured output schemas, session continuation, and error types. Eliminates ~60% of what we would have built manually. | HIGH |
| Typer | 0.24.0 | CLI framework | Built on Click 8.3.1; uses Python type hints for zero-boilerplate command definitions. Rich error output built-in. Shell completion. Supports both simple commands and complex nested subcommands. The "FastAPI of CLIs" -- modern, actively maintained by Sebastian Ramirez. | HIGH |
| Pydantic | 2.12.5 | Data models & validation | Industry-standard for Python data validation. Used for GSD artifact models (.planning/ files), command input/output schemas, configuration. V2 is 5-50x faster than V1. Type-safe, IDE-friendly, JSON Schema generation built-in. | HIGH |
| Rich | 14.3.3 | Terminal output | Already a dependency of Typer. Tables, progress bars, syntax highlighting, markdown rendering, tree views. Use for human-readable CLI output alongside JSON output for machines. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| pydantic-settings | 2.13.1 | Configuration management | Loading config from env vars, .env files, and .planning/config.json. Type-safe settings with validation and layered overrides. | HIGH |
| orjson | 3.11.7 | Fast JSON serialization | Parsing Claude Code JSON output (10x faster serialize, 2x faster deserialize vs stdlib json). Native datetime/dataclass/UUID support. Use for all JSON I/O in the hot path. | HIGH |
| structlog | 25.5.0 | Structured logging | All internal logging. Key-value structured logs that render as colored console output in dev and JSON in production. Context binding for per-project/per-session log enrichment. | MEDIUM |
| pluggy | 1.6.0 | Plugin/hook system | Extensibility layer for OpenClawPack. Battle-tested (powers pytest's 1400+ plugins). Defines hook specifications that third-party code can implement. Use for user-defined pre/post phase hooks, custom extractors, output formatters. | MEDIUM |
| anyio | 4.12.1 | Async abstraction | Structured concurrency for managing multiple concurrent Claude sessions (multi-project). Task groups with proper cancellation semantics. Less than 1ms overhead vs raw asyncio. Already widely adopted (used by Prefect, httpx, Starlette). | MEDIUM |

### Development Tools

| Tool | Version | Purpose | Notes | Confidence |
|------|---------|---------|-------|------------|
| uv | 0.10.4 | Package manager & project manager | 10-100x faster than pip. Replaces pip, pip-tools, virtualenv, pyenv. Universal lockfile. Use `uv init`, `uv add`, `uv run`. Rust-based, from Astral (same team as Ruff). | HIGH |
| ruff | 0.15.2 | Linter & formatter | Replaces Black + flake8 + isort + pyupgrade + autoflake in one tool. 10-100x faster. 800+ built-in rules. 2026 style guide support. Use for all linting and formatting. | HIGH |
| mypy | 1.19.1 | Static type checking | Essential for a typed Python codebase. Catches type errors before runtime. Use strict mode. Complements Pydantic's runtime validation with compile-time checking. | HIGH |
| pytest | 9.0.2 | Testing framework | Industry standard. Rich plugin ecosystem. Use with pytest-asyncio for async tests. | HIGH |
| pytest-asyncio | 1.3.0 | Async test support | Required for testing claude-agent-sdk integration (all SDK calls are async). v1.0+ removed deprecated event_loop fixture -- use modern patterns. | HIGH |
| pytest-mock | 3.15.1 | Mocking support | Thin wrapper around unittest.mock. Essential for mocking Claude SDK calls in unit tests. | HIGH |
| hatchling | 1.28.0 | Build backend | Modern PEP 517/621 build backend. Use in pyproject.toml. Recommended by Python Packaging Authority for new projects. Faster and more configurable than setuptools. | HIGH |

---

## Installation

```bash
# Initialize project with uv
uv init openclawpack
cd openclawpack

# Core dependencies
uv add claude-agent-sdk typer pydantic pydantic-settings rich orjson structlog pluggy anyio

# Dev dependencies
uv add --dev ruff mypy pytest pytest-asyncio pytest-mock

# Verify installation
uv run python -c "import claude_agent_sdk; print('SDK ready')"
uv run openclawpack --help
```

### pyproject.toml skeleton

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "openclawpack"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk>=0.1.39",
    "typer>=0.24.0",
    "pydantic>=2.12.0",
    "pydantic-settings>=2.13.0",
    "rich>=14.0.0",
    "orjson>=3.11.0",
    "structlog>=25.0.0",
    "pluggy>=1.6.0",
    "anyio>=4.12.0",
]

[project.scripts]
openclawpack = "openclawpack.cli:app"

[project.optional-dependencies]
dev = [
    "ruff>=0.15.0",
    "mypy>=1.19.0",
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "pytest-mock>=3.15.0",
]

[tool.ruff]
target-version = "py310"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "SIM", "TCH"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **claude-agent-sdk** | Raw `subprocess.Popen` / `asyncio.create_subprocess_exec` | The SDK already manages the Claude CLI subprocess lifecycle, parses JSON output into typed Python objects, handles streaming, hooks, permissions, session continuation, and error recovery. Building this from scratch would duplicate 2000+ lines of battle-tested code. |
| **claude-agent-sdk** | Claude API direct (anthropic SDK) | We need GSD skills which run inside Claude Code's agent loop with tools (Read, Write, Bash, etc.). The raw API gives you a chat completion, not an agentic executor. The Agent SDK gives us the full Claude Code environment. |
| **Typer** | Click (8.3.1) | Click is mature and Typer is built on it, but Typer eliminates decorator boilerplate via type hints. Since we're already using type hints throughout (Pydantic, mypy), Typer fits the codebase idiomatically. Click is still used internally. |
| **Typer** | argparse (stdlib) | argparse requires verbose setup for subcommands, has no auto-completion, no rich output, and produces ugly help text. For a tool that agents and humans both use, UX matters. |
| **Pydantic v2** | dataclasses + manual validation | Pydantic provides JSON Schema generation (needed for `--json-schema` output format), serialization/deserialization, settings management via pydantic-settings, and integrates with Claude Agent SDK's structured output schemas. dataclasses would require reimplementing all of this. |
| **orjson** | stdlib json | stdlib json is 2-10x slower. When parsing streaming JSON output from Claude (potentially hundreds of messages per session), orjson's performance matters. Also handles datetime/UUID natively which Pydantic models use. |
| **structlog** | stdlib logging | stdlib logging requires verbose configuration for structured output. structlog gives us key-value logging, colored dev output, JSON production output, and context binding (per-project, per-session) with minimal setup. |
| **pluggy** | blinker (1.9) | Blinker is a signal/event dispatcher (observer pattern). Pluggy is a hook/plugin system. We need both event callbacks (handled by claude-agent-sdk hooks) AND user extensibility (custom GSD extractors, formatters). Pluggy is the right abstraction for the extensibility layer. |
| **anyio** | raw asyncio | anyio provides structured concurrency (task groups with proper cancellation), which is critical when managing multiple concurrent Claude sessions. Raw asyncio's `create_task` doesn't propagate errors or cancel siblings. anyio adds <1ms overhead. |
| **uv** | pip + virtualenv + pyenv | uv replaces all three in one tool, is 10-100x faster, has universal lockfile, and is the clear 2025-2026 community standard. Same team as Ruff (Astral). |
| **ruff** | Black + flake8 + isort | ruff replaces all three, runs 10-100x faster, and is a single dependency. No reason to use separate tools in 2026. |
| **hatchling** | setuptools | hatchling is faster, more modern, designed for pyproject.toml from the start. setuptools carries legacy baggage (setup.py, setup.cfg). For a new project, hatchling is the right choice. |
| **mypy** | pyright / pytype | mypy has the largest ecosystem, most IDE integrations, and is the most widely used. pyright is faster but less configurable. For strict type checking of a Pydantic-heavy codebase, mypy is battle-tested. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Raw subprocess.Popen for Claude** | The claude-agent-sdk handles subprocess management, output parsing, error handling, streaming, and session management. Rolling your own loses typed messages, hook callbacks, permission control, and session continuation. | claude-agent-sdk `query()` and `ClaudeSDKClient` |
| **anthropic SDK (direct API)** | Gives you raw chat completions, not agentic tool-using Claude Code. You'd lose all GSD skills, file system tools, and the agent loop. | claude-agent-sdk which wraps Claude Code's full agent environment |
| **Poetry** | Slower than uv, less actively developed, uses its own lockfile format. uv has won the Python packaging race in 2025-2026. | uv |
| **Black + flake8 + isort** | Three separate tools, each slower than ruff alone. More config files, more CI steps, more dependencies. | ruff (one tool, 800+ rules, formatting included) |
| **asyncio.gather()** | Does not propagate errors properly or cancel sibling tasks. Dangerous for concurrent Claude sessions where one failure should cancel others. | anyio task groups with structured concurrency |
| **logging (stdlib) without structlog** | Produces unstructured text logs that are hard to search/filter. No context binding, no automatic JSON output for production. | structlog wrapping stdlib logging |
| **sqlite/redis for state** | PROJECT.md specifies: "All project state lives in `.planning/`". Introducing a database adds a dependency and diverges from GSD's file-based state model. | Pydantic models reading/writing `.planning/` JSON/YAML/Markdown files |
| **TOML/YAML parsing libraries** | GSD's config.json is JSON. Claude SDK output is JSON. `.planning/` state files that aren't markdown are JSON. Don't introduce TOML/YAML unless GSD forces it. | orjson for all JSON, Pydantic for validation |
| **celery/dramatiq** | Overkill for subprocess orchestration. We're managing Claude CLI processes, not distributed task queues. | anyio task groups + claude-agent-sdk session management |
| **typer-cli** | Deprecated package. Do NOT confuse with `typer`. `typer-cli` was a separate tool for generating Click groups from Typer apps -- it has been folded into Typer itself. | typer (the main package) |

---

## Stack Patterns by Variant

**If building a pure library (no CLI):**
- Drop Typer/Rich from core deps, keep as optional
- Expose `openclawpack.api` module with async functions
- Because: Some consumers (OpenClaw) will import directly, never call CLI

**If building CLI-only (no library consumers):**
- Typer commands can call claude-agent-sdk directly
- Because: Simpler architecture, fewer abstractions

**If building both (recommended by PROJECT.md):**
- Library core in `openclawpack/core/` with async API
- CLI layer in `openclawpack/cli/` that wraps core with Typer
- Because: CLI wraps library; library is the real product. Agents can shell out OR import.

**If multi-project concurrency is critical:**
- Use anyio task groups for parallel Claude sessions
- Each project gets its own `ClaudeSDKClient` instance with isolated cwd
- Because: Structured concurrency prevents leaked resources and ensures clean cancellation

**If hook extensibility is needed early:**
- Define pluggy hook specifications for key lifecycle events
- Claude-agent-sdk hooks handle Claude-level events; pluggy hooks handle OpenClawPack-level events (phase start/end, artifact created, etc.)
- Because: Two hook layers -- one for Claude control, one for user extensibility

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| claude-agent-sdk 0.1.39 | Python 3.10-3.13 | Alpha status; API may change. Pin to ~=0.1.39, monitor releases. |
| Typer 0.24.0 | Click >=8.0, Rich >=10.11, Python 3.10+ | Click and Rich are auto-installed as Typer dependencies |
| Pydantic 2.12.5 | Python 3.9+, pydantic-settings 2.13.1 | pydantic-settings is a separate package since Pydantic v2 |
| orjson 3.11.7 | Python 3.10-3.15 | C extension; wheels available for all major platforms |
| anyio 4.12.1 | Python 3.9+, works on asyncio backend | No Trio needed; asyncio backend is default |
| pluggy 1.6.0 | Python 3.9+ | Stable API since 1.0; used by pytest |
| structlog 25.5.0 | Python 3.9+ | Wraps stdlib logging; compatible with any logging config |
| ruff 0.15.2 | Python 3.7+ target, runs on 3.10+ | Standalone binary; no Python runtime dependency |
| mypy 1.19.1 | Python 3.9+ | Use with Pydantic mypy plugin for best model checking |

**Known compatibility concern:** claude-agent-sdk is at v0.1.x (Alpha). Expect breaking changes. Mitigate by:
1. Pinning to specific version in lockfile
2. Wrapping SDK calls behind an internal adapter interface
3. Writing integration tests that catch API changes early

---

## Architecture Implication

The existence of `claude-agent-sdk` fundamentally changes the architecture from what PROJECT.md initially assumed:

**Original assumption:** OpenClawPack spawns `claude` CLI subprocesses, pipes prompts, parses raw stdout.

**Updated reality:** OpenClawPack uses `claude-agent-sdk` which handles subprocess management internally. Our code works with typed Python objects (`Message`, `AssistantMessage`, `ToolUseBlock`, `ResultMessage`), not raw text streams.

**What this means for the roadmap:**
1. **Subprocess layer is solved** -- no need to build it
2. **Output parsing is solved** -- SDK provides typed messages and content blocks
3. **Hook system is partially solved** -- SDK provides `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop` hooks
4. **Session management is solved** -- `ClaudeSDKClient` maintains conversation context
5. **Structured output is solved** -- SDK supports `--json-schema` via `output_format` option

**What OpenClawPack still needs to build:**
1. GSD skill orchestration (translating "new-project" into the right prompts/options for SDK)
2. GSD artifact models (.planning/ file parsing and generation)
3. Multi-project state management
4. CLI interface (Typer commands wrapping SDK calls)
5. Higher-level hook system (pluggy) for user extensibility beyond Claude-level hooks

---

## Sources

- [PyPI: claude-agent-sdk 0.1.39](https://pypi.org/project/claude-agent-sdk/) -- Version, release date, Python compatibility (verified 2026-02-21)
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- Full API documentation, types, examples (verified 2026-02-21)
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) -- CLI flags, --output-format, --json-schema (verified 2026-02-21)
- [PyPI: typer 0.24.0](https://pypi.org/project/typer/) -- Version, dependencies, Python support (verified 2026-02-21)
- [PyPI: pydantic 2.12.5](https://pypi.org/project/pydantic/) -- Version, release date (verified 2026-02-21)
- [PyPI: pydantic-settings 2.13.1](https://pypi.org/project/pydantic-settings/) -- Version, release date (verified 2026-02-21)
- [PyPI: rich 14.3.3](https://pypi.org/project/rich/) -- Version, release date (verified 2026-02-21)
- [PyPI: orjson 3.11.7](https://pypi.org/project/orjson/) -- Version, performance benchmarks (verified 2026-02-21)
- [PyPI: structlog 25.5.0](https://pypi.org/project/structlog/) -- Version, release date (verified 2026-02-21)
- [PyPI: pluggy 1.6.0](https://pypi.org/project/pluggy/) -- Version, release date (verified 2026-02-21)
- [PyPI: anyio 4.12.1](https://pypi.org/project/anyio/) -- Version, features, subprocess support (verified 2026-02-21)
- [PyPI: uv 0.10.4](https://pypi.org/project/uv/) -- Version, release date (verified 2026-02-21)
- [PyPI: ruff 0.15.2](https://pypi.org/project/ruff/) -- Version, release date (verified 2026-02-21)
- [PyPI: mypy 1.19.1](https://pypi.org/project/mypy/) -- Version, release date (verified 2026-02-21)
- [PyPI: pytest 9.0.2](https://pypi.org/project/pytest/) -- Version, release date (verified 2026-02-21)
- [PyPI: pytest-asyncio 1.3.0](https://pypi.org/project/pytest-asyncio/) -- Version, breaking changes in v1.0 (verified 2026-02-21)
- [PyPI: pytest-mock 3.15.1](https://pypi.org/project/pytest-mock/) -- Version, release date (verified 2026-02-21)
- [PyPI: hatchling 1.28.0](https://pypi.org/project/hatchling/) -- Version, release date (verified 2026-02-21)
- [AnyIO Documentation: Why AnyIO](https://anyio.readthedocs.io/en/stable/why.html) -- Structured concurrency rationale
- [Structlog: Logging Best Practices](https://www.structlog.org/en/stable/logging-best-practices.html) -- Dev vs production logging patterns
- [Python Packaging Best Practices 2026](https://dasroot.net/posts/2026/01/python-packaging-best-practices-setuptools-poetry-hatch/) -- hatchling recommendation
- [Astral: Ruff v0.15.0](https://astral.sh/blog/ruff-v0.15.0) -- 2026 style guide, latest features

---
*Stack research for: OpenClawPack -- Python CLI middleware for AI agent orchestration*
*Researched: 2026-02-21*
