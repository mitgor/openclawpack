"""Answer injection for non-interactive GSD workflow execution.

Builds ``can_use_tool`` callbacks that intercept ``AskUserQuestion`` tool calls
and supply pre-determined answers, enabling fully non-interactive operation.

The matching strategy is:
1. Exact match -- question text is a key in the answer map.
2. Substring/fuzzy match -- any answer map key is a case-insensitive substring
   of the question text.
3. Fallback -- select the first option's label (for multiple-choice), or empty
   string (for free-text).

IMPORTANT: ``PermissionResultAllow`` is imported lazily inside the callback
to preserve CLI independence (PKG-04). This module can be imported without
the SDK installed.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


def build_answer_callback(
    answer_map: dict[str, str],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Create a ``can_use_tool`` callback that injects answers for AskUserQuestion.

    Args:
        answer_map: Mapping of question text (or substring) to answer value.
            For multiple-choice questions, the value should be the option label.
            For multi-select, join labels with ``", "``.
            For free-text, use the desired text directly.

    Returns:
        An async callable suitable for the ``can_use_tool`` parameter of
        ``sdk_query()``.
    """

    async def can_use_tool(
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
    ) -> Any:
        # Lazy import to avoid SDK dependency at module level
        from claude_agent_sdk import PermissionResultAllow

        if tool_name != "AskUserQuestion":
            return PermissionResultAllow()

        questions = tool_input.get("questions", [])
        answers: dict[str, str] = {}

        for q in questions:
            question_text: str = q.get("question", "")
            matched = False

            # 1. Exact match
            if question_text in answer_map:
                answers[question_text] = answer_map[question_text]
                matched = True
            else:
                # 2. Substring/fuzzy match (case-insensitive)
                question_lower = question_text.lower()
                for key, value in answer_map.items():
                    if key.lower() in question_lower:
                        answers[question_text] = value
                        matched = True
                        break

            if not matched:
                # 3. Fallback: first option label or empty string
                options = q.get("options", [])
                if options:
                    fallback = options[0].get("label", "")
                    answers[question_text] = fallback
                    logger.warning(
                        "Unmatched question, using first option fallback: "
                        "%r -> %r",
                        question_text,
                        fallback,
                    )
                else:
                    answers[question_text] = ""
                    logger.warning(
                        "Unmatched question with no options, using empty string: %r",
                        question_text,
                    )

        return PermissionResultAllow(
            updated_input={"questions": questions, "answers": answers}
        )

    return can_use_tool


def build_noop_pretool_hook() -> Callable[..., Coroutine[Any, Any, dict]]:
    """Create a no-op PreToolUse hook matching the SDK ``HookCallback`` signature.

    The Python SDK requires a ``PreToolUse`` hook to be registered for the
    ``can_use_tool`` callback to be invoked. The hook callback signature is
    ``(HookInput, str | None, HookContext) -> Awaitable[HookJSONOutput]``.

    Uses ``Any`` for parameter types to avoid importing SDK types directly,
    preserving PKG-04 lazy import compatibility.

    Returns:
        An async callable with the 3-parameter SDK ``HookCallback`` signature.
    """

    async def pre_tool_use(
        input: Any,  # HookInput  # noqa: A002
        tool_use_id: Any,  # str | None
        context: Any,  # HookContext
    ) -> dict:
        """No-op hook -- allow all tool use."""
        return {}  # empty SyncHookJSONOutput = proceed normally

    return pre_tool_use


def build_hooks_dict() -> dict[str, list]:
    """Build hooks dict in SDK-expected format.

    Returns a ``{HookEvent: [HookMatcher(hooks=[callback])]}`` structure
    that the SDK expects. Lazy-imports ``HookMatcher`` from the SDK.

    Returns:
        Dict mapping ``"PreToolUse"`` to a list containing one ``HookMatcher``.
    """
    from claude_agent_sdk import HookMatcher

    return {"PreToolUse": [HookMatcher(hooks=[build_noop_pretool_hook()])]}
