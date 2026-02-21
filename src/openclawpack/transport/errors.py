"""Typed exception hierarchy for transport failures.

Each exception maps to a specific failure mode, enabling callers to catch
and handle distinct scenarios independently. All transport exceptions inherit
from TransportError, which can be used as a catch-all.

SDK exception mapping:
    CLINotFoundError   -> CLINotFound
    ProcessError       -> ProcessError
    CLIJSONDecodeError -> JSONDecodeError
    CLIConnectionError -> ConnectionError_
    TimeoutError       -> TransportTimeout
"""

from __future__ import annotations


class TransportError(Exception):
    """Base exception for all transport failures.

    Catch this to handle any transport-related error generically.
    """

    def __init__(self, message: str = "Transport operation failed") -> None:
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class CLINotFound(TransportError):
    """Raised when the Claude Code CLI is not found on the system.

    Maps from SDK's CLINotFoundError.
    """

    def __init__(
        self,
        message: str = (
            "Claude Code CLI not found. "
            "Install with: npm install -g @anthropic-ai/claude-code"
        ),
    ) -> None:
        super().__init__(message)


class ProcessError(TransportError):
    """Raised when the subprocess exits with a non-zero code.

    Maps from SDK's ProcessError.
    """

    def __init__(
        self,
        message: str = "Claude Code subprocess failed",
        *,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.exit_code is not None:
            parts.append(f"exit_code={self.exit_code}")
        if self.stderr:
            parts.append(f"stderr={self.stderr!r}")
        return " | ".join(parts)


class TransportTimeout(TransportError):
    """Raised when the subprocess exceeds the configured timeout.

    Maps from Python's TimeoutError / asyncio.TimeoutError.
    """

    def __init__(
        self,
        message: str = "Claude Code subprocess timed out",
        *,
        timeout_seconds: float = 0.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message)

    def __str__(self) -> str:
        if self.timeout_seconds > 0:
            return f"{self.message} | timeout_seconds={self.timeout_seconds}"
        return self.message


class JSONDecodeError(TransportError):
    """Raised when subprocess output contains malformed JSON.

    Maps from SDK's CLIJSONDecodeError.
    """

    def __init__(
        self,
        message: str = "Failed to decode JSON from Claude Code output",
        *,
        raw_output: str | None = None,
    ) -> None:
        self.raw_output = raw_output
        super().__init__(message)

    def __str__(self) -> str:
        if self.raw_output is not None:
            # Truncate long raw output for readability
            preview = self.raw_output[:200]
            if len(self.raw_output) > 200:
                preview += "..."
            return f"{self.message} | raw_output={preview!r}"
        return self.message


class ConnectionError_(TransportError):
    """Raised when the connection to the subprocess is lost.

    Maps from SDK's CLIConnectionError. Trailing underscore avoids
    shadowing the builtin ConnectionError.
    """

    def __init__(
        self,
        message: str = "Connection to Claude Code subprocess lost",
    ) -> None:
        super().__init__(message)
