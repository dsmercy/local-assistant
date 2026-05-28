import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.base import ToolCall
from src.tools.run_command import RunCommandTool
from src.workspace.context import WorkspaceContext


def _tool(tmp_path, timeout: float = 60.0):
    return RunCommandTool(WorkspaceContext(root=tmp_path), timeout=timeout)


def _call(**kwargs) -> ToolCall:
    return ToolCall(tool_name="run_command", arguments=kwargs)


def _mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


async def test_allowed_command_returns_success_on_exit_0(tmp_path):
    proc = _mock_proc(returncode=0, stdout=b"pytest 8.2.0\n")
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await _tool(tmp_path).execute(_call(command="pytest --version"))
    assert result.success is True
    assert "pytest" in result.output


async def test_allowed_command_returns_failure_with_stderr_on_exit_1(tmp_path):
    proc = _mock_proc(returncode=1, stdout=b"", stderr=b"error: bad args\n")
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await _tool(tmp_path).execute(_call(command="pytest bad_test.py"))
    assert result.success is False
    assert "error: bad args" in result.output


@pytest.mark.parametrize("cmd", ["rm -rf /", "bash -c ls", "curl http://example.com"])
async def test_disallowed_executable_raises_value_error_immediately(tmp_path, cmd):
    with pytest.raises(ValueError, match="not in the allowed list"):
        await _tool(tmp_path).execute(_call(command=cmd))


@pytest.mark.parametrize("cmd", ["git status", "wget http://example.com", "powershell -c ls"])
async def test_unknown_subcommand_raises_value_error(tmp_path, cmd):
    with pytest.raises(ValueError, match="not in the allowed list"):
        await _tool(tmp_path).execute(_call(command=cmd))


async def test_timeout_returns_error_result(tmp_path):
    calls = 0

    async def _slow_communicate():
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(10)
        return b"", b""

    proc = MagicMock()
    proc.kill = MagicMock()
    proc.communicate = _slow_communicate

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await _tool(tmp_path, timeout=0.01).execute(_call(command="pytest"))

    assert result.success is False
    assert "timed out" in result.output.lower()


async def test_propagates_cancellation(tmp_path):
    async def _never_returns():
        await asyncio.sleep(10)
        return b"", b""

    proc = MagicMock()
    proc.kill = MagicMock()
    proc.communicate = _never_returns

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        task = asyncio.create_task(_tool(tmp_path).execute(_call(command="pytest")))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
