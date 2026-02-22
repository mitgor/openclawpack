# Phase 5: Multi-Project Management - Research

**Researched:** 2026-02-22
**Domain:** Persistent project registry with CLI subcommand group and cross-platform data storage
**Confidence:** HIGH

## Summary

Phase 5 adds a persistent project registry that lets agents register, list, and remove GSD projects via `openclawpack projects add/list/remove`. This is a self-contained feature with no Claude subprocess dependency -- all operations are local file reads/writes against a JSON registry file stored in a platform-appropriate user data directory.

The technical domain is straightforward: a Typer subcommand group (`app.add_typer(projects_app, name="projects")`) exposes three commands. A `ProjectRegistry` class manages a JSON file containing registered project entries. Each entry stores the project path, a user-friendly name (derived from the directory name), and a "last-known state" snapshot from the existing state parser. The registry file lives in a cross-platform user data directory resolved without adding new dependencies (stdlib `Path.home()` plus platform detection via `sys.platform`).

**Primary recommendation:** Use Typer `add_typer()` for the subcommand group, a Pydantic-backed registry model persisted as JSON, atomic writes via `tempfile` + `os.replace()`, and stdlib-only cross-platform path resolution to stay within PKG-03 constraints.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STATE-03 | Multi-project registry tracks registered projects with paths and last-known state | Registry model stores project entries with path, name, and last-known-state snapshot. State parser (already built in Phase 1) provides the snapshot data. JSON file persisted in user data dir. |
| STATE-04 | Projects can be registered, listed, and removed via `openclawpack projects add/list/remove` | Typer `add_typer()` creates `projects` subcommand group. Three commands map directly: `add` validates path has `.planning/`, `list` reads registry + optionally refreshes state, `remove` deletes entry by name. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | >=2.12 (existing dep) | Registry and entry models with JSON serialization | Already used for all models in the project; `model_dump_json()` / `model_validate_json()` provide round-trip serialization |
| Typer | >=0.24 (existing dep) | `projects` subcommand group via `add_typer()` | Already used for all CLI commands; `add_typer()` is the documented pattern for command groups |
| pathlib (stdlib) | N/A | Cross-platform path resolution and file operations | Zero-dependency path handling, already used throughout codebase |
| tempfile (stdlib) | N/A | Atomic write via `NamedTemporaryFile` + `os.replace()` | Standard pattern for crash-safe file writes without external deps |
| json (stdlib) | N/A | Registry file format (human-readable, debuggable) | Simple, universal, no binary format needed for a small registry |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sys (stdlib) | N/A | `sys.platform` for cross-platform data dir detection | Used in the `_user_data_dir()` helper to distinguish macOS/Linux/Windows |
| os (stdlib) | N/A | `os.replace()` for atomic file rename, `os.environ` for XDG overrides | Used in atomic write and XDG_DATA_HOME detection |
| datetime (stdlib) | N/A | ISO timestamps for `registered_at` and `last_checked_at` fields | Used in registry entry metadata |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib path resolution | `platformdirs` library | Cleaner API but violates PKG-03 (zero deps beyond Pydantic/Typer/anyio). Stdlib approach is ~15 lines. |
| JSON file | SQLite | Overkill for <100 entries; JSON is human-readable and debuggable; out of scope per REQUIREMENTS.md |
| `os.replace()` atomic write | `atomicwrites` library | Extra dependency; `os.replace()` is sufficient for single-writer scenario |
| Pydantic models | Plain dicts | Would break INT-02 pattern; all other models in the project are Pydantic |

## Architecture Patterns

### Recommended Project Structure

```
src/openclawpack/
├── state/
│   ├── __init__.py      # Add ProjectRegistry exports
│   ├── models.py         # Add RegistryEntry model
│   ├── registry.py       # NEW: ProjectRegistry class (read/write/CRUD)
│   ├── parser.py          # Existing (unchanged)
│   └── reader.py          # Existing (unchanged)
├── commands/
│   └── projects.py       # NEW: projects_app Typer + add/list/remove commands
├── api.py                 # Add list_projects(), add_project(), remove_project()
├── cli.py                 # Add: app.add_typer(projects_app, name="projects")
└── __init__.py            # Add lazy re-exports for new API functions
```

### Pattern 1: Typer Subcommand Group

**What:** Use `app.add_typer()` to create `openclawpack projects` as a command group with `add`, `list`, `remove` sub-commands.
**When to use:** When a CLI tool needs grouped commands (like `git remote add/remove`).
**Example:**

```python
# src/openclawpack/commands/projects.py
import typer

projects_app = typer.Typer(help="Manage registered projects.")

@projects_app.command("add")
def projects_add(
    path: str = typer.Argument(..., help="Path to a GSD project directory."),
    name: str | None = typer.Option(None, "--name", "-n", help="Friendly name (defaults to directory name)."),
) -> None:
    """Register a GSD project."""
    ...

@projects_app.command("list")
def projects_list() -> None:
    """List all registered projects."""
    ...

@projects_app.command("remove")
def projects_remove(
    name: str = typer.Argument(..., help="Name of the project to remove."),
) -> None:
    """Remove a registered project."""
    ...

# In cli.py:
# from openclawpack.commands.projects import projects_app
# app.add_typer(projects_app, name="projects")
```

Source: [Typer SubCommands - Single File](https://typer.tiangolo.com/tutorial/subcommands/single-file/)

### Pattern 2: Pydantic-Backed JSON Registry

**What:** A Pydantic `BaseModel` representing the full registry, with `model_dump_json()` / `model_validate_json()` for serialization. Each entry is also a Pydantic model.
**When to use:** When you need validated, typed, serializable data structures with JSON round-tripping.
**Example:**

```python
# src/openclawpack/state/models.py (additions)
class RegistryEntry(BaseModel):
    """A single registered project in the multi-project registry."""
    name: str
    path: str  # Absolute, resolved path
    registered_at: str  # ISO 8601 timestamp
    last_checked_at: str | None = None
    last_known_state: dict[str, Any] | None = None  # Snapshot from get_project_summary()

class ProjectRegistryData(BaseModel):
    """Persistent registry of all registered GSD projects."""
    version: int = 1  # Schema version for future migration
    projects: dict[str, RegistryEntry] = {}  # Keyed by name
```

### Pattern 3: Cross-Platform User Data Directory (No Dependencies)

**What:** Resolve the user data directory using only stdlib, respecting platform conventions and XDG overrides.
**When to use:** When PKG-03 forbids adding `platformdirs` as a dependency.
**Example:**

```python
import os
import sys
from pathlib import Path

def _user_data_dir(appname: str = "openclawpack") -> Path:
    """Return platform-appropriate user data directory.

    - Linux: $XDG_DATA_HOME/openclawpack or ~/.local/share/openclawpack
    - macOS: ~/Library/Application Support/openclawpack
    - Windows: %LOCALAPPDATA%/openclawpack
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux / other Unix
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / appname
```

Source: [XDG Base Directory Spec](https://xdgbasedirectoryspecification.com/), [platformdirs source code patterns](https://platformdirs.readthedocs.io/)

### Pattern 4: Atomic JSON Write

**What:** Write to a temporary file in the same directory, then atomically replace the target. Prevents corruption on crash.
**When to use:** Whenever persisting state to a file that must survive interruption.
**Example:**

```python
import json
import os
import tempfile
from pathlib import Path

def _atomic_write_json(path: Path, data: str) -> None:
    """Atomically write JSON string to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

Source: [Python os.replace docs](https://docs.python.org/3/library/os.html#os.replace), [Atomic write discussion](https://discuss.python.org/t/adding-atomicwrite-in-stdlib/11899)

### Anti-Patterns to Avoid

- **Storing registry in the project directory:** The registry is global (tracks multiple projects), so it belongs in user data dir, not inside any single `.planning/` dir.
- **Using project path as the key:** Paths can change (mounts, symlinks). Use a stable name derived from the directory name, with uniqueness enforcement.
- **Locking the registry file for concurrent access:** Overkill for single-user CLI tool. Atomic write is sufficient. Concurrent multi-agent scenarios are v2 (SCALE-01).
- **Lazy-loading the registry on every CLI invocation:** Only load when a `projects` subcommand is invoked. Non-projects commands should not touch the registry.
- **Adding `platformdirs` as a new dependency:** Violates PKG-03. The stdlib approach is ~15 lines and covers macOS/Linux/Windows.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization with validation | Custom dict parsing | Pydantic `model_dump_json()` / `model_validate_json()` | Handles nested models, validation, defaults, schema evolution |
| Cross-platform user data dir | Ad-hoc `~/.openclawpack` | Stdlib helper following XDG/macOS/Windows conventions | Respects platform conventions, XDG_DATA_HOME overrides |
| CLI subcommand group | Manual argparse/click routing | Typer `add_typer()` | Already used; handles help text, argument parsing, nesting |
| Project state snapshot | Custom state scraping | `get_project_summary()` from `state.reader` | Already built in Phase 1, tested, returns the exact dict we need |
| Atomic file writes | Raw `open().write()` | `tempfile.mkstemp()` + `os.replace()` | Prevents half-written files on crash or power loss |

**Key insight:** Phase 5 primarily composes existing infrastructure (state parser, Pydantic models, Typer CLI, CommandResult envelope) with a thin registry layer. Almost nothing needs to be built from scratch -- the novel code is the registry CRUD class and the cross-platform path helper.

## Common Pitfalls

### Pitfall 1: Registry File Corruption on Crash

**What goes wrong:** Writing JSON directly to the registry file, process is killed mid-write, file is now invalid JSON.
**Why it happens:** Non-atomic writes leave a window where the file content is incomplete.
**How to avoid:** Always use atomic write pattern: write to temp file, fsync, then `os.replace()`.
**Warning signs:** Tests that mock `open()` directly instead of testing through the atomic write path.

### Pitfall 2: Path Resolution Inconsistency

**What goes wrong:** User registers `/foo/../bar/project` and later tries to find it via `/bar/project`. Registry has duplicate entries for the same physical directory.
**How to avoid:** Always `Path(path).resolve()` before storing. Compare resolved paths on add to detect duplicates.
**Warning signs:** Tests that use relative paths without checking they're resolved.

### Pitfall 3: Name Collision on Add

**What goes wrong:** User adds two projects from directories with the same name (e.g., `/home/user/work/myapp` and `/home/user/personal/myapp`). Second silently overwrites first.
**How to avoid:** Check if name already exists before adding. If collision, return an error suggesting `--name` override. Never silently overwrite.
**Warning signs:** Missing uniqueness check in `add` command.

### Pitfall 4: Stale State in Registry

**What goes wrong:** Registry shows "Phase 2, 50% complete" but project has since moved to Phase 4. Agents make decisions on stale data.
**How to avoid:** `last_known_state` is explicitly a snapshot (field name communicates this). `list` command could optionally `--refresh` state by re-reading `.planning/` dirs. Timestamp `last_checked_at` tells consumers how fresh the data is.
**Warning signs:** No timestamp on state snapshots; consumers treating registry state as authoritative.

### Pitfall 5: Breaking PKG-04 with Eager Imports

**What goes wrong:** Adding `from openclawpack.commands.projects import projects_app` at module level in `cli.py` triggers import of the registry module, which might import state models. Chain reaction causes `openclawpack --version` to fail if `pydantic` is not installed.
**How to avoid:** Follow the established lazy-import pattern. In `cli.py`, use lazy import inside a function or behind `TYPE_CHECKING`. The `add_typer()` call itself is safe (just registration), but the command function bodies should use lazy imports for registry operations.
**Warning signs:** `openclawpack --version` test failing after adding projects subcommand.

### Pitfall 6: Non-Existent Project Path on Add

**What goes wrong:** User runs `openclawpack projects add /nonexistent/path` and it registers successfully. Later `list` or state refresh crashes trying to read `.planning/`.
**How to avoid:** Validate on `add`: check path exists AND has a `.planning/` directory. Return clear error if not.
**Warning signs:** No validation in `add` command path handling.

### Pitfall 7: Registry File Doesn't Exist Yet

**What goes wrong:** First-ever `list` or `remove` command crashes because registry file doesn't exist.
**How to avoid:** `ProjectRegistry.load()` returns empty registry when file doesn't exist (same pattern as `ProjectConfig()` defaults in `reader.py`).
**Warning signs:** Tests that pre-create the registry file instead of testing the cold-start path.

## Code Examples

Verified patterns from the existing codebase (high confidence -- these are established project conventions):

### CommandResult Envelope (Existing Pattern)

```python
# Source: src/openclawpack/commands/status.py
# All commands return CommandResult -- projects commands follow the same pattern
from openclawpack.output.schema import CommandResult

def list_projects() -> CommandResult:
    try:
        registry = ProjectRegistry.load()
        entries = [entry.model_dump() for entry in registry.data.projects.values()]
        return CommandResult.ok(result=entries, duration_ms=elapsed)
    except Exception as e:
        return CommandResult.error(str(e))
```

### Lazy Import Pattern (Existing Convention)

```python
# Source: src/openclawpack/cli.py (established PKG-04 pattern)
# projects commands follow the same lazy-import-in-body pattern
@projects_app.command("add")
def projects_add(path: str = typer.Argument(...)) -> None:
    # Lazy import inside body -- not at module level
    from openclawpack.state.registry import ProjectRegistry
    from openclawpack.state.reader import get_project_summary
    ...
```

### Pydantic Model with Defaults (Existing Pattern)

```python
# Source: src/openclawpack/state/models.py
# RegistryEntry follows the same pattern as ProjectConfig
class RegistryEntry(BaseModel):
    name: str
    path: str
    registered_at: str
    last_checked_at: str | None = None
    last_known_state: dict[str, Any] | None = None
```

### API Function Pattern (Existing Convention)

```python
# Source: src/openclawpack/api.py
# New API functions follow the exact same pattern as get_status()
async def list_projects(
    *,
    event_bus: EventBus | None = None,
) -> CommandResult:
    from openclawpack.state.registry import ProjectRegistry
    bus = event_bus or EventBus()
    registry = ProjectRegistry.load()
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `appdirs` for user data dirs | `platformdirs` (maintained fork) | 2022 (appdirs abandoned) | Use platformdirs if adding dep; or stdlib approach for zero-dep |
| Raw `json.dump()` to file | Pydantic `model_dump_json()` with atomic write | Pydantic v2 (2023) | Built-in validation, schema evolution, type safety |
| Click command groups | Typer `add_typer()` | Typer 0.9+ | Simpler API, type hints, same Click internals |

**Deprecated/outdated:**
- `appdirs`: Abandoned; replaced by `platformdirs`. Neither needed here due to PKG-03.
- Pydantic v1 `.json()` / `.parse_raw()`: Replaced by v2 `model_dump_json()` / `model_validate_json()`.

## Open Questions

1. **Should `list` auto-refresh state from project directories?**
   - What we know: The `last_known_state` snapshot will go stale. A `--refresh` flag could re-read each project's `.planning/` on list.
   - What's unclear: Should refresh be the default (slower but accurate) or opt-in (fast but potentially stale)?
   - Recommendation: Make `list` fast by default (read registry only). Add `--refresh` flag that re-reads state for each registered project. This follows the principle of least surprise for agent consumers who may call `list` frequently.

2. **Should `remove` accept path as well as name?**
   - What we know: Success criteria says `remove <name>`. But users might want `remove /path/to/project`.
   - What's unclear: Whether supporting both creates ambiguity (is the argument a name or a path?).
   - Recommendation: Accept name only (per success criteria). If the user provides a path, suggest they use `list` first to find the name. This keeps the interface simple and unambiguous.

3. **Should the registry store the name derivation strategy?**
   - What we know: Name defaults to directory basename. But what if directory is renamed?
   - What's unclear: Whether we need name-update mechanics.
   - Recommendation: Name is immutable once registered. Users can `remove` + `add --name` to rename. Keeps registry logic simple.

4. **Library API surface for Phase 5**
   - What we know: Phase 4 established the `api.py` async function pattern. Phase 5 adds CRUD operations.
   - What's unclear: Whether `add_project()`, `remove_project()`, `list_projects()` need to be async (they're all local file ops).
   - Recommendation: Make them `async` for API consistency (all existing api.py functions are async). The implementation can be sync internally since these are local file operations. This maintains the uniform async interface that library consumers expect.

## Sources

### Primary (HIGH confidence)

- [Typer SubCommands - Single File](https://typer.tiangolo.com/tutorial/subcommands/single-file/) - `add_typer()` pattern for command groups
- [Typer SubCommands - Command Groups](https://typer.tiangolo.com/tutorial/subcommands/) - General subcommand architecture
- [Typer SubCommand Callback Override](https://typer.tiangolo.com/tutorial/subcommands/callback-override/) - Callback precedence in sub-Typers
- [Python os.replace docs](https://docs.python.org/3/library/os.html#os.replace) - Atomic file replacement
- [Python tempfile docs](https://docs.python.org/3/library/tempfile.html) - Temp file creation for atomic writes
- [Python pathlib docs](https://docs.python.org/3/library/pathlib.html) - Path.home() for cross-platform home dir
- Existing codebase: `src/openclawpack/state/`, `src/openclawpack/cli.py`, `src/openclawpack/api.py` - All established patterns

### Secondary (MEDIUM confidence)

- [platformdirs docs](https://platformdirs.readthedocs.io/) - Reference for correct platform paths (used to verify stdlib approach)
- [XDG Base Directory Specification](https://xdgbasedirectoryspecification.com/) - Linux data dir conventions

### Tertiary (LOW confidence)

- [Atomic write discussion on Python.org](https://discuss.python.org/t/adding-atomicwrite-in-stdlib/11899) - Community patterns (not stdlib yet)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components are existing project dependencies or stdlib. No new dependencies needed.
- Architecture: HIGH - Patterns directly follow existing codebase conventions (Typer CLI, Pydantic models, CommandResult envelope, lazy imports, api.py facade).
- Pitfalls: HIGH - Pitfalls are well-understood file I/O and CLI concerns. All have clear, tested mitigation strategies.

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain -- file I/O patterns and Typer API are mature)
