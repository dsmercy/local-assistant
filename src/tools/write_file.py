from typing import Any

import aiofiles
import structlog

from src.tools.base import ToolCall, ToolResult
from src.workspace.context import WorkspaceContext

logger = structlog.get_logger(__name__)


class WriteFileTool:
    name = "write_file"
    description = "Write or patch a file within the workspace using an atomic write."
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from workspace root"},
            "content": {"type": "string", "description": "Content to write"},
            "line_range": {
                "type": "string",
                "description": "Optional line range for targeted patch, e.g. '10-20'",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, workspace: WorkspaceContext) -> None:
        self._workspace = workspace

    async def execute(self, call: ToolCall) -> ToolResult:
        path_str: str = call.arguments["path"]
        content: str = call.arguments["content"]
        line_range: str | None = call.arguments.get("line_range")

        safe_path = self._workspace.assert_path_safe(path_str)

        if not safe_path.parent.exists():
            return ToolResult(
                success=False,
                output=f"Directory does not exist: {safe_path.parent}",
                error="missing_parent",
            )

        final_content: str
        if line_range is not None:
            try:
                start_str, end_str = line_range.split("-", 1)
                start = int(start_str)
                end = int(end_str)
            except (ValueError, AttributeError):
                return ToolResult(
                    success=False,
                    output=f"Invalid line_range format: '{line_range}'",
                    error="bad_line_range",
                )

            if not safe_path.exists():
                return ToolResult(
                    success=False, output=f"File not found: {path_str}", error="not_found"
                )

            lines = safe_path.read_text(encoding="utf-8").splitlines(keepends=True)
            if start < 1 or end > len(lines) or start > end:
                return ToolResult(
                    success=False,
                    output=f"Line range {line_range} out of bounds (file has {len(lines)} lines)",
                    error="out_of_bounds",
                )

            replacement = content.splitlines(keepends=True)
            final_content = "".join(lines[: start - 1] + replacement + lines[end:])
        else:
            final_content = content

        tmp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
        try:
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as fh:
                await fh.write(final_content)
            tmp_path.replace(safe_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

        logger.debug("write_file", path=path_str)
        return ToolResult(success=True, output=f"Successfully wrote {path_str}")
