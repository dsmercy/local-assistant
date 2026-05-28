import pytest

from src.workspace.context import PathSafetyError, WorkspaceContext, WorkspaceNotFoundError


def _ws(tmp_path):
    return WorkspaceContext(root=tmp_path)


def test_is_path_safe_returns_true_for_valid_path(tmp_path):
    ws = _ws(tmp_path)
    (tmp_path / "src").mkdir()
    assert ws.is_path_safe("src/main.py") is True


def test_is_path_safe_returns_false_for_dotdot_traversal(tmp_path):
    ws = _ws(tmp_path)
    assert ws.is_path_safe("../etc/passwd") is False


def test_is_path_safe_returns_false_for_null_byte(tmp_path):
    ws = _ws(tmp_path)
    assert ws.is_path_safe("file\x00.py") is False


def test_is_path_safe_returns_false_for_out_of_root_path(tmp_path):
    ws = _ws(tmp_path)
    outside = str(tmp_path.parent / "other" / "file.py")
    assert ws.is_path_safe(outside) is False


def test_assert_path_safe_raises_for_dotdot(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(PathSafetyError):
        ws.assert_path_safe("../../etc/passwd")


def test_raises_workspace_not_found_when_no_project_file(tmp_path):
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(isolated)
        with pytest.raises(WorkspaceNotFoundError):
            WorkspaceContext()
    finally:
        os.chdir(original_cwd)
