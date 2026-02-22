# Phase 1: Foundation - Research

**Researched:** 2026-02-21
**Domain:** Python packaging, subprocess transport, state parsing, structured output
**Confidence:** HIGH

## Summary

Phase 1 builds four foundational subsystems: (1) an installable Python package with CLI entry point, (2) a transport layer for spawning and communicating with Claude Code subprocesses, (3) a state parser that reads `.planning/` files into typed Pydantic models, and (4) a standard JSON output envelope wrapping all operations.

The most significant finding is that the **Claude Agent SDK** (`claude-agent-sdk` v0.1.39, Feb 2026) has matured well beyond the alpha status noted in the roadmap. It bundles the Claude Code CLI, manages subprocess lifecycle automatically, provides typed Python message objects (including `ResultMessage` with `session_id`, `duration_ms`, `total_cost_usd`, `usage`), and ships with a typed exception hierarchy (`CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, `CLIConnectionError`) that maps almost exactly to TRNS-04's requirements. This eliminates the need to hand-roll subprocess management or build a custom transport layer from scratch.

The package skeleton uses `hatchling` as the build backend with `pyproject.toml`, Typer v0.24.x for the CLI framework, and Pydantic v2.12.x for all data models. The state parser will use regex-based section extraction from markdown files (no heavy markdown AST library needed -- the `.planning/` files have predictable, stable formats). The standard output schema maps cleanly onto the SDK's `ResultMessage` fields plus a thin wrapper.

**Primary recommendation:** Use `claude-agent-sdk` as the transport layer (wrapping it behind an adapter interface for isolation), Pydantic v2 for all models, Typer for CLI, and hatchling for packaging. Do NOT hand-roll subprocess management.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRNS-01 | CLI can spawn Claude Code subprocess with piped stdin/stdout and capture structured output | Claude Agent SDK `query()` and `ClaudeSDKClient` handle subprocess spawning, piping, and structured message iteration natively. SDK bundles the CLI binary. |
| TRNS-02 | Subprocess has configurable timeout with graceful termination (SIGTERM then SIGKILL) | SDK manages subprocess lifecycle internally. External timeout via `asyncio.wait_for()` or `anyio.fail_after()`. Graceful termination pattern: SIGTERM -> wait -> SIGKILL. The `ClaudeSDKClient.interrupt()` method provides cooperative cancellation. |
| TRNS-03 | Concurrent stdout/stderr reading prevents pipe buffer deadlocks | SDK handles stdout/stderr concurrently internally. `ClaudeAgentOptions.stderr` callback captures stderr. No manual pipe management needed. |
| TRNS-04 | Typed exception hierarchy: CLINotFound, ProcessError, TimeoutError, JSONDecodeError, GSD-specific | SDK provides `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, `CLIConnectionError`. Add `TimeoutError` (from asyncio) and custom GSD-specific exceptions as thin wrappers. |
| STATE-01 | Parse config.json, STATE.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md without subprocess | Pure Python: `json.loads()` for config.json, regex-based section extraction for markdown files, Pydantic v2 models for validation. No subprocess or external tool needed. |
| STATE-02 | State queries return structured data: current phase, progress, blocker list, requirement completion | Pydantic models extract phase number, completion counts, and blockers from STATE.md and ROADMAP.md. Computed fields derive progress percentage and status. |
| OUT-01 | Every command returns JSON: {success, result, errors, session_id, usage, duration_ms} | Standard `CommandResult` Pydantic model wrapping all outputs. Maps from SDK's `ResultMessage` fields (`session_id`, `duration_ms`, `total_cost_usd`, `usage`, `is_error`). |
| OUT-02 | JSON output validated against Pydantic models with consistent schema | All output through a single `CommandResult` model with `.model_dump_json()`. Schema generated via `CommandResult.model_json_schema()`. |
| PKG-01 | `pip install openclawpack` provides `openclawpack` CLI binary | `pyproject.toml` with `[project.scripts] openclawpack = "openclawpack.cli:app"` using Typer. |
| PKG-02 | Requires Python 3.10+ and Claude Code CLI installed | `requires-python = ">=3.10"` in pyproject.toml. Claude Code CLI bundled via `claude-agent-sdk` dependency. Runtime check with clear error message when attempting transport operations without valid auth. |
| PKG-03 | Zero required runtime dependencies beyond stdlib + Pydantic + Typer + anyio | Dependencies: `pydantic>=2.12`, `typer>=0.24`, `anyio>=4.8`, `claude-agent-sdk>=0.1.39`. Note: claude-agent-sdk itself uses anyio internally. |
| PKG-04 | `openclawpack --version` and `--help` work without Claude Code installed | CLI (Typer) loads without importing transport layer. Transport is lazy-imported only when subprocess operations are invoked. State parsing also works independently. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| claude-agent-sdk | >=0.1.39 | Claude Code subprocess transport | Official Anthropic SDK. Bundles CLI, manages subprocess lifecycle, typed messages and errors. Eliminates hand-rolled subprocess management. |
| pydantic | >=2.12 | Data validation and JSON schema | Industry standard for Python data models. V2 uses Rust core for performance. Native JSON schema generation. |
| typer | >=0.24 | CLI framework | Built on Click. Type-hint-driven CLI. Auto-generates `--help`. Supports subcommands, options, and arguments declaratively. |
| anyio | >=4.8 | Async runtime compatibility | Required by claude-agent-sdk. Works on asyncio and Trio. Structured concurrency, subprocess support. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hatchling | >=1.25 | Build backend | pyproject.toml build system. PEP 621 compliant. Reproducible builds. Better defaults than setuptools. |
| pytest | >=8.0 | Testing | All test suites. |
| pytest-anyio | >=0.0.0 | Async test support | Testing async transport and SDK operations. |
| ruff | >=0.9 | Linting and formatting | Code quality. Replaces flake8 + black + isort. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| claude-agent-sdk | Raw `asyncio.create_subprocess_exec` calling `claude` CLI | Full control but must hand-roll pipe management, JSON parsing, error handling, and keep up with CLI changes. SDK abstracts all of this. |
| claude-agent-sdk | claude-agent-sdk `query()` only (no `ClaudeSDKClient`) | Simpler but no session continuity, no interrupts, no hooks. Phase 3+ will need `ClaudeSDKClient`. |
| Typer | Click directly | Typer wraps Click with type hints. Less boilerplate. No reason to use raw Click. |
| Typer | argparse | Standard library but verbose, no auto-completion, no rich help. |
| hatchling | setuptools | Setuptools works but weaker defaults, no reproducible sdists, verbose config. |
| hatchling | uv_build | Newer but less mature ecosystem. hatchling is proven. |
| regex markdown parsing | markdown-it-py or mistune | Full AST parsing overkill for predictable `.planning/` file formats. Adds dependency for no benefit. |

**Installation (runtime):**
```bash
pip install pydantic typer anyio claude-agent-sdk
```

**Installation (dev):**
```bash
pip install hatchling pytest pytest-anyio ruff
```

## Architecture Patterns

### Recommended Project Structure

```
openclawpack/
├── pyproject.toml
├── src/
│   └── openclawpack/
│       ├── __init__.py           # Package version, public API
│       ├── cli.py                # Typer app, commands, entry point
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── client.py         # Transport adapter wrapping claude-agent-sdk
│       │   ├── errors.py         # Exception hierarchy (extends SDK errors)
│       │   └── types.py          # Transport-specific types
│       ├── state/
│       │   ├── __init__.py
│       │   ├── parser.py         # Markdown/JSON file parsers
│       │   ├── models.py         # Pydantic models for .planning/ files
│       │   └── reader.py         # High-level state reader (orchestrates parsers)
│       ├── output/
│       │   ├── __init__.py
│       │   ├── schema.py         # CommandResult and standard output envelope
│       │   └── formatter.py      # JSON serialization helpers
│       └── _version.py           # Single source of version truth
├── tests/
│   ├── conftest.py
│   ├── test_transport/
│   ├── test_state/
│   └── test_output/
└── .planning/                    # GSD project files (this project)
```

### Pattern 1: Transport Adapter (Facade over SDK)

**What:** Wrap `claude-agent-sdk` behind an adapter interface so the rest of the codebase never imports the SDK directly.

**When to use:** Always. The SDK is v0.1.x and API may change. The adapter isolates breaking changes to one file.

**Example:**
```python
# src/openclawpack/transport/client.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

from claude_agent_sdk import (
    query as sdk_query,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from claude_agent_sdk import (
    CLINotFoundError,
    ProcessError as SDKProcessError,
    CLIJSONDecodeError,
    CLIConnectionError,
)

from openclawpack.transport.errors import (
    TransportError,
    CLINotFound,
    ProcessError,
    TransportTimeout,
    JSONDecodeError,
)
from openclawpack.output.schema import CommandResult


@dataclass
class TransportConfig:
    """Configuration for Claude Code transport."""
    cwd: str | None = None
    timeout_seconds: float = 300.0
    allowed_tools: list[str] | None = None
    system_prompt: str | None = None
    cli_path: str | None = None
    permission_mode: str = "bypassPermissions"


class ClaudeTransport:
    """Adapter wrapping claude-agent-sdk for openclawpack."""

    def __init__(self, config: TransportConfig | None = None):
        self.config = config or TransportConfig()

    async def run(self, prompt: str) -> CommandResult:
        """Execute a prompt and return structured result."""
        options = ClaudeAgentOptions(
            cwd=self.config.cwd,
            allowed_tools=self.config.allowed_tools or [],
            permission_mode=self.config.permission_mode,
            cli_path=self.config.cli_path,
        )
        try:
            result_message: ResultMessage | None = None
            async with asyncio.timeout(self.config.timeout_seconds):
                async for message in sdk_query(prompt=prompt, options=options):
                    if isinstance(message, ResultMessage):
                        result_message = message

            if result_message is None:
                raise ProcessError("No result message received from Claude")

            return CommandResult(
                success=not result_message.is_error,
                result=result_message.result,
                errors=[result_message.result] if result_message.is_error else [],
                session_id=result_message.session_id,
                usage=result_message.usage,
                duration_ms=result_message.duration_ms,
            )
        except CLINotFoundError as e:
            raise CLINotFound(str(e)) from e
        except SDKProcessError as e:
            raise ProcessError(str(e), exit_code=e.exit_code) from e
        except CLIJSONDecodeError as e:
            raise JSONDecodeError(str(e)) from e
        except TimeoutError:
            raise TransportTimeout(
                f"Claude Code subprocess timed out after {self.config.timeout_seconds}s"
            )
```

### Pattern 2: Lazy Import for CLI Independence

**What:** The CLI module imports transport only when a command that needs it is invoked, not at module load time.

**When to use:** Required for PKG-04 -- `--version` and `--help` must work without Claude Code.

**Example:**
```python
# src/openclawpack/cli.py
import typer

app = typer.Typer(name="openclawpack", help="AI agent control over GSD framework")


def version_callback(value: bool):
    if value:
        from openclawpack._version import __version__
        typer.echo(f"openclawpack {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """OpenClawPack: Programmatic control over GSD via Claude Code."""
    pass


@app.command()
def status(
    project_dir: str = typer.Option(".", "--project-dir", help="Project directory"),
):
    """Show project state as structured JSON."""
    # State parsing -- no transport needed, no Claude Code dependency
    from openclawpack.state.reader import read_project_state
    from openclawpack.output.schema import CommandResult
    import time, json

    start = time.monotonic()
    state = read_project_state(project_dir)
    duration = int((time.monotonic() - start) * 1000)

    result = CommandResult(
        success=True,
        result=state.model_dump(),
        errors=[],
        session_id=None,
        usage=None,
        duration_ms=duration,
    )
    typer.echo(result.model_dump_json(indent=2))
```

### Pattern 3: Pydantic Models for .planning/ Files

**What:** Each `.planning/` file type has a corresponding Pydantic model. Markdown files are parsed with regex section extraction, not a full markdown parser.

**When to use:** STATE-01, STATE-02.

**Example:**
```python
# src/openclawpack/state/models.py
from __future__ import annotations
import re
from pydantic import BaseModel, Field, computed_field


class PhaseInfo(BaseModel):
    """A phase from ROADMAP.md."""
    number: int
    name: str
    goal: str | None = None
    requirements: list[str] = Field(default_factory=list)
    plans_complete: int = 0
    plans_total: int = 0
    status: str = "Not started"


class RequirementInfo(BaseModel):
    """A requirement from REQUIREMENTS.md."""
    id: str
    description: str
    phase: int | None = None
    completed: bool = False


class ProjectState(BaseModel):
    """Parsed state from STATE.md."""
    current_phase: int
    current_phase_name: str
    plans_complete: int = 0
    plans_total: int = 0
    progress_percent: float = 0.0
    last_activity: str | None = None
    blockers: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    """Parsed config.json from .planning/."""
    mode: str = "yolo"
    depth: str = "standard"
    parallelization: bool = True
    commit_docs: bool = True
    model_profile: str = "quality"


class ProjectInfo(BaseModel):
    """Parsed PROJECT.md."""
    name: str
    description: str
    core_value: str | None = None
    constraints: list[str] = Field(default_factory=list)


class PlanningDirectory(BaseModel):
    """Complete parsed .planning/ directory."""
    config: ProjectConfig
    state: ProjectState
    project: ProjectInfo
    phases: list[PhaseInfo] = Field(default_factory=list)
    requirements: list[RequirementInfo] = Field(default_factory=list)

    @computed_field
    @property
    def current_phase_info(self) -> PhaseInfo | None:
        for phase in self.phases:
            if phase.number == self.state.current_phase:
                return phase
        return None

    @computed_field
    @property
    def overall_progress(self) -> float:
        if not self.phases:
            return 0.0
        total_plans = sum(p.plans_total for p in self.phases)
        done_plans = sum(p.plans_complete for p in self.phases)
        return (done_plans / total_plans * 100) if total_plans > 0 else 0.0
```

### Pattern 4: Standard Output Envelope

**What:** Every command returns the same JSON structure, regardless of whether it used transport or just local state parsing.

**When to use:** OUT-01, OUT-02.

**Example:**
```python
# src/openclawpack/output/schema.py
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    """Standard output envelope for all openclawpack operations."""
    success: bool
    result: Any = None
    errors: list[str] = Field(default_factory=list)
    session_id: str | None = None
    usage: dict[str, Any] | None = None
    duration_ms: int = 0

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
```

### Anti-Patterns to Avoid

- **Importing transport at module level:** Breaks `--version` and `--help` when Claude Code is not installed. Always lazy-import transport.
- **Parsing markdown with regex for arbitrary documents:** Works here ONLY because `.planning/` files have predictable, stable formats controlled by GSD. Do not generalize this approach.
- **Catching bare `Exception` in transport:** Defeats the purpose of the typed exception hierarchy. Always catch specific SDK exceptions and re-raise as typed transport errors.
- **Returning raw dicts instead of Pydantic models:** Loses type safety, schema validation, and JSON schema generation. Always use models.
- **Storing version in multiple places:** Use a single `_version.py` file or `importlib.metadata` to read from pyproject.toml at runtime.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude Code subprocess management | Custom asyncio subprocess with pipe management | `claude-agent-sdk` `query()` / `ClaudeSDKClient` | SDK handles pipe buffering, JSON parsing, message framing, CLI version compatibility, bundled CLI binary |
| CLI framework | argparse wrappers | Typer | Auto-completion, rich help, type validation, subcommands |
| Data validation | Manual dict checks | Pydantic v2 | JSON schema generation, type coercion, computed fields, serialization |
| Error classification from subprocess | Exit code parsing | SDK's typed exceptions | `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError` already distinguish failure modes |
| Async subprocess timeout | Manual signal handling | `asyncio.timeout()` (Python 3.11+) or `anyio.fail_after()` | Built-in, cancellation-safe, works with structured concurrency |
| JSON output schema | Manual dict construction | Pydantic `model_dump_json()` + `model_json_schema()` | Consistent serialization, schema export, validation |

**Key insight:** The Claude Agent SDK eliminates the entire "build a subprocess transport from scratch" problem that the roadmap originally anticipated. The SDK is no longer alpha -- it's at v0.1.39 with comprehensive typed messages, error handling, session management, and hooks. The transport adapter layer should be a thin facade over the SDK, not a reimplementation.

## Common Pitfalls

### Pitfall 1: Importing Transport at Module Load Time
**What goes wrong:** `openclawpack --version` crashes with `CLINotFoundError` or import error when Claude Code is not installed.
**Why it happens:** Python executes all top-level imports when a module is loaded. If `cli.py` imports from `transport/` at the top, and transport imports `claude-agent-sdk`, the SDK will attempt to locate the Claude CLI binary.
**How to avoid:** Use lazy imports. Transport is imported inside command functions, never at module level in `cli.py`.
**Warning signs:** `--help` or `--version` failing in CI environments or fresh installs.

### Pitfall 2: Blocking the Event Loop with Synchronous Calls
**What goes wrong:** CLI commands using `asyncio.run()` inside Typer callbacks can conflict if the event loop is already running.
**Why it happens:** Typer is synchronous. Running async SDK calls requires bridging sync-to-async.
**How to avoid:** Use `anyio.from_thread.run()` or a dedicated `asyncio.run()` in each command. Do NOT try to share event loops across commands. Alternatively, use `anyio.run()` as the top-level entry point.
**Warning signs:** `RuntimeError: This event loop is already running`.

### Pitfall 3: Not Handling Partial SDK Output
**What goes wrong:** Assuming `query()` always yields a `ResultMessage`. If the process crashes mid-stream, you may get `AssistantMessage`s but never a `ResultMessage`.
**Why it happens:** Subprocess can die, be killed, or lose connection at any point.
**How to avoid:** Always check if `ResultMessage` was received. If the async iterator completes without one, treat it as a `ProcessError`.
**Warning signs:** `None` session_id or missing duration_ms in output.

### Pitfall 4: Brittle Markdown Parsing
**What goes wrong:** State parser breaks when GSD changes `.planning/` file format slightly.
**Why it happens:** Overly strict regex patterns that break on whitespace changes, header level changes, or new sections.
**How to avoid:** Parse sections by header name (e.g., `## Current Position`), not by line number or exact formatting. Use permissive patterns. Add fallback defaults for missing sections. Test against multiple real GSD project states.
**Warning signs:** `ValidationError` from Pydantic when parsing real projects.

### Pitfall 5: Missing `src/` Layout
**What goes wrong:** Tests import the wrong version of the package (local source vs installed).
**Why it happens:** Flat layout allows Python to find the package in the current directory instead of the installed version.
**How to avoid:** Use `src/` layout. The package lives in `src/openclawpack/`, so `import openclawpack` always resolves to the installed version during tests.
**Warning signs:** Tests pass locally but fail in CI, or changes don't appear in test runs.

### Pitfall 6: Hardcoded `.planning/` Paths
**What goes wrong:** State parser only works when cwd is the project root.
**Why it happens:** Using relative paths like `.planning/STATE.md` instead of constructing paths from a configurable base directory.
**How to avoid:** All state functions accept a `project_dir: Path` parameter. Construct all paths relative to it: `project_dir / ".planning" / "STATE.md"`.
**Warning signs:** `FileNotFoundError` when running from a different directory.

## Code Examples

Verified patterns from official sources:

### Claude Agent SDK: Basic Query
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def run_claude(prompt: str, cwd: str) -> ResultMessage:
    options = ClaudeAgentOptions(
        cwd=cwd,
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="bypassPermissions",
    )
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None:
        raise RuntimeError("No ResultMessage received")
    return result

# result.session_id, result.duration_ms, result.total_cost_usd, result.usage, result.is_error
```

### Claude Agent SDK: Error Handling
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/python
from claude_agent_sdk import (
    query,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    CLIConnectionError,
)

try:
    async for message in query(prompt="Hello"):
        pass
except CLINotFoundError:
    # Claude Code CLI not installed or not found
    print("Install Claude Code: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    # Subprocess failed
    print(f"Exit code: {e.exit_code}, stderr: {e.stderr}")
except CLIJSONDecodeError as e:
    # Malformed JSON from subprocess
    print(f"Bad line: {e.line}")
except CLIConnectionError:
    # General connection failure
    print("Could not connect to Claude Code process")
```

### Claude Agent SDK: Session Continuity
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage

async def multi_turn():
    async with ClaudeSDKClient(
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode="acceptEdits",
        )
    ) as client:
        await client.query("Read the auth module")
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                session_id = msg.session_id

        # Follow-up -- Claude remembers context
        await client.query("Now find all callers of that module")
        async for msg in client.receive_response():
            pass
```

### Typer CLI with Version Callback
```python
# Source: https://typer.tiangolo.com/tutorial/options/version/
import typer

app = typer.Typer()

def version_callback(value: bool):
    if value:
        from openclawpack._version import __version__
        typer.echo(f"openclawpack {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """OpenClawPack CLI."""
    pass
```

### Pydantic v2: Model with Computed Fields
```python
# Source: https://docs.pydantic.dev/latest/
from pydantic import BaseModel, Field, computed_field

class ProjectState(BaseModel):
    current_phase: int
    plans_complete: int = 0
    plans_total: int = 0

    @computed_field
    @property
    def progress_percent(self) -> float:
        if self.plans_total == 0:
            return 0.0
        return round(self.plans_complete / self.plans_total * 100, 1)

# Usage:
state = ProjectState(current_phase=1, plans_complete=2, plans_total=3)
print(state.model_dump_json())
# {"current_phase":1,"plans_complete":2,"plans_total":3,"progress_percent":66.7}
```

### pyproject.toml Configuration
```toml
# Source: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "openclawpack"
version = "0.1.0"
description = "AI agent control over the GSD framework via Claude Code"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "pydantic>=2.12",
    "typer>=0.24",
    "anyio>=4.8",
    "claude-agent-sdk>=0.1.39",
]

[project.scripts]
openclawpack = "openclawpack.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-anyio>=0.0.0",
    "ruff>=0.9",
]
```

### Async Timeout with Graceful Termination
```python
# Source: https://docs.python.org/3/library/asyncio-subprocess.html
import asyncio

async def run_with_timeout(prompt: str, timeout: float):
    """Run Claude with timeout, graceful then forceful termination."""
    try:
        async with asyncio.timeout(timeout):
            # SDK manages subprocess internally
            async for message in query(prompt=prompt, options=options):
                process_message(message)
    except TimeoutError:
        # asyncio.timeout cancels the task, SDK cleans up subprocess
        raise TransportTimeout(f"Timed out after {timeout}s")
```

### Markdown Section Parsing
```python
# Pattern for parsing predictable .planning/ markdown files
import re
from pathlib import Path

def extract_section(content: str, header: str, level: int = 2) -> str | None:
    """Extract content under a markdown header."""
    prefix = "#" * level
    # Match the target header and capture until the next header of same or higher level
    pattern = rf"^{prefix}\s+{re.escape(header)}\s*\n(.*?)(?=^{'#'}{'{1,' + str(level) + '}'}\s|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else None

def parse_checkbox_items(section: str) -> list[tuple[bool, str]]:
    """Parse markdown checkbox items: - [ ] or - [x]."""
    pattern = r"^-\s+\[([ xX])\]\s+(.+)$"
    return [
        (m.group(1).lower() == "x", m.group(2).strip())
        for m in re.finditer(pattern, section, re.MULTILINE)
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `claude` CLI subprocess + pipe management | Claude Agent SDK (`claude-agent-sdk`) | May 2025 initial, Sep 2025 renamed, Feb 2026 v0.1.39 | Eliminates hand-rolled subprocess management. Typed messages, error hierarchy, session management included. |
| `setup.py` + setuptools | `pyproject.toml` + hatchling | PEP 621 (2021), hatchling mature by 2024 | Declarative config, reproducible builds, better defaults. |
| Pydantic v1 | Pydantic v2 (v2.12.x) | June 2023 | Rust core, 5-50x faster validation, `model_dump()` replaces `.dict()`, `model_validate()` replaces `.parse_obj()`. |
| `typer-cli` separate package | `typer` v0.12.1+ includes CLI | 2024 | Single package. `typer-cli` is deprecated. |
| `asyncio.wait_for()` for timeout | `asyncio.timeout()` context manager | Python 3.11 (Oct 2022) | Cleaner API, works with structured concurrency. |

**Deprecated/outdated:**
- `typer-cli`: Deprecated. All functionality merged into `typer` 0.12.1+.
- `claude-code-sdk`: Renamed to `claude-agent-sdk` (Sep 2025). Both package names install the same thing, but `claude-agent-sdk` is canonical.
- Pydantic v1 API: `.dict()`, `.parse_obj()`, `@validator` -- all replaced in v2. Use `model_dump()`, `model_validate()`, `@field_validator`.
- `setup.py` / `setup.cfg`: Still works but `pyproject.toml` is the modern standard.

## Open Questions

1. **Claude Agent SDK version pinning strategy**
   - What we know: SDK is at v0.1.39, actively developed, API has changed since initial release (renamed, new features).
   - What's unclear: How stable is the v0.1.x API? Will there be breaking changes before v1.0?
   - Recommendation: Pin minimum version (`>=0.1.39`), use adapter pattern to isolate SDK calls. Run tests against latest SDK in CI.

2. **PKG-03 dependency scope: Does claude-agent-sdk count?**
   - What we know: Requirements say "zero dependencies beyond stdlib + Pydantic + Typer + anyio." But the transport layer needs the SDK.
   - What's unclear: Whether the requirement was written before the SDK matured (roadmap mentioned "alpha risk").
   - Recommendation: Add `claude-agent-sdk` as a fourth required dependency. It IS the transport layer. The requirement's spirit is "minimal dependencies" which this satisfies -- the SDK replaces what would otherwise be hundreds of lines of subprocess management code. Document this decision.

3. **Markdown parsing robustness across GSD versions**
   - What we know: Current `.planning/` file formats are well-structured and predictable.
   - What's unclear: How often does GSD change these formats? Are there format version markers?
   - Recommendation: Parse by section header names (resilient to reordering). Add format version detection if config.json ever includes one. Include a "parsing failed" fallback that returns partial data rather than crashing.

4. **Sync vs async CLI boundary**
   - What we know: Typer is synchronous. SDK is async. Need to bridge.
   - What's unclear: Best pattern for sync-to-async bridge in CLI commands.
   - Recommendation: Use `anyio.run()` or `asyncio.run()` inside each CLI command that needs async. Keep state parsing synchronous (no async needed for file I/O). This avoids event loop conflicts.

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) - Full API reference: classes, types, methods, error hierarchy, message types, configuration options
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) - Architecture, capabilities, comparison with CLI and Client SDK
- [Claude Code Headless Mode / CLI](https://code.claude.com/docs/en/headless) - CLI `-p` flag, `--output-format`, `--resume`, session management
- [claude-agent-sdk PyPI](https://pypi.org/project/claude-agent-sdk/) - v0.1.39, Python 3.10+, MIT license
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) - communicate(), pipe deadlock prevention, signal handling
- [Python packaging guide: pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) - PEP 621, `[project.scripts]`, build backends
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/) - BaseModel, computed_field, model_dump_json, model_json_schema
- [Typer docs](https://typer.tiangolo.com/) - CLI framework, version callback, subcommands, entry points

### Secondary (MEDIUM confidence)
- [Hatchling vs setuptools comparison](https://www.oreateai.com/blog/hatchling-vs-setuptools-the-future-of-python-packaging/500f5340e750b19c738ab8e69a86bcaa) - PEP 621 compliance, reproducible builds, defaults
- [Python build backends in 2025](https://medium.com/@dynamicy/python-build-backends-in-2025-what-to-use-and-why-uv-build-vs-hatchling-vs-poetry-core-94dd6b92248f) - Ecosystem adoption data, recommendations
- [AnyIO PyPI](https://pypi.org/project/anyio/) - v4.12.1, subprocess support, Python 3.14+ compatibility
- [Typer PyPI](https://pypi.org/project/typer/) - v0.24.0, actively maintained

### Tertiary (LOW confidence)
- [python-frontmatter](https://python-frontmatter.readthedocs.io/) - Considered but not needed. GSD `.planning/` files don't use YAML frontmatter.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and PyPI. SDK API confirmed via official reference docs.
- Architecture: HIGH - Patterns follow established Python packaging conventions and SDK usage patterns from official docs.
- Pitfalls: HIGH - Based on known Python packaging issues, asyncio patterns, and SDK behavior documented in official sources.

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days -- stack is stable, SDK is actively developed but API is settling)
