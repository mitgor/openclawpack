# OpenClawPack

AI agent control over the [GSD](https://github.com/gsd-build/get-shit-done) framework through a CLI and Python library. Translates non-interactive commands into Claude Code subprocess calls that execute GSD skills, returning structured JSON output for fully autonomous project lifecycle management.

An AI agent can go from "build me a todo app" to a fully planned GSD project with roadmap, without any human interaction.

## Install

```bash
pip install openclawpack
```

Requires Python 3.10+ and [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated.

## CLI

```bash
# Create a project from an idea
openclawpack new-project -i "Build a REST API for task management"

# Plan and execute phases
openclawpack plan-phase 1
openclawpack execute-phase 1

# Check progress
openclawpack status

# Multi-project management
openclawpack projects add /path/to/project --name myproject
openclawpack projects list
openclawpack projects remove myproject
```

All commands output structured JSON by default. Use `--output-format text` for human-readable output.

### Options

| Flag | Description |
|------|-------------|
| `--output-format json\|text` | Output format (default: json) |
| `--project-dir PATH` | Project directory (default: cwd) |
| `--verbose` | Show subprocess output |
| `--quiet` | Suppress non-JSON output |
| `--timeout SECONDS` | Subprocess timeout |
| `--resume SESSION_ID` | Resume a previous session |

## Python Library

```python
from openclawpack import create_project, plan_phase, execute_phase, get_status
from openclawpack import EventBus, EventType

# Create event bus for lifecycle hooks
bus = EventBus()
bus.on(EventType.PHASE_COMPLETE, lambda e: print(f"Phase done: {e.data}"))
bus.on(EventType.ERROR, lambda e: print(f"Error: {e.data}"))

# Run GSD workflow
result = await create_project(
    idea="Build a REST API for task management",
    event_bus=bus,
)

result = await plan_phase(1, event_bus=bus)
result = await execute_phase(1, event_bus=bus)
status = await get_status()
```

### API Functions

| Function | Description |
|----------|-------------|
| `create_project(idea, ...)` | Create a new GSD project from an idea |
| `plan_phase(phase, ...)` | Plan a specific phase |
| `execute_phase(phase, ...)` | Execute a planned phase |
| `get_status(...)` | Get project state as structured data |
| `add_project(path, name)` | Register a project in the registry |
| `list_projects()` | List registered projects |
| `remove_project(name)` | Remove a project from the registry |

All functions are async and return a `CommandResult`:

```json
{
  "success": true,
  "result": { ... },
  "errors": [],
  "session_id": "abc-123",
  "usage": { "input_tokens": 1000, "output_tokens": 500, "total_cost_usd": 0.01 },
  "duration_ms": 5000
}
```

### Event Types

| Event | Fires when |
|-------|------------|
| `PHASE_COMPLETE` | A phase finishes execution |
| `PLAN_COMPLETE` | A phase plan is created |
| `ERROR` | An error occurs during execution |
| `DECISION_NEEDED` | Agent needs human input (no answer overrides) |
| `PROGRESS_UPDATE` | Progress changes during execution |

## OpenClaw Plugin

The repo includes an [OpenClaw](https://docs.openclaw.ai) plugin at `openclawpack-plugin/` that forces agents to evaluate task complexity and route medium/hard tasks through GSD.

```bash
# Install plugin
openclaw plugins install -l ./openclawpack-plugin
```

The plugin:
- Injects a task evaluation rubric into the agent's system prompt
- Classifies tasks as **simple** (do directly), **medium** (GSD single-phase), or **hard** (GSD multi-phase)
- Exposes 4 tools: `gsd_new_project`, `gsd_plan_phase`, `gsd_execute_phase`, `gsd_status`

See `openclawpack-plugin/` for configuration options.

## Architecture

```
CLI (Typer) -> API facade (async) -> Workflow engine -> Transport (Claude Agent SDK) -> Claude Code subprocess
```

- **Transport**: Claude Agent SDK adapter with retry, exponential backoff, session resume
- **Output**: Pydantic-validated `CommandResult` schema with usage/cost tracking
- **Events**: EventBus with sync/async handlers (library) and JSON-to-stderr (CLI)
- **State**: `.planning/` file parser with Pydantic models
- **Registry**: Multi-project atomic JSON persistence

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run plugin tests
cd openclawpack-plugin && npm test
```

## License

MIT
