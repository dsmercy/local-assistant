import asyncio

import pytest

from src.tools.base import ToolCall
from src.tools.read_file import MAX_FILE_SIZE, ReadFileTool
from src.workspace.context import PathSafetyError, WorkspaceContext


def _tool(tmp_path):
    return ReadFileTool(WorkspaceContext(root=tmp_path))


def _call(path: str) -> ToolCall:
    return ToolCall(tool_name="read_file", arguments={"path": path})


async def test_reads_file_within_workspace(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')")
    result = await _tool(tmp_path).execute(_call("hello.py"))
    assert result.success is True
    assert "print('hello')" in result.output


async def test_raises_path_safety_error_for_dotdot(tmp_path):
    with pytest.raises(PathSafetyError):
        await _tool(tmp_path).execute(_call("../outside.py"))


async def test_raises_path_safety_error_for_null_byte(tmp_path):
    with pytest.raises(PathSafetyError):
        await _tool(tmp_path).execute(_call("file\x00.py"))


async def test_returns_error_result_when_file_not_found(tmp_path):
    result = await _tool(tmp_path).execute(_call("missing.py"))
    assert result.success is False
    assert "not found" in result.output.lower()


async def test_returns_error_result_when_file_exceeds_512kb(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * (MAX_FILE_SIZE + 1))
    result = await _tool(tmp_path).execute(_call("big.bin"))
    assert result.success is False
    assert "too large" in result.output.lower()


async def test_propagates_cancellation(tmp_path):
    (tmp_path / "file.py").write_text("content")
    tool = _tool(tmp_path)

    async def _slow(_request):
        await asyncio.sleep(10)

    task = asyncio.create_task(tool.execute(_call("file.py")))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
