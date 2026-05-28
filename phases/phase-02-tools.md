# Phase 02 — Tool Implementations

## Phase goal
Implement all five ToolHandler classes one at a time, each tested before the next begins.
All file operations are sandboxed. Shell is fully blocked except the allow-list.

## Entry criteria
- [ ] Phase 01 exit gates passed · `pytest -x` green

## Active standards
§7 Code quality · §8 Error handling · §10 Performance · §19 Tool rules · §24 Security

## Shared types & workspace (implement first)

### WorkspaceContext — `src/workspace/context.py`
```python
from pathlib import Path
import fnmatch

class PathSafetyError(Exception): ...
class WorkspaceNotFoundError(Exception): ...

class WorkspaceContext:
    def __init__(self, root: Path | None = None) -> None:
        self.root: Path = root or self._detect_root()

    def is_path_safe(self, requested: str) -> bool:
        """Return False for traversal, null bytes, or out-of-root paths."""
        if "\0" in requested or ".." in requested:
            return False
        resolved = (self.root / requested).resolve()
        return resolved.is_relative_to(self.root)

    def assert_path_safe(self, requested: str) -> Path:
        """Resolve and return the safe absolute path or raise PathSafetyError."""
        if not self.is_path_safe(requested):
            raise PathSafetyError(f"Path '{requested}' is outside the workspace root.")
        return (self.root / requested).resolve()

    def get_ignored_patterns(self) -> list[str]:
        """Read .gitignore patterns; always includes standard noise folders."""
        always_ignore = ["__pycache__", ".venv", "*.pyc", ".git", "node_modules", "dist"]
        gitignore = self.root / ".gitignore"
        if gitignore.exists():
            patterns = [l.strip() for l in gitignore.read_text().splitlines()
                        if l.strip() and not l.startswith("#")]
            return always_ignore + patterns
        return always_ignore

    def _detect_root(self) -> Path:
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            if any(parent.glob("pyproject.toml")) or any(parent.glob("*.sln")):
                return parent
        raise WorkspaceNotFoundError("No pyproject.toml found walking up from cwd.")
```

### Base ToolHandler — `src/tools/base.py`
```python
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    arguments: dict

@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: str
    error: str | None = None

@runtime_checkable
class ToolHandler(Protocol):
    name: str
    description: str
    parameters_schema: dict

    async def execute(self, call: ToolCall) -> ToolResult: ...
```

---

## Tools — implement in order, test each before moving on

### Tool 2.1 — ReadFileTool (`src/tools/read_file.py`)

Rules:
- `assert_path_safe` first — `PathSafetyError` on violation
- `aiofiles.open` for async read — propagate `asyncio.CancelledError`
- Cap at 512 KB — return `ToolResult(success=False, …)` for larger files
- File not found → `ToolResult(success=False, output="File not found: {path}")`
- Never log file contents — log only the relative path at `debug`

| Test scenario | Expected |
|---|---|
| Valid path | Returns content in `ToolResult.output` |
| `..` traversal | `PathSafetyError` |
| Null byte | `PathSafetyError` |
| File not found | `ToolResult(success=False, …)` |
| File > 512 KB | `ToolResult(success=False, "File too large: …")` |
| Cancellation | `asyncio.CancelledError` propagated |

---

### Tool 2.2 — ListFilesTool (`src/tools/list_files.py`)

Rules:
- Accept optional `directory` arg (default: `workspace.root`)
- `assert_path_safe` the directory arg before use
- Use `Path.rglob("*")` — skip `is_path_safe` failures silently
- Respect `.gitignore` patterns from `workspace.get_ignored_patterns()`
- Cap at 500 results — append truncation notice
- Return paths relative to workspace root, one per line

| Test scenario | Expected |
|---|---|
| Valid directory | Relative paths, one per line |
| Directory outside root | `PathSafetyError` |
| Over 500 files | Truncation notice in output |
| `.gitignore` excludes a file | Excluded file absent |
| `__pycache__` always excluded | Never appears |

---

### Tool 2.3 — SearchFilesTool (`src/tools/search_files.py`)

Rules:
- Params: `pattern: str`, `is_regex: bool = False`, `directory: str | None = None`
- `assert_path_safe` the directory
- Respect same exclusion list as `ListFilesTool`
- Return `{relative_path}:{line_number}: {matched_line}` per match
- Cap at 200 matches — truncate with notice
- Catch `re.error` → `ToolResult(success=False, "Invalid regex: …")`

| Test scenario | Expected |
|---|---|
| Literal match | Correct file + line |
| Regex match | Correct file + line |
| Invalid regex | `ToolResult(success=False, "Invalid regex: …")` |
| No matches | `ToolResult(success=True, "No matches found")` |
| Over 200 matches | Truncation notice |
| Directory outside root | `PathSafetyError` |

---

### Tool 2.4 — WriteFileTool (`src/tools/write_file.py`)

Rules:
- `assert_path_safe` before any write
- Accept optional `line_range: str` (e.g. `"10-20"`) for targeted patch
- If no `line_range`: overwrite entire file only when model explicitly requests it
- Atomic write: write to `.tmp` then `Path.replace()` — never leave partial writes
- If `line_range` out of bounds: `ToolResult(success=False, "…out of bounds…")`
- Never create parent directories silently

| Test scenario | Expected |
|---|---|
| Full file write | Content matches exactly |
| Line-range patch | Only targeted lines replaced |
| Out-of-bounds range | `ToolResult(success=False, …)` |
| Path outside root | `PathSafetyError` |
| Parent dir missing | `ToolResult(success=False, "Directory does not exist: …")` |

---

### Tool 2.5 — RunCommandTool (`src/tools/run_command.py`)

Rules:
- **Allow-list first** — raise `ValueError` immediately if not in list:
  ```python
  ALLOWED = frozenset({"pytest", "ruff", "mypy", "black", "pip"})
  ```
- Use `asyncio.create_subprocess_exec` — never `shell=True`
- `cwd` = `workspace.root`
- Configurable timeout (default 60s) — kill and return error on timeout
- Capture both `stdout` and `stderr` — include `stderr` in output on failure
- Support cancellation via `asyncio.CancelledError`

| Test scenario | Expected |
|---|---|
| `pytest` (exit 0, mocked) | `ToolResult(success=True, …)` |
| `pytest` (exit 1, mocked) | `ToolResult(success=False, stderr included)` |
| `rm` command | `ValueError` immediately |
| `bash` command | `ValueError` immediately |
| Timeout fires | `ToolResult(success=False, "Command timed out after 60s")` |
| Cancellation | `asyncio.CancelledError` propagated |

---

### ToolRegistry — `src/tools/registry.py`

```python
class ToolNotFoundException(Exception): ...
class ToolDepthExceededError(Exception): ...

class ToolRegistry:
    def __init__(self, handlers: list[ToolHandler], max_depth: int = 10) -> None: ...
    def resolve(self, name: str) -> ToolHandler: ...  # raises ToolNotFoundException
    def increment_depth(self) -> None: ...             # raises ToolDepthExceededError
    def reset_depth(self) -> None: ...
    @property
    def definitions(self) -> list[ToolDefinition]: ...
```

## Validation gate
```bash
pytest tests/tools/ tests/workspace/ -v
ruff check src/tools/ src/workspace/
mypy src/tools/ src/workspace/
```

## Exit criteria
- [ ] All five tools and WorkspaceContext tested and green
- [ ] `PathSafetyError` raised by every file tool on traversal (automated)
- [ ] `ValueError` raised by RunCommandTool on non-allowed command (automated)
- [ ] Atomic write tested — no partial files on failure
- [ ] `mypy` strict passes on all tool files

## What not to do
- Do not wire tools into the agent loop (Phase 03)
- Do not add any shell commands beyond the allow-list
- Do not log file contents at any log level
