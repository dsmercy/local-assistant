from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: str
    error: str | None = None


@runtime_checkable
class ToolHandler(Protocol):
    name: str
    description: str
    parameters_schema: dict[str, Any]

    async def execute(self, call: ToolCall) -> ToolResult: ...
