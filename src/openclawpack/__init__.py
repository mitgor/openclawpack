"""OpenClawPack: AI agent control over the GSD framework via Claude Code.

Public API (lazy-loaded to preserve PKG-04 -- ``openclawpack --version``
works without Claude Code installed):

    from openclawpack import create_project, plan_phase, execute_phase, get_status
    from openclawpack import add_project, list_projects, remove_project
    from openclawpack import EventBus, EventType, Event
"""

from openclawpack._version import __version__

__all__ = [
    "__version__",
    "create_project",
    "plan_phase",
    "execute_phase",
    "get_status",
    "add_project",
    "list_projects",
    "remove_project",
    "EventBus",
    "EventType",
    "Event",
]


def __getattr__(name: str):
    _api_names = {
        "create_project",
        "plan_phase",
        "execute_phase",
        "get_status",
        "add_project",
        "list_projects",
        "remove_project",
    }
    if name in _api_names:
        from openclawpack import api

        return getattr(api, name)

    _event_names = {"EventBus", "EventType", "Event"}
    if name in _event_names:
        from openclawpack import events

        return getattr(events, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
