"""Transport configuration types.

Uses @dataclass (not Pydantic) since this is configuration, not validated data.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransportConfig:
    """Configuration for Claude Code subprocess transport.

    Attributes:
        cwd: Working directory for the subprocess. None uses the current directory.
        timeout_seconds: Maximum time to wait for subprocess completion (default 5 min).
        allowed_tools: List of tools Claude can use. None allows the SDK default.
        system_prompt: Optional system prompt override. Accepts a raw string or a
            SystemPromptPreset dict (e.g. ``{"type": "preset", "preset": "claude_code",
            "append": "..."}``) to preserve Claude Code's built-in prompt.
        cli_path: Path to the Claude CLI binary. None auto-detects.
        permission_mode: SDK permission mode (default bypasses all permission prompts).
        setting_sources: Optional list of setting sources (e.g. ``["project"]``).
        max_turns: Optional max conversation turns per invocation.
        max_budget_usd: Optional per-invocation spending limit.
    """

    cwd: str | None = None
    timeout_seconds: float = 300.0
    allowed_tools: list[str] | None = None
    system_prompt: str | dict | None = None
    cli_path: str | None = None
    permission_mode: str = "bypassPermissions"
    setting_sources: list[str] | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
