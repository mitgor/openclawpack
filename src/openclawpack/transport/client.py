"""ClaudeTransport adapter wrapping claude-agent-sdk.

This is the ONLY module in the codebase that imports from claude_agent_sdk
directly. All other code communicates with Claude Code through this adapter,
isolating the SDK's v0.1.x API from the rest of openclawpack.
"""

from __future__ import annotations

import asyncio
from typing import Any

import anyio

from claude_agent_sdk import (
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ClaudeAgentOptions,
    ResultMessage,
)
from claude_agent_sdk import ProcessError as SDKProcessError
from claude_agent_sdk import query as sdk_query

from openclawpack.output.schema import CommandResult
from openclawpack.transport.errors import (
    CLINotFound,
    ConnectionError_,
    JSONDecodeError,
    ProcessError,
    TransportTimeout,
)
from openclawpack.transport.types import TransportConfig


class ClaudeTransport:
    """Adapter wrapping claude-agent-sdk for openclawpack.

    Provides a stable interface that translates SDK messages and exceptions
    into openclawpack's own types (CommandResult, typed errors).

    Usage::

        transport = ClaudeTransport(TransportConfig(timeout_seconds=60))
        result = await transport.run("List all Python files")
        print(result.success, result.result)

    Or synchronously::

        result = transport.run_sync("List all Python files")
    """

    def __init__(self, config: TransportConfig | None = None) -> None:
        self.config = config or TransportConfig()

    async def run(self, prompt: str, **kwargs: Any) -> CommandResult:
        """Execute a prompt via Claude Code and return a structured result.

        Args:
            prompt: The prompt to send to Claude Code.
            **kwargs: Override config values for this call (cwd, allowed_tools, etc).

        Returns:
            CommandResult with success status, result text, errors, session info.

        Raises:
            CLINotFound: Claude Code CLI not found on the system.
            ProcessError: Subprocess exited with non-zero code.
            TransportTimeout: Subprocess exceeded configured timeout.
            JSONDecodeError: Subprocess output contained malformed JSON.
            ConnectionError_: Connection to subprocess lost.
        """
        options = ClaudeAgentOptions(
            cwd=kwargs.get("cwd", self.config.cwd),
            allowed_tools=kwargs.get("allowed_tools", self.config.allowed_tools) or [],
            permission_mode=kwargs.get("permission_mode", self.config.permission_mode),
            cli_path=kwargs.get("cli_path", self.config.cli_path),
        )

        system_prompt = kwargs.get("system_prompt", self.config.system_prompt)
        if system_prompt is not None:
            options.system_prompt = system_prompt

        try:
            result_message: ResultMessage | None = None
            async with asyncio.timeout(self.config.timeout_seconds):
                async for message in sdk_query(prompt=prompt, options=options):
                    if isinstance(message, ResultMessage):
                        result_message = message

            if result_message is None:
                raise ProcessError(
                    "No result message received from Claude Code"
                )

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
            raise ProcessError(
                str(e),
                exit_code=e.exit_code,
                stderr=e.stderr,
            ) from e
        except CLIJSONDecodeError as e:
            raise JSONDecodeError(
                str(e),
                raw_output=e.line if hasattr(e, "line") else None,
            ) from e
        except CLIConnectionError as e:
            raise ConnectionError_(str(e)) from e
        except TimeoutError:
            raise TransportTimeout(
                f"Claude Code subprocess timed out after {self.config.timeout_seconds}s",
                timeout_seconds=self.config.timeout_seconds,
            )

    def run_sync(self, prompt: str, **kwargs: Any) -> CommandResult:
        """Synchronous wrapper for run().

        Uses anyio.run() to bridge sync-to-async, suitable for CLI commands.

        Args:
            prompt: The prompt to send to Claude Code.
            **kwargs: Override config values for this call.

        Returns:
            CommandResult with success status, result text, errors, session info.
        """
        return anyio.from_thread.run(self.run, prompt, **kwargs)
