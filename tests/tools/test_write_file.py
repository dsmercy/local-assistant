from unittest.mock import AsyncMock, patch

import pytest

from src.tools.base import ToolCall
from src.tools.write_file import WriteFileTool
from src.workspace.context import PathSafetyError, WorkspaceContext


def _tool(tmp_path):
    return WriteFileTool(WorkspaceContext(root=tmp_path))


def _call(**kwargs) -> ToolCall:
    return ToolCall(tool_name="write_file", arguments=kwargs)


async def test_full_file_write_matches_content_exactly(tmp_path):
    result = await _tool(tmp_path).execute(_call(path="new.py", content="print('hi')\n"))
    assert result.success is True
    assert (tmp_path / "new.py").read_text() == "print('hi')\n"


async def test_line_range_patch_replaces_only_targeted_lines(tmp_path):
    (tmp_path / "file.py").write_text("line1\nline2\nline3\n")
    result = await _tool(tmp_path).execute(
        _call(path="file.py", content="REPLACED\n", line_range="2-2")
    )
    assert result.success is True
    assert (tmp_path / "file.py").read_text() == "line1\nREPLACED\nline3\n"


async def test_out_of_bounds_range_returns_error_result(tmp_path):
    (tmp_path / "file.py").write_text("only one line\n")
    result = await _tool(tmp_path).execute(
        _call(path="file.py", content="x", line_range="5-10")
    )
    assert result.success is False
    assert "out of bounds" in result.output.lower()


async def test_raises_path_safety_error_for_outside_root(tmp_path):
    with pytest.raises(PathSafetyError):
        await _tool(tmp_path).execute(_call(path="../escape.py", content="bad"))


async def test_missing_parent_directory_returns_error_result(tmp_path):
    result = await _tool(tmp_path).execute(
        _call(path="nonexistent/sub/file.py", content="x")
    )
    assert result.success is False
    assert "does not exist" in result.output.lower()


async def test_atomic_write_leaves_no_partial_file_on_failure(tmp_path):
    original = tmp_path / "orig.py"
    original.write_text("original content")

    tool = _tool(tmp_path)

    mock_fh = AsyncMock()
    mock_fh.write = AsyncMock(side_effect=OSError("simulated disk error"))
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_fh)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("src.tools.write_file.aiofiles.open", return_value=mock_ctx):
        with pytest.raises(OSError):
            await tool.execute(_call(path="orig.py", content="new content"))

    assert original.read_text() == "original content"
    assert not (tmp_path / "orig.py.tmp").exists()
