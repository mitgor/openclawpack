"""Workflow engine translating high-level commands into GSD skill invocations.

The engine constructs the correct prompt string, system_prompt preset,
setting_sources, answer callback, and hooks for each GSD command type,
then invokes ``ClaudeTransport.run()``.
"""

from __future__ import annotations

import os
from typing import Any

import anyio

from openclawpack.commands import DEFAULT_TIMEOUTS
from openclawpack.output.schema import CommandResult


class WorkflowEngine:
    """Translates command parameters into GSD skill invocations.

    Usage::

        engine = WorkflowEngine(project_dir="/my/project", verbose=True)
        result = await engine.run_gsd_command(
            "gsd:new-project",
            prompt_args="--auto",
            answer_map={"depth": "3"},
        )

    Args:
        project_dir: Working directory for the Claude subprocess.
            Defaults to ``os.getcwd()`` when None.
        verbose: Whether to show detailed subprocess output.
        quiet: Whether to suppress all non-JSON output.
        timeout: Optional global timeout override (seconds).
    """

    def __init__(
        self,
        project_dir: str | None = None,
        verbose: bool = False,
        quiet: bool = False,
        timeout: float | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.verbose = verbose
        self.quiet = quiet
        self.timeout = timeout

    async def run_gsd_command(
        self,
        command: str,
        prompt_args: str = "",
        answer_map: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> CommandResult:
        """Execute a GSD command via Claude Code transport.

        Args:
            command: The GSD command name (e.g. ``"gsd:new-project"``).
            prompt_args: Additional arguments appended to the prompt
                (e.g. ``"--auto"``).
            answer_map: Optional mapping of question text to pre-determined
                answers for AskUserQuestion interception.
            prompt_override: If provided, used as the full prompt instead of
                constructing from command + prompt_args.

        Returns:
            A :class:`CommandResult` with the operation outcome.
        """
        # Lazy imports to avoid SDK dependency at module level
        from openclawpack.commands.answers import (
            build_answer_callback,
            build_noop_pretool_hook,
        )
        from openclawpack.transport.client import ClaudeTransport
        from openclawpack.transport.types import TransportConfig

        # 1. Construct prompt
        if prompt_override is not None:
            prompt = prompt_override
        else:
            prompt = f"/{command}"
            if prompt_args:
                prompt = f"{prompt} {prompt_args}"

        # 2. Determine timeout
        effective_timeout = self.timeout or DEFAULT_TIMEOUTS.get(command, 600)

        # 3. Build transport config
        config = TransportConfig(
            cwd=self.project_dir or os.getcwd(),
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": (
                    "Execute the following command non-interactively. "
                    "Do not ask unnecessary clarifying questions."
                ),
            },
            setting_sources=["project"],
            timeout_seconds=effective_timeout,
        )

        # 4. Build answer callback and hooks if answer_map provided
        run_kwargs: dict[str, Any] = {}
        if answer_map is not None:
            run_kwargs["can_use_tool"] = build_answer_callback(answer_map)
            run_kwargs["hooks"] = {"PreToolUse": build_noop_pretool_hook()}

        # 5. Create transport and run
        transport = ClaudeTransport(config)
        return await transport.run(prompt, **run_kwargs)

    def run_gsd_command_sync(
        self,
        command: str,
        prompt_args: str = "",
        answer_map: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> CommandResult:
        """Synchronous wrapper for :meth:`run_gsd_command`.

        Uses ``anyio.from_thread.run()`` to bridge sync-to-async.

        Args:
            command: The GSD command name.
            prompt_args: Additional prompt arguments.
            answer_map: Optional answer injection map.
            prompt_override: Optional full prompt override.

        Returns:
            A :class:`CommandResult` with the operation outcome.
        """
        return anyio.from_thread.run(
            self.run_gsd_command,
            command,
            prompt_args,
            answer_map,
            prompt_override,
        )
