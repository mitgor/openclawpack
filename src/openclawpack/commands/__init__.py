"""Command infrastructure for GSD workflow orchestration.

Provides the workflow engine, answer injection callbacks, and shared
utilities used by individual command modules (new_project, plan_phase,
execute_phase, status).

Direct imports (no SDK dependency):
    DEFAULT_TIMEOUTS

Lazy imports (trigger SDK-dependent modules):
    WorkflowEngine, build_answer_callback, build_noop_pretool_hook
"""

DEFAULT_TIMEOUTS: dict[str, float] = {
    "gsd:new-project": 900,
    "gsd:plan-phase": 600,
    "gsd:execute-phase": 1200,
}

__all__ = [
    "DEFAULT_TIMEOUTS",
    "WorkflowEngine",
    "build_answer_callback",
    "build_noop_pretool_hook",
]


def __getattr__(name: str):
    if name == "WorkflowEngine":
        from openclawpack.commands.engine import WorkflowEngine

        return WorkflowEngine
    if name in ("build_answer_callback", "build_noop_pretool_hook"):
        from openclawpack.commands import answers

        return getattr(answers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
