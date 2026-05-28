import fnmatch
from typing import Any

import structlog

from src.tools.base import ToolCall, ToolResult
from src.workspace.context import WorkspaceContext

logger = structlog.get_logger(__name__)

MAX_RESULTS = 500


class ListFilesTool:
    name = "list_files"
    description = "List files in the workspace, respecting .gitignore patterns."
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Optional subdirectory relative to workspace root",
            },
        },
        "required": [],
    }

    def __init__(self, workspace: WorkspaceContext) -> None:
        self._workspace = workspace

    async def execute(self, call: ToolCall) -> ToolResult:
        directory_str: str | None = call.arguments.get("directory")

        if directory_str is not None:
            start_path = self._workspace.assert_path_safe(directory_str)
        else:
            start_path = self._workspace.root

        ignored = self._workspace.get_ignored_patterns()
        results: list[str] = []
        truncated = False

        for path in start_path.rglob("*"):
            if not path.is_file():
                continue

            try:
                rel = path.relative_to(self._workspace.root)
            except ValueError:
                continue

            if _is_ignored(rel.parts, ignored):
                continue

            results.append(str(rel))
            if len(results) >= MAX_RESULTS:
                truncated = True
                break

        output = "\n".join(results)
        if truncated:
            output += f"\n[Truncated: showing first {MAX_RESULTS} results]"
        return ToolResult(success=True, output=output)


def _is_ignored(parts: tuple[str, ...], patterns: list[str]) -> bool:
    for part in parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False
