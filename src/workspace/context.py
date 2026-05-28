from pathlib import Path


class PathSafetyError(Exception):
    """Raised when a requested path is outside the workspace root."""


class WorkspaceNotFoundError(Exception):
    """Raised when no project root can be detected."""


class WorkspaceContext:
    """Holds the workspace root and enforces path safety for all file operations."""

    def __init__(self, root: Path | None = None) -> None:
        self.root: Path = root or self._detect_root()

    def is_path_safe(self, requested: str) -> bool:
        """Return False for traversal attempts, null bytes, or out-of-root paths."""
        if "\0" in requested or ".." in requested:
            return False
        resolved = (self.root / requested).resolve()
        return resolved.is_relative_to(self.root)

    def assert_path_safe(self, requested: str) -> Path:
        """Resolve and return the safe absolute path, or raise PathSafetyError."""
        if not self.is_path_safe(requested):
            raise PathSafetyError(f"Path '{requested}' is outside the workspace root.")
        return (self.root / requested).resolve()

    def get_ignored_patterns(self) -> list[str]:
        """Return .gitignore patterns merged with always-ignored directories."""
        always_ignore = ["__pycache__", ".venv", "*.pyc", ".git", "node_modules", "dist"]
        gitignore = self.root / ".gitignore"
        if gitignore.exists():
            patterns = [
                line.strip()
                for line in gitignore.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
            return always_ignore + patterns
        return always_ignore

    def _detect_root(self) -> Path:
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            if any(parent.glob("pyproject.toml")) or any(parent.glob("*.sln")):
                return parent
        raise WorkspaceNotFoundError("No pyproject.toml or .sln found walking up from cwd.")
