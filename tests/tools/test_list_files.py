import pytest

from src.tools.base import ToolCall
from src.tools.list_files import MAX_RESULTS, ListFilesTool
from src.workspace.context import PathSafetyError, WorkspaceContext


def _tool(tmp_path):
    return ListFilesTool(WorkspaceContext(root=tmp_path))


def _call(**kwargs) -> ToolCall:
    return ToolCall(tool_name="list_files", arguments=kwargs)


async def test_lists_files_in_valid_directory(tmp_path):
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")
    result = await _tool(tmp_path).execute(_call())
    assert result.success is True
    assert "a.py" in result.output
    assert "b.py" in result.output


async def test_raises_path_safety_error_for_directory_outside_root(tmp_path):
    with pytest.raises(PathSafetyError):
        await _tool(tmp_path).execute(_call(directory="../../etc"))


async def test_truncates_at_500_files_with_notice(tmp_path):
    for i in range(MAX_RESULTS + 5):
        (tmp_path / f"f{i}.txt").write_text("x")
    result = await _tool(tmp_path).execute(_call())
    assert result.success is True
    assert "Truncated" in result.output


async def test_excludes_pycache_and_venv_always(tmp_path):
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "mod.pyc").write_bytes(b"")
    (tmp_path / "real.py").write_text("x")
    result = await _tool(tmp_path).execute(_call())
    assert "__pycache__" not in result.output
    assert "real.py" in result.output


async def test_respects_gitignore_patterns(tmp_path):
    (tmp_path / ".gitignore").write_text("secret.txt\n")
    (tmp_path / "secret.txt").write_text("hidden")
    (tmp_path / "visible.py").write_text("shown")
    result = await _tool(tmp_path).execute(_call())
    assert "secret.txt" not in result.output
    assert "visible.py" in result.output
