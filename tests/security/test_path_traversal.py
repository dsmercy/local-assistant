"""Security regression: path traversal, null bytes, absolute paths, disallowed commands."""
import pytest

from src.tools.base import ToolCall
from src.tools.list_files import ListFilesTool
from src.tools.read_file import ReadFileTool
from src.tools.run_command import RunCommandTool
from src.tools.search_files import SearchFilesTool
from src.tools.write_file import WriteFileTool
from src.workspace.context import PathSafetyError, WorkspaceContext

TRAVERSAL_PATHS = [
    "../../etc/passwd",
    "../outside.txt",
    "sub/../../escape.py",
]
NULL_BYTE_PATHS = [
    "file\x00.py",
    "\x00secret",
]


def _ws(tmp_path):
    return WorkspaceContext(root=tmp_path)


# ── ReadFileTool ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
async def test_read_file_rejects_traversal(tmp_path, bad_path):
    with pytest.raises(PathSafetyError):
        await ReadFileTool(_ws(tmp_path)).execute(
            ToolCall(tool_name="read_file", arguments={"path": bad_path})
        )


@pytest.mark.parametrize("bad_path", NULL_BYTE_PATHS)
async def test_read_file_rejects_null_byte(tmp_path, bad_path):
    with pytest.raises(PathSafetyError):
        await ReadFileTool(_ws(tmp_path)).execute(
            ToolCall(tool_name="read_file", arguments={"path": bad_path})
        )


# ── ListFilesTool ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
async def test_list_files_rejects_traversal(tmp_path, bad_path):
    with pytest.raises(PathSafetyError):
        await ListFilesTool(_ws(tmp_path)).execute(
            ToolCall(tool_name="list_files", arguments={"directory": bad_path})
        )


# ── SearchFilesTool ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
async def test_search_files_rejects_traversal(tmp_path, bad_path):
    with pytest.raises(PathSafetyError):
        await SearchFilesTool(_ws(tmp_path)).execute(
            ToolCall(
                tool_name="search_files",
                arguments={"pattern": "x", "directory": bad_path},
            )
        )


# ── WriteFileTool ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS + NULL_BYTE_PATHS)
async def test_write_file_rejects_unsafe_path(tmp_path, bad_path):
    with pytest.raises(PathSafetyError):
        await WriteFileTool(_ws(tmp_path)).execute(
            ToolCall(
                tool_name="write_file",
                arguments={"path": bad_path, "content": "bad"},
            )
        )


# ── RunCommandTool — disallowed executables ────────────────────────────────────


@pytest.mark.parametrize(
    "cmd",
    ["rm -rf /", "bash -c ls", "curl http://x.com", "powershell -c ls", "wget http://x.com"],
)
async def test_run_command_rejects_disallowed_executable(tmp_path, cmd):
    with pytest.raises(ValueError, match="not in the allowed list"):
        await RunCommandTool(_ws(tmp_path)).execute(
            ToolCall(tool_name="run_command", arguments={"command": cmd})
        )
