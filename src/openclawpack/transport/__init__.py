"""Transport layer for Claude Code subprocess communication.

Provides a stable adapter interface wrapping claude-agent-sdk behind
openclawpack's own types (CommandResult, typed exceptions).

ClaudeTransport is lazily imported to avoid loading claude-agent-sdk at
module import time. This ensures --version and --help work without the SDK.

Direct imports (no SDK dependency):
    TransportConfig, TransportError, CLINotFound, ProcessError,
    TransportTimeout, JSONDecodeError, ConnectionError_

Lazy imports (triggers SDK load):
    ClaudeTransport
"""

from openclawpack.transport.errors import (
    CLINotFound,
    ConnectionError_,
    JSONDecodeError,
    ProcessError,
    TransportError,
    TransportTimeout,
)
from openclawpack.transport.types import TransportConfig

__all__ = [
    "ClaudeTransport",
    "TransportConfig",
    "TransportError",
    "CLINotFound",
    "ProcessError",
    "TransportTimeout",
    "JSONDecodeError",
    "ConnectionError_",
]


def __getattr__(name: str):
    if name == "ClaudeTransport":
        from openclawpack.transport.client import ClaudeTransport

        return ClaudeTransport
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
