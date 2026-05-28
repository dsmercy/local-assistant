from typing import Any

import aiofiles
import structlog

from src.tools.base import ToolCall, ToolResult
from src.workspace.context import WorkspaceContext

logger = structlog.get_logger(__name__)

MAX_FILE_SIZE = 512 * 1024  # 512 KB


class ReadFileTool:
    name = "read_file"
    description = "Read a file within the workspace. Returns file contents as text."
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from workspace root"},
        },
        "required": ["path"],
    }

    def __init__(self, workspace: WorkspaceContext) -> None:
        self._workspace = workspace

    async def execute(self, call: ToolCall) -> ToolResult:
        path_str: str = call.arguments["path"]
        safe_path = self._workspace.assert_path_safe(path_str)

        if not safe_path.exists():
            return ToolResult(
                success=False, output=f"File not found: {path_str}", error="not_found"
            )

        size = safe_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                output=f"File too large: {path_str} ({size} bytes, limit {MAX_FILE_SIZE})",
                error="too_large",
            )

        logger.debug("read_file", path=path_str)
        async with aiofiles.open(safe_path, encoding="utf-8", errors="replace") as fh:
            content = await fh.read()

        return ToolResult(success=True, output=content)
