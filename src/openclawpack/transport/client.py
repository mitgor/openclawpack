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
            **kwargs: Override config values for this call. Supported overrides:
                cwd, allowed_tools, permission_mode, cli_path, system_prompt,
                setting_sources, max_turns, max_budget_usd, can_use_tool, hooks.

        Returns:
            CommandResult with success status, result text, errors, session info.

        Raises:
            CLINotFound: Claude Code CLI not found on the system.
            ProcessError: Subprocess exited with non-zero code.
            TransportTimeout: Subprocess exceeded configured timeout.
            JSONDecodeError: Subprocess output contained malformed JSON.
            ConnectionError_: Connection to subprocess lost.
        """
        # Pop per-call-only kwargs before building options
        can_use_tool = kwargs.pop("can_use_tool", None)
        hooks = kwargs.pop("hooks", None)

        options = ClaudeAgentOptions(
            cwd=kwargs.get("cwd", self.config.cwd),
            allowed_tools=kwargs.get("allowed_tools", self.config.allowed_tools) or [],
            permission_mode=kwargs.get("permission_mode", self.config.permission_mode),
            cli_path=kwargs.get("cli_path", self.config.cli_path),
        )

        system_prompt = kwargs.get("system_prompt", self.config.system_prompt)
        if system_prompt is not None:
            options.system_prompt = system_prompt

        setting_sources = kwargs.get("setting_sources", self.config.setting_sources)
        if setting_sources is not None:
            options.setting_sources = setting_sources

        max_turns = kwargs.get("max_turns", self.config.max_turns)
        if max_turns is not None:
            options.max_turns = max_turns

        max_budget_usd = kwargs.get("max_budget_usd", self.config.max_budget_usd)
        if max_budget_usd is not None:
            options.max_budget_usd = max_budget_usd

        # Build sdk_query kwargs for optional per-call parameters
        query_kwargs: dict[str, Any] = {
            "prompt": prompt,
            "options": options,
        }
        if can_use_tool is not None:
            query_kwargs["can_use_tool"] = can_use_tool
        if hooks is not None:
            query_kwargs["hooks"] = hooks

        try:
            result_message: ResultMessage | None = None
            async with asyncio.timeout(self.config.timeout_seconds):
                async for message in sdk_query(**query_kwargs):
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
