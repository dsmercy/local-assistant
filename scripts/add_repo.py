#!/usr/bin/env python3
"""
Add source code repositories to the agent's RAG knowledge base.

Downloads or copies repository files into context_store/codebase/ or
context_store/samples/, then run `python scripts/ingest.py` to index them.

Usage:
    # Add a local repository
    python scripts/add_repo.py --path /path/to/my/dotnet/project

    # Add a GitHub repository (clones a shallow copy)
    python scripts/add_repo.py --github https://github.com/user/repo

    # Add as canonical samples instead of codebase
    python scripts/add_repo.py --path /path/to/patterns --as-samples

    # Preview what files would be added (no copy)
    python scripts/add_repo.py --path /path/to/repo --dry-run

    # List all repositories currently indexed
    python scripts/add_repo.py --list

    # Remove a repository from context_store
    python scripts/add_repo.py --remove my-repo-name

After adding, always run:
    python scripts/ingest.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# ── Destination directories ────────────────────────────────────────────────
CODEBASE_DIR = Path("context_store/codebase")
SAMPLES_DIR  = Path("context_store/samples")

# ── File extensions to include ─────────────────────────────────────────────
INCLUDE_EXTENSIONS: frozenset[str] = frozenset({
    # .NET / C#
    ".cs", ".csproj", ".sln", ".razor", ".cshtml", ".http",
    # Config / settings
    ".json", ".yaml", ".yml", ".xml", ".ini", ".toml",
    # Web / React / TypeScript
    ".ts", ".tsx", ".js", ".jsx", ".css", ".scss",
    # Python
    ".py",
    # Docs
    ".md", ".txt",
    # SQL
    ".sql",
})

# ── Directories to always skip ─────────────────────────────────────────────
EXCLUDED_DIRS: frozenset[str] = frozenset({
    # .NET build artefacts
    "bin", "obj", ".vs", "packages", "TestResults",
    # Node
    "node_modules", "dist", "build", ".next", "coverage",
    # Python
    "__pycache__", ".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    # Version control
    ".git", ".svn", ".hg",
    # IDE
    ".idea", ".vscode",
    # Generated
    "Migrations",        # EF Core migrations — usually generated
    "migrations",
    "wwwroot",           # static assets, often generated/minified
})

# ── Files to always skip ───────────────────────────────────────────────────
EXCLUDED_PATTERNS: tuple[str, ...] = (
    "*.min.js", "*.min.css",           # minified
    "*.g.cs", "*.designer.cs",         # generated C#
    "AssemblyInfo.cs",
    "*.lock", "package-lock.json",     # lockfiles
    "*.suo", "*.user", "*.DotSettings",
    "*.png", "*.jpg", "*.jpeg",        # images
    "*.gif", "*.svg", "*.ico",
    "*.pdf", "*.zip", "*.exe",
    "*.dll", "*.pdb", "*.nupkg",       # binaries
)

# ── Size limits ────────────────────────────────────────────────────────────
MAX_FILE_SIZE_KB = 100    # skip files larger than this
MAX_TOTAL_FILES  = 2000   # warn if a repo has more than this many eligible files


# ── Helpers ────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert a repository name to a safe folder name."""
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", name)
    return re.sub(r"-{2,}", "-", slug).strip("-").lower()


def matches_excluded_pattern(path: Path) -> bool:
    """Return True if the filename matches any excluded pattern."""
    import fnmatch
    name = path.name
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDED_PATTERNS)


def should_include(file: Path) -> bool:
    """Return True if this file should be copied into context_store."""
    # Check extension
    if file.suffix.lower() not in INCLUDE_EXTENSIONS:
        return False
    # Check excluded filename patterns
    if matches_excluded_pattern(file):
        return False
    # Skip very large files
    try:
        size_kb = file.stat().st_size / 1024
        if size_kb > MAX_FILE_SIZE_KB:
            return False
    except OSError:
        return False
    return True


def collect_files(root: Path) -> list[Path]:
    """
    Walk root and collect all files that should be indexed.
    Respects EXCLUDED_DIRS and INCLUDE_EXTENSIONS.
    """
    files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        # Skip if any parent directory is excluded
        rel_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue

        if should_include(path):
            files.append(path)

    return sorted(files)


def copy_repo_files(
    source_root: Path,
    dest_root: Path,
    repo_name: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Copy eligible files from source_root into dest_root/repo_name/.
    Returns (copied_count, skipped_count).
    """
    dest = dest_root / repo_name
    files = collect_files(source_root)

    if not files:
        print(f"  ⚠  No eligible files found in {source_root}")
        return 0, 0

    if len(files) > MAX_TOTAL_FILES:
        print(
            f"  ⚠  Large repository: {len(files)} eligible files found.\n"
            f"     Consider using --filter to restrict to specific subdirectories."
        )

    copied = skipped = 0
    ext_counts: dict[str, int] = {}

    for src in files:
        rel = src.relative_to(source_root)
        dst = dest / rel
        ext = src.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if dry_run:
            print(f"  [dry-run] {rel}")
            copied += 1
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except OSError as exc:
            print(f"  ✗ Could not copy {rel}: {exc}")
            skipped += 1

    return copied, skipped


def print_ext_summary(files: list[Path]) -> None:
    ext_counts: dict[str, int] = {}
    for f in files:
        ext = f.suffix.lower() or "(no ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        print(f"    {ext:<15} {count} files")


def clone_github(url: str, target: Path) -> Path:
    """Shallow-clone a GitHub repo into a temp directory."""
    print(f"  Cloning {url} …")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ✗ Git clone failed:\n{exc.stderr}")
        raise SystemExit(1)
    except FileNotFoundError:
        print("  ✗ 'git' is not installed. Install git and try again.")
        raise SystemExit(1)
    return target


def repo_name_from_url(url: str) -> str:
    """Extract repo name from a GitHub URL."""
    path = urlparse(url).path.strip("/")
    name = path.split("/")[-1]
    return slugify(name.removesuffix(".git"))


def repo_name_from_path(path: Path) -> str:
    return slugify(path.name)


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_add_local(args: argparse.Namespace) -> None:
    source = Path(args.path).resolve()
    if not source.exists():
        print(f"\n  ✗  Path not found: {source}\n")
        raise SystemExit(1)

    repo_name = args.name or repo_name_from_path(source)
    dest_root  = SAMPLES_DIR if args.as_samples else CODEBASE_DIR
    dest_label = "samples" if args.as_samples else "codebase"

    print(f"\n{'═'*60}")
    print(f"  Adding local repository")
    print(f"  Source  : {source}")
    print(f"  Dest    : context_store/{dest_label}/{repo_name}/")
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'COPY'}")
    print(f"{'═'*60}\n")

    files = collect_files(source)
    print(f"  Found {len(files)} eligible files:")
    print_ext_summary(files)
    print()

    copied, skipped = copy_repo_files(source, dest_root, repo_name, dry_run=args.dry_run)

    _print_result(copied, skipped, args.dry_run, dest_label, repo_name)


def cmd_add_github(args: argparse.Namespace) -> None:
    url = args.github
    repo_name = args.name or repo_name_from_url(url)
    dest_root  = SAMPLES_DIR if args.as_samples else CODEBASE_DIR
    dest_label = "samples" if args.as_samples else "codebase"

    print(f"\n{'═'*60}")
    print(f"  Adding GitHub repository")
    print(f"  URL     : {url}")
    print(f"  Dest    : context_store/{dest_label}/{repo_name}/")
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'CLONE + COPY'}")
    print(f"{'═'*60}\n")

    with tempfile.TemporaryDirectory(prefix="add_repo_") as tmp:
        clone_target = Path(tmp) / "repo"

        if args.dry_run:
            print("  [dry-run] Would clone repository — skipping network call")
            print("  [dry-run] Would copy eligible files to context_store/")
            return

        clone_github(url, clone_target)
        print(f"  ✓ Cloned successfully\n")

        files = collect_files(clone_target)
        print(f"  Found {len(files)} eligible files:")
        print_ext_summary(files)
        print()

        copied, skipped = copy_repo_files(clone_target, dest_root, repo_name)

    _print_result(copied, skipped, args.dry_run, dest_label, repo_name)


def cmd_list(args: argparse.Namespace) -> None:
    print(f"\n{'═'*60}")
    print("  context_store contents")
    print(f"{'═'*60}\n")

    for store_name, store_dir in [("codebase", CODEBASE_DIR), ("samples", SAMPLES_DIR)]:
        if not store_dir.exists():
            print(f"  {store_name}/   (empty)")
            continue

        repos = [d for d in store_dir.iterdir() if d.is_dir()]
        files_flat = [f for f in store_dir.rglob("*") if f.is_file()]

        if not repos and not files_flat:
            print(f"  {store_name}/   (empty)")
            continue

        print(f"  {store_name}/   ({len(files_flat)} files total)")

        # Show top-level subdirectories as "repos"
        for repo in sorted(repos):
            repo_files = list(repo.rglob("*"))
            file_count = sum(1 for f in repo_files if f.is_file())
            size_kb    = sum(
                f.stat().st_size for f in repo_files if f.is_file()
            ) / 1024
            print(f"    ├── {repo.name:<30} {file_count:>4} files  {size_kb:>7.0f} KB")

        # Also count loose files (not in a subdir)
        loose = [f for f in store_dir.iterdir() if f.is_file()]
        if loose:
            print(f"    └── (loose files)  {len(loose)}")
        print()


def cmd_remove(args: argparse.Namespace) -> None:
    name = args.remove
    removed = False

    for store_dir in [CODEBASE_DIR, SAMPLES_DIR]:
        target = store_dir / name
        if target.exists() and target.is_dir():
            store_label = store_dir.name
            confirm = input(
                f"  Delete context_store/{store_label}/{name}/ ? [y/N] "
            ).strip().lower()
            if confirm == "y":
                shutil.rmtree(target)
                print(f"  ✓ Removed context_store/{store_label}/{name}/")
                print(f"  ↻ Run python scripts/ingest.py to update the index")
                removed = True
            else:
                print("  Cancelled.")
            break

    if not removed and not any(
        (d / name).exists() for d in [CODEBASE_DIR, SAMPLES_DIR]
    ):
        print(f"\n  ✗  Repository '{name}' not found in context_store/\n")
        print("  Run:  python scripts/add_repo.py --list   to see what's available\n")


def _print_result(
    copied: int, skipped: int, dry_run: bool, dest_label: str, repo_name: str
) -> None:
    print(f"\n{'═'*60}")
    if dry_run:
        print(f"  Dry run complete — {copied} files would be copied")
    else:
        print(f"  Done — {copied} files copied, {skipped} skipped")
        if copied > 0:
            print(f"\n  ✅ Next step:")
            print(f"     python scripts/ingest.py")
            print(f"\n     This chunks and embeds the new files into ChromaDB.")
            print(f"     The agent will then reference {repo_name} when answering questions.")
    print(f"{'═'*60}\n")


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add code repositories to the agent's RAG knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--path", "-p",
        metavar="PATH",
        help="Local directory path of a repository to add",
    )
    source.add_argument(
        "--github", "-g",
        metavar="URL",
        help="GitHub repository URL to clone and add",
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all repositories currently in context_store/",
    )
    parser.add_argument(
        "--remove", "-r",
        metavar="NAME",
        help="Remove a repository from context_store/ by folder name",
    )
    parser.add_argument(
        "--name", "-n",
        metavar="NAME",
        help="Override the repository folder name (default: derived from path/URL)",
    )
    parser.add_argument(
        "--as-samples",
        action="store_true",
        help="Save to context_store/samples/ instead of context_store/codebase/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be copied without making any changes",
    )

    args = parser.parse_args()

    if args.list:
        cmd_list(args)
    elif args.remove:
        cmd_remove(args)
    elif args.path:
        cmd_add_local(args)
    elif args.github:
        cmd_add_github(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
