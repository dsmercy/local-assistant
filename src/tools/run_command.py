import asyncio
from typing import Any

import structlog

from src.tools.base import ToolCall, ToolResult
from src.workspace.context import WorkspaceContext

logger = structlog.get_logger(__name__)

ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "pytest", "ruff", "mypy", "black", "pip",
    "dotnet", "npm", "npx", "node", "tsc", "vitest", "eslint",
})

DEFAULT_TIMEOUT: float = 60.0


class RunCommandTool:
    name = "run_command"
    description = "Run an allowed command in the workspace directory."
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command and arguments to execute"},
            "timeout": {
                "type": "number",
                "description": f"Timeout in seconds (default {DEFAULT_TIMEOUT:.0f})",
            },
        },
        "required": ["command"],
    }

    def __init__(self, workspace: WorkspaceContext, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._workspace = workspace
        self._default_timeout = timeout

    async def execute(self, call: ToolCall) -> ToolResult:
        command: str = call.arguments["command"]
        timeout: float = float(call.arguments.get("timeout", self._default_timeout))

        parts = command.split()
        if not parts:
            raise ValueError("Command must not be empty.")

        executable = parts[0]
        if executable not in ALLOWED_COMMANDS:
            raise ValueError(
                f"Command '{executable}' is not in the allowed list. "
                f"Allowed: {sorted(ALLOWED_COMMANDS)}"
            )

        logger.debug("run_command", executable=executable)

        try:
            proc = await asyncio.create_subprocess_exec(
                *parts,
                cwd=self._workspace.root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except TimeoutError:
                proc.kill()
                await proc.communicate()
                return ToolResult(
                    success=False,
                    output=f"Command timed out after {timeout:.0f}s: {command}",
                    error="timeout",
                )
        except asyncio.CancelledError:
            raise

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        success = proc.returncode == 0

        if success:
            return ToolResult(success=True, output=stdout)

        combined = "\n".join(filter(None, [stdout, stderr])).strip()
        return ToolResult(success=False, output=combined, error=f"exit_{proc.returncode}")
