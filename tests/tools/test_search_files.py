import pytest

from src.tools.base import ToolCall
from src.tools.search_files import MAX_MATCHES, SearchFilesTool
from src.workspace.context import PathSafetyError, WorkspaceContext


def _tool(tmp_path):
    return SearchFilesTool(WorkspaceContext(root=tmp_path))


def _call(**kwargs) -> ToolCall:
    return ToolCall(tool_name="search_files", arguments=kwargs)


async def test_literal_match_returns_correct_file_and_line(tmp_path):
    (tmp_path / "code.py").write_text("def hello():\n    pass\n")
    result = await _tool(tmp_path).execute(_call(pattern="hello"))
    assert result.success is True
    assert "code.py:1" in result.output
    assert "hello" in result.output


async def test_regex_match_returns_correct_file_and_line(tmp_path):
    (tmp_path / "code.py").write_text("foo = 42\nbar = 7\n")
    result = await _tool(tmp_path).execute(_call(pattern=r"\d+", is_regex=True))
    assert result.success is True
    assert "code.py" in result.output


async def test_invalid_regex_returns_error_result(tmp_path):
    result = await _tool(tmp_path).execute(_call(pattern="[invalid", is_regex=True))
    assert result.success is False
    assert "Invalid regex" in result.output


async def test_no_matches_returns_success_with_no_matches_message(tmp_path):
    (tmp_path / "empty.py").write_text("# nothing here\n")
    result = await _tool(tmp_path).execute(_call(pattern="xyzzy_not_here"))
    assert result.success is True
    assert "No matches found" in result.output


async def test_truncates_at_200_matches_with_notice(tmp_path):
    lines = "\n".join([f"match_{i}" for i in range(MAX_MATCHES + 10)])
    (tmp_path / "big.py").write_text(lines)
    result = await _tool(tmp_path).execute(_call(pattern="match_"))
    assert result.success is True
    assert "Truncated" in result.output


async def test_raises_path_safety_error_for_outside_root(tmp_path):
    with pytest.raises(PathSafetyError):
        await _tool(tmp_path).execute(_call(pattern="x", directory="../../etc"))
