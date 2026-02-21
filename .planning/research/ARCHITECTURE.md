# Architecture Research

**Domain:** CLI middleware for AI agent orchestration (subprocess wrapper with structured output)
**Researched:** 2026-02-21
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
                         ┌─────────────────────────────────────────────────────────┐
                         │               Consumers (Callers)                       │
                         │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
                         │  │  OpenClaw    │  │  Shell /      │  │  CI / CD     │   │
                         │  │  (import)    │  │  CLI agent    │  │  scripts     │   │
                         │  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘   │
                         └─────────┼────────────────┼────────────────┼────────────┘
                                   │                │                │
                    ═══════════════╪════════════════╪════════════════╪═════════════
                         ┌─────────┴────────────────┴────────────────┴────────────┐
                         │                   Public API Layer                      │
                         │  ┌──────────────────────┐  ┌─────────────────────────┐ │
                         │  │ CLI (Typer/Click)     │  │ Python Library API      │ │
                         │  │ `openclawpack new`    │  │ `openclawpack.run()`    │ │
                         │  └──────────┬───────────┘  └──────────┬──────────────┘ │
                         └─────────────┼──────────────────────────┼───────────────┘
                                       │                          │
                         ┌─────────────┴──────────────────────────┴───────────────┐
                         │                  Command Router                         │
                         │  Maps CLI verbs / library calls to workflow handlers    │
                         └─────────────────────────┬─────────────────────────────┘
                                                   │
                         ┌─────────────────────────┴─────────────────────────────┐
                         │                  Workflow Engine                        │
                         │  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │
                         │  │ new-project│  │ plan-phase │  │ execute-phase  │   │
                         │  └─────┬──────┘  └─────┬──────┘  └──────┬─────────┘   │
                         │        │               │                │              │
                         │  ┌─────┴───────────────┴────────────────┴──────────┐  │
                         │  │            Workflow Step Sequencer               │  │
                         │  │  (hooks: before_step, after_step, on_error)      │  │
                         │  └──────────────────────┬──────────────────────────┘  │
                         └─────────────────────────┼─────────────────────────────┘
                                                   │
                    ═══════════════════════════════╪══════════════════════════════
                         ┌─────────────────────────┴─────────────────────────────┐
                         │               Subprocess Transport                     │
                         │  ┌───────────────┐  ┌─────────────┐  ┌─────────────┐  │
                         │  │ Process       │  │ NDJSON      │  │ Error &     │  │
                         │  │ Lifecycle Mgr │  │ Stream      │  │ Retry       │  │
                         │  │ (spawn/kill)  │  │ Parser      │  │ Handler     │  │
                         │  └───────┬───────┘  └──────┬──────┘  └──────┬──────┘  │
                         └──────────┼─────────────────┼───────────────┼──────────┘
                                    │                 │               │
                    ════════════════╪═════════════════╪═══════════════╪═══════════
                         ┌──────────┴─────────────────┴───────────────┴──────────┐
                         │                Claude Code CLI Process                 │
                         │  `claude -p "..." --output-format stream-json`         │
                         │  (Node.js process with GSD skills loaded)              │
                         └────────────────────────────┬──────────────────────────┘
                                                      │
                         ┌────────────────────────────┴──────────────────────────┐
                         │                  State Layer                           │
                         │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │
                         │  │ .planning/  │  │ Project      │  │ Artifact    │  │
                         │  │ File I/O    │  │ Registry     │  │ Parser      │  │
                         │  └─────────────┘  └──────────────┘  └─────────────┘  │
                         └───────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **CLI Interface** | Parses shell arguments, validates input, returns exit codes + JSON to stdout | Command Router, consumers via stdout |
| **Library API** | Python-importable async functions, returns typed dataclasses/dicts | Command Router, consumers via return values |
| **Command Router** | Maps command names to workflow handlers, validates required state preconditions | CLI/Library API (inbound), Workflow Engine (outbound) |
| **Workflow Engine** | Sequences multi-step operations (e.g., research -> plan -> execute), fires event hooks | Command Router (inbound), Subprocess Transport + State Layer (outbound) |
| **Subprocess Transport** | Spawns `claude` CLI processes, streams NDJSON, manages lifecycle (timeout, kill, retry) | Workflow Engine (inbound), Claude CLI process (outbound via stdin/stdout) |
| **NDJSON Stream Parser** | Reads newline-delimited JSON from subprocess stdout, yields typed message objects | Subprocess Transport (called by), Workflow Engine (yields to) |
| **Error & Retry Handler** | Catches subprocess failures (exit codes, malformed JSON, timeouts), applies retry policies | Subprocess Transport (wraps) |
| **State Layer** | Reads/writes `.planning/` files, tracks multi-project registry, parses GSD artifacts (ROADMAP.md, STATE.md, config.json) | Workflow Engine (called by), filesystem (I/O) |
| **Event Hook System** | Dispatches lifecycle events (phase_started, step_complete, error, decision_needed) to registered callbacks | Workflow Engine (emits), consumers (subscribe) |
| **Project Registry** | Tracks multiple projects by path, stores per-project metadata and active session state | State Layer (component of), Workflow Engine (queried by) |

## Recommended Project Structure

```
openclawpack/
├── src/
│   └── openclawpack/
│       ├── __init__.py            # Public API exports
│       ├── api.py                 # Library-facing async functions
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py             # Typer/Click app definition
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── new_project.py # `openclawpack new-project`
│       │   │   ├── plan_phase.py  # `openclawpack plan-phase`
│       │   │   ├── execute.py     # `openclawpack execute-phase`
│       │   │   ├── status.py      # `openclawpack status`
│       │   │   └── config.py      # `openclawpack config`
│       │   └── formatters.py      # JSON/text output formatting
│       ├── workflows/
│       │   ├── __init__.py
│       │   ├── base.py            # Base workflow class with hook points
│       │   ├── new_project.py     # Multi-step: questions -> research -> plan
│       │   ├── plan_phase.py      # research -> plan -> verify
│       │   └── execute_phase.py   # plan execution orchestration
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── process.py         # Subprocess lifecycle (spawn, kill, timeout)
│       │   ├── stream.py          # NDJSON reader / message parser
│       │   ├── protocol.py        # Message types (dataclasses for typed messages)
│       │   └── errors.py          # Transport-specific error types
│       ├── state/
│       │   ├── __init__.py
│       │   ├── artifacts.py       # Parse/write .planning/ files (markdown + YAML frontmatter)
│       │   ├── registry.py        # Multi-project registry
│       │   └── models.py          # Dataclasses: ProjectState, PhaseState, PlanState
│       ├── hooks/
│       │   ├── __init__.py
│       │   └── events.py          # Event emitter + hook registration
│       └── errors.py              # Top-level error hierarchy
├── tests/
│   ├── unit/
│   │   ├── test_transport.py
│   │   ├── test_stream.py
│   │   ├── test_artifacts.py
│   │   └── test_workflows.py
│   ├── integration/
│   │   ├── test_subprocess.py     # Actually spawns claude (requires CLI)
│   │   └── test_end_to_end.py
│   └── fixtures/
│       ├── sample_ndjson/         # Captured stream-json output for replay
│       ├── sample_planning/       # .planning/ directory snapshots
│       └── mock_claude.py         # Fake subprocess for unit tests
├── pyproject.toml
└── README.md
```

### Structure Rationale

- **`cli/` separate from `api.py`**: CLI is a thin wrapper that calls the same functions available to library consumers. The CLI handles argument parsing and output formatting; `api.py` handles logic. This enables the "dual interface" pattern where `openclawpack.new_project(idea="...")` and `openclawpack new-project --idea "..."` call identical codepaths.
- **`transport/` isolated**: Subprocess management is the highest-risk, most testable boundary. Isolating it allows mock-based unit testing (replay captured NDJSON) without needing the Claude CLI installed.
- **`workflows/` as orchestrators**: Each workflow encodes the multi-step sequence for a GSD operation. Workflows call transport for Claude interactions and state for file I/O. They never bypass these boundaries.
- **`state/` as file abstraction**: All `.planning/` file access goes through `state/`. This is the integration surface with GSD -- we read GSD's artifacts but delegate mutation to GSD via Claude subprocess calls where possible.
- **`hooks/` decoupled**: Event system is its own module because consumers (OpenClaw, CI scripts) need to register callbacks without importing workflow internals.

## Architectural Patterns

### Pattern 1: Transport Abstraction (Critical Path)

**What:** The Subprocess Transport wraps `asyncio.create_subprocess_exec()` with a higher-level interface that hides process lifecycle, NDJSON streaming, and error recovery behind a single async generator.

**When to use:** Every interaction with Claude Code CLI.

**Trade-offs:** Adds a layer of indirection, but this layer is what makes the entire system testable and reliable. Without it, every workflow becomes tightly coupled to subprocess behavior.

**Example:**
```python
# transport/process.py
import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class TransportConfig:
    claude_path: str = "claude"
    timeout_seconds: int = 300
    max_retries: int = 2
    working_directory: str | None = None

@dataclass
class ClaudeMessage:
    type: str           # "user", "assistant", "system", "result"
    content: dict       # Parsed JSON content
    raw: str            # Original line for debugging

class SubprocessTransport:
    """Manages a single Claude CLI subprocess interaction."""

    def __init__(self, config: TransportConfig):
        self.config = config
        self._process: asyncio.subprocess.Process | None = None

    async def run(
        self,
        prompt: str,
        *,
        allowed_tools: list[str] | None = None,
        system_prompt_append: str | None = None,
        json_schema: dict | None = None,
    ) -> AsyncIterator[ClaudeMessage]:
        """Spawn claude -p, stream NDJSON, yield typed messages."""
        cmd = [self.config.claude_path, "-p", prompt,
               "--output-format", "stream-json",
               "--verbose"]
        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])
        if system_prompt_append:
            cmd.extend(["--append-system-prompt", system_prompt_append])

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.config.working_directory,
        )

        try:
            async for line in self._read_lines():
                parsed = json.loads(line)
                yield ClaudeMessage(
                    type=parsed.get("type", "unknown"),
                    content=parsed,
                    raw=line,
                )
        finally:
            await self._cleanup()

    async def _read_lines(self) -> AsyncIterator[str]:
        """Read NDJSON lines from stdout with timeout."""
        assert self._process and self._process.stdout
        while True:
            try:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=self.config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise TransportTimeoutError(self.config.timeout_seconds)
            if not line:
                break
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

    async def _cleanup(self):
        if self._process and self._process.returncode is None:
            self._process.terminate()
            await self._process.wait()
```

### Pattern 2: Workflow-as-Orchestrator (GSD Alignment)

**What:** Each workflow encodes a multi-step GSD operation as a sequence of subprocess calls interspersed with state reads/writes and hook dispatches. Mirrors GSD's own orchestrator pattern where thin workflows coordinate specialized subagent calls.

**When to use:** Any multi-step command (new-project, plan-phase, execute-phase).

**Trade-offs:** More files than a monolithic approach, but each workflow is independently testable and the step sequence is explicit, not buried in conditionals.

**Example:**
```python
# workflows/new_project.py
from openclawpack.transport import SubprocessTransport
from openclawpack.state import ProjectState, ArtifactManager
from openclawpack.hooks import EventEmitter, Events

class NewProjectWorkflow:
    def __init__(
        self,
        transport: SubprocessTransport,
        state: ArtifactManager,
        hooks: EventEmitter,
    ):
        self.transport = transport
        self.state = state
        self.hooks = hooks

    async def run(self, idea: str, answers: dict | None = None) -> dict:
        """Execute full new-project flow: questions -> research -> roadmap."""
        await self.hooks.emit(Events.WORKFLOW_STARTED, {"workflow": "new-project"})

        # Step 1: Generate project definition
        prompt = self._build_project_prompt(idea, answers)
        result = await self._run_claude_step(prompt, step="project-definition")

        # Step 2: Read generated artifacts
        project = await self.state.load_project()
        await self.hooks.emit(Events.STEP_COMPLETE, {"step": "project-definition"})

        # Step 3: Research phase (if enabled in config)
        config = await self.state.load_config()
        if config.get("workflow", {}).get("research", True):
            await self._run_claude_step(
                "Run /gsd:new-project research phase",
                step="research",
            )
            await self.hooks.emit(Events.STEP_COMPLETE, {"step": "research"})

        # Step 4: Generate roadmap
        await self._run_claude_step(
            "Run /gsd:new-project roadmap generation",
            step="roadmap",
        )
        await self.hooks.emit(Events.STEP_COMPLETE, {"step": "roadmap"})

        await self.hooks.emit(Events.WORKFLOW_COMPLETE, {"workflow": "new-project"})
        return await self.state.load_project_summary()
```

### Pattern 3: Dual Interface (CLI + Library)

**What:** A single set of core functions exposed both as CLI commands (via Typer/Click decorators) and as importable async Python functions. The CLI is a thin formatting layer on top of the library.

**When to use:** Always. This is a foundational pattern for the project.

**Trade-offs:** Requires discipline to keep the CLI layer truly thin. The temptation is to add CLI-specific logic that then isn't available to library consumers.

**Example:**
```python
# api.py (library interface)
async def new_project(
    idea: str,
    project_dir: str = ".",
    answers: dict | None = None,
    hooks: dict | None = None,
) -> ProjectResult:
    """Create a new GSD project from an idea. Returns structured result."""
    ...

# cli/commands/new_project.py (CLI interface)
import typer
import asyncio
import json
from openclawpack.api import new_project

app = typer.Typer()

@app.command()
def new(
    idea: str = typer.Argument(..., help="Project idea description"),
    project_dir: str = typer.Option(".", help="Target directory"),
    output_format: str = typer.Option("json", help="Output format"),
):
    """Create a new GSD project from an idea."""
    result = asyncio.run(new_project(idea=idea, project_dir=project_dir))
    if output_format == "json":
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(result.to_text())
```

### Pattern 4: Event Hook System

**What:** A lightweight pub/sub system where workflows emit named events and consumers register callbacks. Supports both sync and async callbacks using the "await me maybe" pattern.

**When to use:** When consumers need lifecycle visibility (phase started, step complete, error occurred, decision needed).

**Trade-offs:** Adds complexity vs. simple return values, but essential for long-running operations where the caller needs progress updates.

**Example:**
```python
# hooks/events.py
import asyncio
import inspect
from enum import Enum
from typing import Callable, Any

class Events(str, Enum):
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETE = "workflow.complete"
    STEP_COMPLETE = "step.complete"
    SUBPROCESS_SPAWNED = "subprocess.spawned"
    SUBPROCESS_MESSAGE = "subprocess.message"
    SUBPROCESS_EXITED = "subprocess.exited"
    ERROR = "error"
    DECISION_NEEDED = "decision.needed"

class EventEmitter:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: Events | str, handler: Callable) -> None:
        key = str(event)
        self._handlers.setdefault(key, []).append(handler)

    async def emit(self, event: Events | str, data: Any = None) -> None:
        for handler in self._handlers.get(str(event), []):
            result = handler(data)
            if inspect.isawaitable(result):
                await result
```

## Data Flow

### Primary Request Flow: CLI Command to Structured Output

```
Consumer (agent / shell)
    │
    │  `openclawpack new-project --idea "todo app"`
    │  or: `await openclawpack.new_project(idea="todo app")`
    ▼
┌──────────────────────────────┐
│  Public API Layer            │
│  - Validates input           │
│  - Resolves project dir      │
│  - Creates workflow instance  │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  Workflow Engine             │
│  - Loads project state       │     hook: workflow.started
│  - Builds Claude prompt      │
│  - Includes pre-filled       │
│    answers (non-interactive) │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  Subprocess Transport        │
│  - Spawns: `claude -p "..."  │
│    --output-format           │
│    stream-json --verbose`    │
│  - Pipes prompt to stdin     │     hook: subprocess.spawned
│  - Reads NDJSON from stdout  │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  NDJSON Stream Parser        │
│  - readline() loop           │
│  - JSON.parse each line      │
│  - Yield typed ClaudeMessage │     hook: subprocess.message (per line)
│  - Detect ResultMessage      │
│    (terminal signal)         │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  Workflow Engine             │
│  - Collects result           │
│  - Reads updated .planning/  │
│    files from filesystem     │     hook: step.complete
│  - Sequences next step       │
│    (or returns final result) │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  State Layer                 │
│  - Parse .planning/STATE.md  │
│  - Parse .planning/ROADMAP.md│
│  - Build ProjectResult       │     hook: workflow.complete
│    dataclass                 │
└──────────────┬───────────────┘
               ▼
Consumer receives structured JSON / Python dict
```

### State Management Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Filesystem (.planning/)                       │
│                                                                      │
│  PROJECT.md ──→ read-only by openclawpack (written by GSD via Claude)│
│  ROADMAP.md ──→ read-only (parsed for phase/plan structure)          │
│  STATE.md   ──→ read-only (parsed for current position + decisions)  │
│  config.json ─→ read-only (parsed for workflow preferences)          │
│  phases/**  ──→ read-only (PLAN.md, SUMMARY.md parsed for status)    │
│  research/** ─→ read-only (research artifacts)                       │
│                                                                      │
│  NOTE: openclawpack READS these files but does NOT write them.       │
│  Mutations happen through Claude subprocess executing GSD skills.    │
│  This preserves GSD as the source of truth for state transitions.    │
└──────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────────┐
openclawpack's own      │  Project Registry    │
state (separate from    │  ~/.openclawpack/    │
GSD artifacts):         │    projects.json     │  ← tracks registered projects
                        │    sessions/         │  ← session IDs for --continue
                        └──────────────────────┘
```

### Multi-Project Concurrent Execution

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Project Registry                                │
│  ~/.openclawpack/projects.json                                       │
│  {                                                                   │
│    "projects": {                                                     │
│      "todo-app": {                                                   │
│        "path": "/home/user/todo-app",                                │
│        "active_session": "sess_abc123",                              │
│        "current_phase": "01",                                        │
│        "status": "executing"                                         │
│      },                                                              │
│      "blog-engine": {                                                │
│        "path": "/home/user/blog",                                    │
│        "active_session": null,                                       │
│        "current_phase": "02",                                        │
│        "status": "planned"                                           │
│      }                                                               │
│    }                                                                 │
│  }                                                                   │
└──────────────────────────────────────────────────────────────────────┘

Each project gets its own:
  - Working directory (cwd for subprocess)
  - Claude session ID (for --continue/--resume)
  - Independent .planning/ state

Projects run concurrently via asyncio.gather():
  - Each subprocess is independent (separate claude process)
  - No shared state between project subprocesses
  - Registry provides coordination (which projects exist, their status)
```

### Key Data Flows

1. **Non-Interactive Question Answering:** Consumer provides pre-filled answers dict -> Workflow builds a prompt that includes all answers inline -> Claude receives prompt with context, never triggers AskUserQuestion -> Result flows back as NDJSON. This is the core innovation: converting GSD's interactive questions into pre-filled non-interactive prompts.

2. **Phase Status Querying:** Consumer asks for project status -> State layer reads STATE.md + ROADMAP.md + scans phases/ for SUMMARY.md existence -> Computes phase completion percentages -> Returns structured status (no subprocess needed for read-only queries).

3. **Error Recovery:** Subprocess exits non-zero or times out -> Error handler captures stderr + exit code -> Retry logic applies (configurable retries with backoff) -> If all retries fail, error event emitted with full context -> Consumer decides next action.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 project, sequential | Single subprocess, synchronous workflow steps. No registry needed. |
| 3-5 projects, concurrent | Project registry for tracking. asyncio.gather() for parallel phase execution. Session ID management for --resume across projects. |
| 10+ projects | Process pool with semaphore limiting concurrent Claude subprocesses (API rate limits, system resources). Queue-based scheduling. Health monitoring per subprocess. |

### Scaling Priorities

1. **First bottleneck: Claude CLI subprocess limits.** Each running project needs its own Claude process. On a single machine, 3-5 concurrent processes is practical. Beyond that, implement a semaphore (`asyncio.Semaphore`) to queue excess requests. The transport layer already isolates this concern.

2. **Second bottleneck: Session management.** GSD conversations use --continue/--resume to maintain context. With many projects, session ID tracking becomes critical. The project registry handles this, but at scale you may need to persist session metadata more robustly (SQLite instead of JSON file).

3. **Third bottleneck: State file contention.** Multiple rapid reads of .planning/ files are fine (read-only). But if two workflows try to trigger GSD mutations on the same project simultaneously, the .planning/ files could get into an inconsistent state. Enforce single-writer-per-project at the workflow level.

## Anti-Patterns

### Anti-Pattern 1: Reimplementing GSD Logic in Python

**What people do:** Parse ROADMAP.md and implement phase state transitions directly in Python, bypassing GSD's workflow.
**Why it's wrong:** GSD's state machine (Uninitialized -> ProjectDefined -> PhaseReady -> Planned -> Executing -> Verified -> Complete) has nuanced transition rules, validation, and side effects. Reimplementing these creates a divergent state machine that breaks when GSD updates.
**Do this instead:** Always delegate state mutations to GSD by running the appropriate Claude command. Read artifacts for status queries, but never write them directly.

### Anti-Pattern 2: Synchronous Subprocess Calls

**What people do:** Use `subprocess.run()` (blocking) instead of `asyncio.create_subprocess_exec()`.
**Why it's wrong:** Claude CLI calls take 10-120+ seconds. Blocking the event loop prevents concurrent project management, progress callbacks, and timeout handling.
**Do this instead:** All subprocess interactions must be async. Use asyncio transport from the start.

### Anti-Pattern 3: Parsing Claude's Markdown Output

**What people do:** Run Claude with `--output-format text` and parse the markdown response with regex.
**Why it's wrong:** Markdown output is for humans. It's fragile, changes between Claude versions, and lacks structured metadata (session ID, token usage, tool calls).
**Do this instead:** Always use `--output-format stream-json` or `--output-format json`. Parse the structured JSON, which includes message types, content blocks, and metadata.

### Anti-Pattern 4: Monolithic Prompt Construction

**What people do:** Build one giant prompt string with all project context, answers, and instructions concatenated.
**Why it's wrong:** Exceeds context limits, wastes tokens, and makes debugging impossible. GSD already manages context loading within its skills.
**Do this instead:** Use `--append-system-prompt` for middleware instructions. Let GSD handle its own context loading. Pass only the necessary information: the command to run, pre-filled answers, and any overrides.

### Anti-Pattern 5: Shared Mutable State Between Projects

**What people do:** Use a global in-memory dict for project state that multiple concurrent workflows read/write.
**Why it's wrong:** Race conditions. Two workflows checking "is phase 1 complete?" and both proceeding to phase 2 simultaneously.
**Do this instead:** Each project gets file-system-isolated state (.planning/ per project dir). The registry is append-only metadata. Workflow-level locking (one active workflow per project) prevents concurrent mutation.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Claude Code CLI** | Subprocess (stdin/stdout NDJSON) | Primary integration. Must be installed + authenticated. Use `claude -p` with `--output-format stream-json`. |
| **GSD Framework** | Indirect via Claude CLI | GSD skills execute inside Claude's context. We invoke them by describing the GSD command in the prompt (e.g., "Run /gsd:plan-phase 1"). |
| **Claude Agent SDK** (`claude-agent-sdk`)  | Alternative to raw subprocess | Anthropic's official Python SDK wraps subprocess management. Consider using instead of raw subprocess for process lifecycle, but evaluate whether it constrains GSD skill invocation. Current version 0.1.39 (Feb 2026). |
| **Filesystem (.planning/)** | Direct file read (Python pathlib) | Read-only access to GSD artifacts. Parse markdown with YAML frontmatter. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **CLI <-> Library API** | Direct function call | CLI commands call `api.py` functions. No serialization needed. |
| **Library API <-> Workflow** | Object instantiation + async call | API creates workflow with injected dependencies (transport, state, hooks). |
| **Workflow <-> Transport** | Async generator (yield ClaudeMessage) | Workflow iterates over transport.run() output. Clean producer/consumer. |
| **Workflow <-> State** | Sync/async file reads returning dataclasses | State layer parses .planning/ files into typed Python objects. |
| **Workflow <-> Hooks** | Fire-and-forget emit() | Workflows emit events. Hooks never block workflow execution (use asyncio.create_task for slow handlers). |
| **Consumer <-> Hooks** | Callback registration (on/off) | Consumers register handlers before starting workflows. |

## Key Architectural Decision: Claude Agent SDK vs. Raw Subprocess

The Claude Agent SDK (`claude-agent-sdk` on PyPI, v0.1.39) provides a pre-built transport layer with typed messages, process lifecycle management, and NDJSON parsing -- exactly what our transport/ module needs to build.

**Option A: Build on Claude Agent SDK**
- Pro: Subprocess lifecycle, NDJSON parsing, typed messages already implemented and maintained by Anthropic
- Pro: Bundles Claude CLI automatically
- Pro: Hooks and permission callbacks built in
- Con: May constrain how we invoke GSD skills (SDK expects prompts, not slash commands)
- Con: Adds a dependency on a fast-moving API (0.1.x version)

**Option B: Build raw subprocess transport**
- Pro: Full control over process arguments, prompt formatting, error handling
- Pro: No dependency on SDK release cadence
- Con: Must implement NDJSON parsing, process lifecycle, timeout handling ourselves

**Recommendation:** Start with Option B (raw subprocess) for the first milestone to understand the integration surface deeply, then evaluate wrapping with Claude Agent SDK in a later phase once the GSD invocation patterns are stable. The transport/ module is designed to make this swap possible without changing workflow code.

## Build Order (Dependency Chain)

The architecture implies a specific build order based on component dependencies:

```
Phase 1: Foundation (no dependencies between these)
  ├── transport/protocol.py      (message dataclasses — zero deps)
  ├── transport/errors.py        (error hierarchy — zero deps)
  ├── state/models.py            (state dataclasses — zero deps)
  └── hooks/events.py            (event emitter — zero deps)

Phase 2: Core I/O (depends on Phase 1 types)
  ├── transport/stream.py        (NDJSON parser — needs protocol.py)
  ├── transport/process.py       (subprocess lifecycle — needs stream.py, errors.py)
  └── state/artifacts.py         (file parser — needs models.py)

Phase 3: Orchestration (depends on Phase 2)
  ├── workflows/base.py          (base class — needs transport, state, hooks)
  ├── state/registry.py          (multi-project — needs models.py)
  └── api.py                     (library API — needs workflows)

Phase 4: Interface (depends on Phase 3)
  ├── cli/app.py                 (CLI entry point — needs api.py)
  └── cli/commands/*.py          (individual commands — needs api.py)

Phase 5: Workflows (depends on Phase 2-3, can parallelize)
  ├── workflows/new_project.py
  ├── workflows/plan_phase.py
  └── workflows/execute_phase.py
```

**Key dependency insight:** The transport layer and state layer are independent of each other. They can be built in parallel. Workflows depend on both. The CLI depends on workflows through the API layer. This means transport + state can be Phase 2 wave items (parallel), and workflows are Phase 3.

## Sources

- [Claude Code Agent SDK (Python) - DeepWiki Architecture](https://deepwiki.com/anthropics/claude-code-sdk-python/1-overview) -- Layered architecture, SubprocessCLITransport, NDJSON streaming, message parser (HIGH confidence)
- [Claude Code Headless / Programmatic Usage](https://code.claude.com/docs/en/headless) -- `claude -p`, `--output-format stream-json`, `--continue`, `--resume` (HIGH confidence, official docs)
- [claude-agent-sdk on PyPI](https://pypi.org/project/claude-agent-sdk/) -- v0.1.39, Python 3.10+, replacement for claude-code-sdk (HIGH confidence)
- [GSD Framework - DeepWiki](https://deepwiki.com/glittercowboy/get-shit-done/15.1-claude-code) -- .planning/ structure, phase lifecycle, orchestrator-subagent pattern (HIGH confidence)
- [GSD GitHub Repository](https://github.com/glittercowboy/get-shit-done) -- Skills, state management, config.json format (HIGH confidence)
- [Claude MPM](https://github.com/bobmatnyc/claude-mpm) -- Multi-project subprocess orchestration with tmux isolation, event-driven inbox (MEDIUM confidence, third-party)
- [jc - CLI to JSON converter](https://github.com/kellyjonbrazil/jc) -- Parser plugin architecture, dual CLI/library interface pattern (MEDIUM confidence, prior art)
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) -- create_subprocess_exec, StreamReader, readline() (HIGH confidence, stdlib docs)
- [python-statemachine](https://python-statemachine.readthedocs.io/en/latest/async.html) -- Async state machine patterns with lifecycle callbacks (MEDIUM confidence)

---
*Architecture research for: CLI middleware / AI agent orchestration*
*Researched: 2026-02-21*
