import pytest

from src.tools.base import ToolCall, ToolHandler, ToolResult
from src.tools.registry import ToolDepthExceededError, ToolNotFoundException, ToolRegistry


class _StubTool:
    name = "stub"
    description = "A stub tool for testing."
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(success=True, output="ok")


def test_resolve_returns_handler_for_known_tool():
    registry = ToolRegistry([_StubTool()])
    handler = registry.resolve("stub")
    assert isinstance(handler, ToolHandler)
    assert handler.name == "stub"


def test_resolve_raises_for_unknown_tool():
    registry = ToolRegistry([_StubTool()])
    with pytest.raises(ToolNotFoundException):
        registry.resolve("nonexistent")


def test_depth_exceeded_raises_after_limit():
    registry = ToolRegistry([_StubTool()], max_depth=3)
    registry.increment_depth()
    registry.increment_depth()
    registry.increment_depth()
    with pytest.raises(ToolDepthExceededError):
        registry.increment_depth()


def test_reset_depth_allows_reuse():
    registry = ToolRegistry([_StubTool()], max_depth=2)
    registry.increment_depth()
    registry.increment_depth()
    registry.reset_depth()
    registry.increment_depth()  # should not raise


def test_definitions_returns_tool_definitions():
    registry = ToolRegistry([_StubTool()])
    defs = registry.definitions
    assert len(defs) == 1
    assert defs[0].name == "stub"
