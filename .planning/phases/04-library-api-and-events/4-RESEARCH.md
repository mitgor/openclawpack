# Phase 4: Library API and Events - Research

**Researched:** 2026-02-22
**Domain:** Python async library API design, event/callback systems
**Confidence:** HIGH

## Summary

Phase 4 wraps the existing workflow functions (`new_project_workflow`, `plan_phase_workflow`, `execute_phase_workflow`, `status_workflow`) behind a clean public library API and adds a lifecycle event system that fires callbacks for key state transitions. The codebase is well-positioned for this: all four workflow functions already exist as standalone async functions returning `CommandResult` Pydantic models. The library API layer is primarily a thin facade that re-exports these functions under cleaner names (`create_project`, `plan_phase`, `execute_phase`, `get_status`) from `openclawpack.__init__` and ensures they return typed Pydantic models (INT-02) rather than raw dicts.

The event system must support two modes: Python callbacks for library consumers (INT-03) and JSON event lines to stdout for CLI consumers (INT-04). Since PKG-03 mandates zero dependencies beyond Pydantic + Typer + anyio, and the event system needed here is simple (five event types, fire-and-forget semantics, no filtering by sender), a lightweight hand-rolled emitter (under 100 lines) is the right choice. External libraries like blinker (v1.9.0, zero-dep, async-capable) would work technically but violate PKG-03.

**Primary recommendation:** Build a minimal `EventBus` class with `on()`, `emit()`, and `emit_async()` methods, integrate it as a parameter on the public API functions, and have the CLI layer install a JSON-line emitter that writes events to stdout.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INT-01 | Python library API exposes async functions: `create_project()`, `plan_phase()`, `execute_phase()`, `get_status()` | Existing workflow functions are already async and return `CommandResult`. Library API is a thin re-export facade with cleaner signatures. `get_status` wraps the sync `status_workflow` in an async wrapper for API consistency. |
| INT-02 | Library returns typed Pydantic models, not raw dicts | `CommandResult` is already a Pydantic `BaseModel`. Status currently returns a raw dict inside `CommandResult.result` -- needs a typed `ProjectStatus` model. All other commands return string results from Claude output which are fine as-is. |
| INT-03 | Event hook system fires callbacks on: phase_complete, plan_complete, error, decision_needed, progress_update | Requires a new `EventBus` class and `Event` model hierarchy. Callbacks registered via `bus.on("phase_complete", handler)`. Events fired at key points in workflow functions. |
| INT-04 | Hooks work in both library mode (Python callbacks) and CLI mode (JSON events to stdout) | CLI layer installs a default JSON-line handler on the bus that serializes events to stdout. Library consumers register their own handlers. Both modes use the same `EventBus` plumbing. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python asyncio | stdlib | Async runtime for library API | Already used throughout codebase via anyio |
| anyio | >=4.8 | Async abstraction layer | Already a project dependency; provides `from_thread.run()` for sync wrappers |
| pydantic | >=2.12 | Typed event and result models | Already a project dependency; `CommandResult` is Pydantic |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing / typing_extensions | stdlib | Protocol types for callback signatures | Define `EventHandler` protocol type |
| enum | stdlib | Event type enumeration | `EventType` enum for the five event kinds |
| dataclasses | stdlib | Lightweight event data containers | Alternative to Pydantic for internal-only event payloads (but Pydantic preferred for consistency) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled EventBus | blinker 1.9.0 | blinker is zero-dep, MIT, has native `send_async()` -- but adding it violates PKG-03 ("zero deps beyond pydantic + typer + anyio"). Not worth the constraint violation for a ~80-line class. |
| Hand-rolled EventBus | pyee | Adds a dependency, Node-style API is foreign to Python ecosystem |
| Pydantic event models | Plain dicts | Loses type safety; contradicts INT-02 principle |
| asyncio.Event | Custom EventBus | `asyncio.Event` is a synchronization primitive, not a pub/sub system |

**No new packages to install.** Phase 4 uses only existing dependencies.

## Architecture Patterns

### Recommended Project Structure

```
src/openclawpack/
├── __init__.py          # PUBLIC API: re-export create_project, plan_phase, etc.
├── api.py               # NEW: async library functions (thin wrappers over workflows)
├── events/
│   ├── __init__.py      # Re-export EventBus, EventType, Event
│   ├── bus.py           # NEW: EventBus class with on/off/emit/emit_async
│   ├── types.py         # NEW: EventType enum, Event model, handler protocol
│   └── cli_handler.py   # NEW: JSON-line stdout handler for CLI mode
├── cli.py               # MODIFIED: install CLI event handler before commands
├── commands/             # MODIFIED: workflow functions accept optional EventBus
│   ├── engine.py        # MODIFIED: emit events during workflow execution
│   └── ...
└── output/
    └── schema.py        # MODIFIED: possibly add ProjectStatus model
```

### Pattern 1: Thin Facade over Existing Workflows

**What:** The public `api.py` functions are thin async wrappers around existing `*_workflow()` functions, adding event bus injection and ensuring typed return values.

**When to use:** When existing internal functions already do the work but the public interface needs to be cleaner, more stable, and decoupled from internal structure.

**Example:**
```python
# src/openclawpack/api.py

from openclawpack.events import EventBus, EventType
from openclawpack.output.schema import CommandResult

async def create_project(
    idea: str,
    *,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
    resume_session_id: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Create a new GSD project from an idea.

    Returns a typed CommandResult with success/error state.
    """
    from openclawpack.commands.new_project import new_project_workflow

    bus = event_bus or EventBus()
    result = await new_project_workflow(
        idea=idea,
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout,
        answer_overrides=answer_overrides,
        resume_session_id=resume_session_id,
    )
    if result.success:
        await bus.emit_async(EventType.PROGRESS_UPDATE, {
            "command": "create_project",
            "status": "complete",
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "create_project",
            "errors": result.errors,
        })
    return result
```

### Pattern 2: Minimal EventBus with Sync + Async Support

**What:** A lightweight pub/sub class that supports both sync callbacks and async coroutine callbacks, with named event types.

**When to use:** When you need fire-and-forget event notification without the complexity of a full signal library.

**Example:**
```python
# src/openclawpack/events/bus.py

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine, Union

from openclawpack.events.types import Event, EventType

logger = logging.getLogger(__name__)

# Handler can be sync or async
EventHandler = Union[
    Callable[[Event], None],
    Callable[[Event], Coroutine[Any, Any, None]],
]


class EventBus:
    """Lightweight event bus for lifecycle notifications.

    Supports both synchronous and async handlers.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a handler for an event type."""
        self._handlers[event_type].remove(handler)

    async def emit_async(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """Emit an event, awaiting async handlers and calling sync handlers."""
        event = Event(type=event_type, data=data or {})
        for handler in self._handlers.get(event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Event handler error for %s", event_type)

    def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """Emit an event synchronously (for CLI mode). Skips async handlers."""
        event = Event(type=event_type, data=data or {})
        for handler in self._handlers.get(event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    # Can't await in sync context -- log and close
                    result.close()
                    logger.warning("Async handler skipped in sync emit for %s", event_type)
            except Exception:
                logger.exception("Event handler error for %s", event_type)
```

### Pattern 3: Typed Event Models

**What:** Pydantic models for event payloads, ensuring type safety for both library and CLI consumers.

**Example:**
```python
# src/openclawpack/events/types.py

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class EventType(str, Enum):
    """Lifecycle event types."""
    PHASE_COMPLETE = "phase_complete"
    PLAN_COMPLETE = "plan_complete"
    ERROR = "error"
    DECISION_NEEDED = "decision_needed"
    PROGRESS_UPDATE = "progress_update"


class Event(BaseModel):
    """A lifecycle event with type and arbitrary data payload."""
    type: EventType
    data: dict[str, Any] = {}

    def to_json_line(self) -> str:
        """Serialize to a single JSON line for CLI event output."""
        return self.model_dump_json()
```

### Pattern 4: CLI Event Handler (JSON Lines to Stdout)

**What:** A pre-built handler that serializes events as JSON lines to stdout, satisfying INT-04 for CLI mode.

**Example:**
```python
# src/openclawpack/events/cli_handler.py

import sys
from openclawpack.events.types import Event


def cli_json_handler(event: Event) -> None:
    """Write event as a JSON line to stdout."""
    # Prefix with event: to distinguish from command output
    print(f"event: {event.to_json_line()}", file=sys.stderr, flush=True)
```

### Pattern 5: Public API in `__init__.py`

**What:** The package `__init__.py` re-exports the public API functions so users can `from openclawpack import create_project`.

**Example:**
```python
# src/openclawpack/__init__.py
"""OpenClawPack: AI agent control over the GSD framework via Claude Code."""

from openclawpack._version import __version__

# Lazy imports for public library API (avoid loading SDK at import time)
def __getattr__(name: str):
    _api_names = {"create_project", "plan_phase", "execute_phase", "get_status"}
    if name in _api_names:
        from openclawpack import api
        return getattr(api, name)

    _event_names = {"EventBus", "EventType", "Event"}
    if name in _event_names:
        from openclawpack import events
        return getattr(events, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "__version__",
    "create_project",
    "plan_phase",
    "execute_phase",
    "get_status",
    "EventBus",
    "EventType",
    "Event",
]
```

### Anti-Patterns to Avoid

- **Eagerly importing SDK in `__init__.py`:** This breaks PKG-04 (--version/--help must work without Claude Code). All SDK-dependent imports must remain lazy.
- **Event bus as global singleton:** Creates testing headaches and hidden coupling. Pass the bus explicitly or use a factory default.
- **Async-only public API without sync wrappers:** Many consumers will call from synchronous code. Each async function needs a `*_sync()` companion or the bus needs to handle both.
- **Emitting events after the result is returned:** Events should fire before return so subscribers see them in causal order.
- **Catching all exceptions in event handlers silently:** Log errors but do not let handler failures crash the main workflow.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pydantic model serialization | Custom JSON serializer | `model_dump_json()` / `model_dump()` | Pydantic handles edge cases (datetime, enums, nested models) |
| Async-to-sync bridging | Manual `asyncio.run()` in each function | `anyio.from_thread.run()` (pattern already in codebase) | Handles event loop detection, works with anyio backends |
| Typed enums with string values | String constants dict | `enum.Enum` with `str` mixin (`class EventType(str, Enum)`) | IDE completion, exhaustiveness checks, serialization |

**Key insight:** The event bus IS the one thing we hand-roll, because it's simpler than adding a dependency and the requirements are minimal (5 event types, no filtering, no sender identity). Everything else uses existing tools.

## Common Pitfalls

### Pitfall 1: Breaking PKG-04 with Eager Imports

**What goes wrong:** Adding `from openclawpack.api import create_project` at module level in `__init__.py` causes `openclawpack --version` to fail when Claude Code SDK is not installed.
**Why it happens:** `api.py` -> workflow functions -> `engine.py` -> `client.py` -> `claude_agent_sdk` import chain.
**How to avoid:** Use `__getattr__` lazy import pattern in `__init__.py` (already established in `transport/__init__.py` and `commands/__init__.py`).
**Warning signs:** `openclawpack --version` throws `ModuleNotFoundError` for `claude_agent_sdk`.

### Pitfall 2: Event Bus Reference Leaks in Long-Running Processes

**What goes wrong:** Handlers accumulate if consumers register but never unregister, especially in test suites.
**Why it happens:** No lifecycle management for the bus instance.
**How to avoid:** Provide `off()` method. Document that bus instances should be scoped to a session/operation. In tests, create fresh `EventBus()` per test.
**Warning signs:** Memory growth in long-running agent processes; test pollution.

### Pitfall 3: Mixing async and sync emit incorrectly

**What goes wrong:** Calling `emit()` (sync) when async handlers are registered silently skips them. Calling `emit_async()` from a sync context raises `RuntimeError: no running event loop`.
**Why it happens:** Python cannot await coroutines without an event loop.
**How to avoid:** `emit_async()` for library mode (within async context), `emit()` for CLI mode (sync context, only sync handlers). Document this clearly. CLI handler is always sync.
**Warning signs:** Events that "disappear" -- handler registered but never called.

### Pitfall 4: Status returning raw dict violates INT-02

**What goes wrong:** `get_status()` wraps `status_workflow()` which returns `CommandResult(result=dict)`. The inner `result` is a raw dict, not a typed model.
**Why it happens:** `get_project_summary()` returns a plain dict by design (Phase 1 choice).
**How to avoid:** Either: (a) create a `ProjectStatus` Pydantic model and use it in `get_project_summary`, or (b) validate the dict into a model in the library API layer. Option (a) is cleaner.
**Warning signs:** `type(result.result)` is `dict` instead of a Pydantic model.

### Pitfall 5: Event Emission Timing in Workflows

**What goes wrong:** Events emitted at the wrong point in the workflow -- e.g., `phase_complete` emitted before the result is validated, or `error` not emitted when the workflow catches an exception internally.
**Why it happens:** Workflow functions have broad `except Exception` catches that swallow errors into `CommandResult.error()`.
**How to avoid:** Emit events after the result is constructed but before returning. The `error` event should fire inside the `except` block. The `api.py` layer is the right place for emission since it wraps all workflows.
**Warning signs:** Library consumers miss error events because they were swallowed.

### Pitfall 6: CLI Event Output Conflicting with Command JSON Output

**What goes wrong:** Event JSON lines intermixed with the command result JSON on stdout makes parsing impossible for machine consumers.
**Why it happens:** Both events and results go to stdout.
**How to avoid:** Send event lines to stderr (they're metadata, not the result). Or prefix them with a distinguishing marker (e.g., `event:`) and document the protocol. Stderr is simpler and cleaner.
**Warning signs:** JSON parsers fail because stdout contains multiple JSON objects.

## Code Examples

### Complete Library Usage (Consumer Perspective)

```python
# How an AI agent (OpenClaw) would use the library API
import asyncio
from openclawpack import create_project, plan_phase, execute_phase, get_status
from openclawpack import EventBus, EventType

async def main():
    # 1. Create event bus with custom handler
    bus = EventBus()

    async def on_progress(event):
        print(f"Progress: {event.data}")

    async def on_error(event):
        print(f"Error: {event.data}")

    bus.on(EventType.PROGRESS_UPDATE, on_progress)
    bus.on(EventType.ERROR, on_error)

    # 2. Create project
    result = await create_project(
        idea="Build a todo app with categories",
        project_dir="/tmp/my-project",
        event_bus=bus,
    )
    assert result.success

    # 3. Plan and execute phase 1
    plan_result = await plan_phase(1, project_dir="/tmp/my-project", event_bus=bus)
    exec_result = await execute_phase(1, project_dir="/tmp/my-project", event_bus=bus)

    # 4. Check status (returns typed model)
    status = await get_status(project_dir="/tmp/my-project")
    print(f"Phase: {status.result.current_phase}")  # typed access

asyncio.run(main())
```

### CLI Event Integration

```python
# How cli.py would install the CLI event handler
# Inside the CLI command functions, before calling workflow:

from openclawpack.events import EventBus, EventType
from openclawpack.events.cli_handler import cli_json_handler

def _make_cli_bus() -> EventBus:
    """Create an EventBus with CLI JSON-line handler on all events."""
    bus = EventBus()
    for event_type in EventType:
        bus.on(event_type, cli_json_handler)
    return bus
```

### Typed Status Result

```python
# Upgrading status to return typed model instead of dict

class ProjectStatus(BaseModel):
    """Typed status result for library consumers (INT-02)."""
    current_phase: int
    current_phase_name: str
    progress_percent: float
    blockers: list[str]
    requirements_complete: int
    requirements_total: int
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync-only library APIs | Async-first with sync wrappers | Python 3.10+ mainstream | Library must be async-first (existing codebase already is) |
| Global event buses (singleton) | Explicit bus injection / context vars | 2023+ best practice | Pass bus as parameter, not module-level global |
| blinker for all Python events | Hand-roll for simple cases, blinker for complex | Always true | 5 event types with no sender filtering = hand-roll territory |
| Raw dict returns | Pydantic models | Pydantic v2 (2023) | INT-02 explicitly requires typed models |

**Deprecated/outdated:**
- `asyncio.coroutine` decorator: Use `async def` directly (already the codebase standard)
- `@asyncio.coroutine` + `yield from`: Removed in Python 3.12

## Open Questions

1. **Should `get_status` be truly async or remain sync under the hood?**
   - What we know: `status_workflow()` is synchronous (only reads local files). The library API should present it as `async` for API consistency.
   - What's unclear: Should it be `async def get_status()` that internally just calls the sync function, or should it remain sync?
   - Recommendation: Make it `async def` for API uniformity. Internally, it just calls the sync function (no real I/O to await). This keeps the consumer API consistent: all four functions are async.

2. **Should events carry the full CommandResult or just summary data?**
   - What we know: Events like `phase_complete` need enough data for the subscriber to act on. The full `CommandResult` is available.
   - What's unclear: Is passing the full result too heavy for fire-and-forget events?
   - Recommendation: Events carry a `data: dict[str, Any]` with key fields (command name, success, error messages, phase number). Not the full CommandResult. Keep events lightweight.

3. **Where exactly to emit events -- in api.py or in the workflow functions?**
   - What we know: `api.py` wraps workflows. Workflows have internal error handling.
   - What's unclear: If events are emitted in `api.py` only, we miss intermediate events (e.g., `progress_update` during a long execution).
   - Recommendation: Start with `api.py` as the emission point (pre/post workflow call). For `progress_update` during execution, the bus would need to be threaded into `WorkflowEngine` -- defer this to a follow-up if needed. The phase success criteria don't require mid-execution streaming.

4. **`decision_needed` event -- when does it fire?**
   - What we know: The current architecture auto-answers all questions via `can_use_tool` callback. There is no real "decision needed" pause point.
   - What's unclear: Is `decision_needed` meant for when the answer_map has no match (currently falls back to first option)?
   - Recommendation: Fire `decision_needed` when the answer callback uses the fallback path (no match found). This gives library consumers the chance to know that an unrecognized question appeared, even though it was auto-answered.

## Sources

### Primary (HIGH confidence)

- **Existing codebase analysis** -- Direct reading of all source files in `src/openclawpack/`. All architecture patterns, existing APIs, and constraints derived from code inspection.
- **REQUIREMENTS.md** -- INT-01 through INT-04 requirement definitions; PKG-03 dependency constraint.
- **STATE.md** -- Project decisions history, including PKG-04 lazy import pattern and adapter facade decisions.

### Secondary (MEDIUM confidence)

- [Blinker 1.9.0 documentation](https://blinker.readthedocs.io/en/stable/) -- Verified async support via `send_async()`, confirmed zero dependencies, confirmed MIT license. Considered and rejected due to PKG-03 constraint.
- [Blinker on PyPI](https://pypi.org/project/blinker/) -- Confirmed version 1.9.0, Python >=3.9, no dependencies.
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html) -- async/await patterns, event loop management, coroutine handling.

### Tertiary (LOW confidence)

- [pyee EventEmitter docs](https://pyee.readthedocs.io/en/latest/api/) -- Reviewed as alternative; Node-style API, adds dependency. Not recommended.
- [aiopubsub on PyPI](https://pypi.org/project/aiopubsub/) -- Reviewed as alternative; more complex than needed, adds dependency.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies; all patterns verified against existing codebase
- Architecture: HIGH -- Thin facade pattern directly follows existing codebase conventions (lazy imports, workflow wrappers, Pydantic models)
- Pitfalls: HIGH -- All identified from direct code analysis (PKG-04 import chains, raw dict returns, event timing)
- Event system design: MEDIUM -- Hand-rolled EventBus is straightforward but the exact emit points (especially `decision_needed` and `progress_update`) require design decisions during planning

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain; no fast-moving dependencies)
