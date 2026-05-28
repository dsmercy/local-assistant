import re
from typing import Any

import aiofiles
import structlog

from src.tools.base import ToolCall, ToolResult
from src.tools.list_files import _is_ignored
from src.workspace.context import WorkspaceContext

logger = structlog.get_logger(__name__)

MAX_MATCHES = 200


class SearchFilesTool:
    name = "search_files"
    description = "Search for a literal or regex pattern across files in the workspace."
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern"},
            "is_regex": {
                "type": "boolean",
                "description": "Treat pattern as a regular expression",
                "default": False,
            },
            "directory": {
                "type": "string",
                "description": "Optional subdirectory to search in",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace: WorkspaceContext) -> None:
        self._workspace = workspace

    async def execute(self, call: ToolCall) -> ToolResult:
        pattern: str = call.arguments["pattern"]
        is_regex: bool = bool(call.arguments.get("is_regex", False))
        directory_str: str | None = call.arguments.get("directory")

        if directory_str is not None:
            start_path = self._workspace.assert_path_safe(directory_str)
        else:
            start_path = self._workspace.root

        compiled: re.Pattern[str] | None = None
        if is_regex:
            try:
                compiled = re.compile(pattern)
            except re.error as exc:
                return ToolResult(success=False, output=f"Invalid regex: {exc}", error=str(exc))

        ignored = self._workspace.get_ignored_patterns()
        matches: list[str] = []
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

            try:
                async with aiofiles.open(path, encoding="utf-8", errors="replace") as fh:
                    content = await fh.read()
            except OSError:
                continue

            for line_num, line in enumerate(content.splitlines(), start=1):
                hit = bool(compiled.search(line)) if compiled is not None else (pattern in line)
                if hit:
                    matches.append(f"{rel}:{line_num}: {line}")
                    if len(matches) >= MAX_MATCHES:
                        truncated = True
                        break
            if truncated:
                break

        if not matches:
            return ToolResult(success=True, output="No matches found")

        output = "\n".join(matches)
        if truncated:
            output += f"\n[Truncated: showing first {MAX_MATCHES} matches]"
        return ToolResult(success=True, output=output)
