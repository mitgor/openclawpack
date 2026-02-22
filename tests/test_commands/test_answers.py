"""Tests for the answer injection callback builder.

Tests use unittest.mock to mock the lazy import of PermissionResultAllow
inside the callback, avoiding a hard dependency on claude_agent_sdk for
unit tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ─────────────────────────────────────────────────────


class FakePermissionResultAllow:
    """Minimal stand-in for PermissionResultAllow."""

    def __init__(self, updated_input: dict | None = None):
        self.updated_input = updated_input


@pytest.fixture()
def _mock_sdk(monkeypatch):
    """Patch claude_agent_sdk.PermissionResultAllow for all tests in this module."""
    mock_module = MagicMock()
    mock_module.PermissionResultAllow = FakePermissionResultAllow
    monkeypatch.setitem(
        __import__("sys").modules, "claude_agent_sdk", mock_module
    )


# ── build_answer_callback tests ──────────────────────────────────


@pytest.mark.usefixtures("_mock_sdk")
class TestBuildAnswerCallback:
    """Test the can_use_tool callback created by build_answer_callback."""

    @pytest.mark.anyio
    async def test_exact_match(self) -> None:
        """Exact key match returns mapped value."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({"What depth level?": "3"})
        tool_input = {
            "questions": [
                {"question": "What depth level?", "options": [{"label": "1"}, {"label": "3"}]}
            ]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        assert isinstance(result, FakePermissionResultAllow)
        assert result.updated_input["answers"]["What depth level?"] == "3"

    @pytest.mark.anyio
    async def test_substring_match_case_insensitive(self) -> None:
        """Substring key match is case-insensitive."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({"depth": "5"})
        tool_input = {
            "questions": [
                {"question": "What Depth level do you prefer?", "options": []}
            ]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        assert result.updated_input["answers"]["What Depth level do you prefer?"] == "5"

    @pytest.mark.anyio
    async def test_fallback_to_first_option(self) -> None:
        """When no match found, selects first option label."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({})
        tool_input = {
            "questions": [
                {
                    "question": "Unknown question?",
                    "options": [{"label": "Alpha"}, {"label": "Beta"}],
                }
            ]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        assert result.updated_input["answers"]["Unknown question?"] == "Alpha"

    @pytest.mark.anyio
    async def test_fallback_empty_string_no_options(self) -> None:
        """When no match and no options, uses empty string."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({})
        tool_input = {
            "questions": [{"question": "Free text?"}]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        assert result.updated_input["answers"]["Free text?"] == ""

    @pytest.mark.anyio
    async def test_non_ask_tool_passes_through(self) -> None:
        """Non-AskUserQuestion tools get a plain PermissionResultAllow."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({"irrelevant": "value"})

        result = await callback("Read", {"file_path": "/tmp/x"}, None)
        assert isinstance(result, FakePermissionResultAllow)
        assert result.updated_input is None

    @pytest.mark.anyio
    async def test_multiple_questions(self) -> None:
        """Multiple questions are each resolved independently."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({
            "depth": "3",
            "parallelization": "Yes",
        })
        tool_input = {
            "questions": [
                {"question": "Choose depth level", "options": []},
                {"question": "Enable parallelization?", "options": [{"label": "Yes"}, {"label": "No"}]},
            ]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        answers = result.updated_input["answers"]
        assert answers["Choose depth level"] == "3"
        assert answers["Enable parallelization?"] == "Yes"

    @pytest.mark.anyio
    async def test_exact_match_takes_precedence(self) -> None:
        """Exact match wins over substring match."""
        from openclawpack.commands.answers import build_answer_callback

        callback = build_answer_callback({
            "depth": "substring-val",
            "What depth level?": "exact-val",
        })
        tool_input = {
            "questions": [{"question": "What depth level?", "options": []}]
        }

        result = await callback("AskUserQuestion", tool_input, None)
        assert result.updated_input["answers"]["What depth level?"] == "exact-val"


# ── build_noop_pretool_hook tests ────────────────────────────────


class TestBuildNoopPretoolHook:
    """Test that build_noop_pretool_hook returns a valid async callable."""

    def test_returns_callable(self) -> None:
        from openclawpack.commands.answers import build_noop_pretool_hook

        hook = build_noop_pretool_hook()
        assert callable(hook)

    @pytest.mark.anyio
    async def test_hook_is_async_noop(self) -> None:
        """Hook completes without error and returns None."""
        from openclawpack.commands.answers import build_noop_pretool_hook

        hook = build_noop_pretool_hook()
        result = await hook(None, None)
        assert result is None

    def test_each_call_returns_new_instance(self) -> None:
        """Each call creates a distinct function object."""
        from openclawpack.commands.answers import build_noop_pretool_hook

        hook1 = build_noop_pretool_hook()
        hook2 = build_noop_pretool_hook()
        assert hook1 is not hook2
