"""Standard output envelope for all openclawpack operations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    """Standard output envelope for all openclawpack operations.

    Every command returns this structure, ensuring consistent JSON output
    with {success, result, errors, session_id, usage, duration_ms}.
    """

    success: bool
    result: Any = None
    errors: list[str] = Field(default_factory=list)
    session_id: str | None = None
    usage: dict[str, Any] | None = None
    duration_ms: int = 0

    def to_json(self) -> str:
        """Serialize to indented JSON string."""
        return self.model_dump_json(indent=2)

    @classmethod
    def error(cls, message: str, duration_ms: int = 0) -> CommandResult:
        """Create an error result."""
        return cls(
            success=False,
            errors=[message],
            duration_ms=duration_ms,
        )

    @classmethod
    def ok(
        cls,
        result: Any,
        session_id: str | None = None,
        usage: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> CommandResult:
        """Create a success result."""
        return cls(
            success=True,
            result=result,
            session_id=session_id,
            usage=usage,
            duration_ms=duration_ms,
        )
