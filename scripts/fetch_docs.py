#!/usr/bin/env python3
"""
Fetch and clean Microsoft documentation pages for RAG ingestion.

Downloads each URL from docs-urls.txt, extracts the article content,
and saves it as a clean markdown file in context_store/instructions/dotnet/.

Usage:
    python scripts/fetch_docs.py              # fetch all URLs in docs-urls.txt
    python scripts/fetch_docs.py --dry-run    # preview file paths without fetching
    python scripts/fetch_docs.py --url <url>  # fetch a single URL

After fetching, run:
    make ingest   (re-indexes context_store/ into ChromaDB)
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ── Configuration ──────────────────────────────────────────────────────────
DOCS_DIR = Path("context_store/instructions/dotnet")
URLS_FILE = Path("docs-urls.txt")
RATE_LIMIT_SECONDS = 1.5   # polite delay between requests to Microsoft servers
REQUEST_TIMEOUT = 30.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; local-ai-copilot/1.0; "
        "+documentation-fetcher; non-commercial)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Version detection from URL ─────────────────────────────────────────────
VERSION_RULES: list[tuple[str, str]] = [
    ("aspnetcore-3.1",  "core-3x"),
    ("aspnetcore-6.0",  "dotnet-6"),
    ("aspnetcore-8.0",  "dotnet-8"),
    ("aspnetcore-10.0", "dotnet-10"),
    ("ef-core-3",       "core-3x"),
    ("ef-core-6",       "dotnet-6"),
    ("ef-core-8",       "dotnet-8"),
    ("ef-core-10",      "dotnet-10"),
    ("dotnet-8",        "dotnet-8"),
    ("dotnet-10",       "dotnet-10"),
    ("/porting/",       "dotnet-6"),
    ("native-aot",      "dotnet-8"),
]


def detect_version(url: str) -> str:
    """Detect the .NET version folder from a URL."""
    for pattern, version in VERSION_RULES:
        if pattern in url:
            return version
    return "general"


def url_to_filename(url: str) -> str:
    """
    Convert a Microsoft docs URL to a descriptive filename.

    Examples:
        .../aspnet/core/?view=aspnetcore-8.0  → aspnet-core-aspnetcore-8.0.md
        .../ef/core/what-is-new/ef-core-8.0/whatsnew → ef-core-8.0-whatsnew.md
        .../dotnet/core/whats-new/dotnet-8/overview   → dotnet-8-overview.md
    """
    parsed = urlparse(url)

    # Strip locale prefix (/en-us/) from path
    path = re.sub(r"^/en-[a-z]+/", "/", parsed.path).strip("/")

    # Use query param 'view' as a suffix if present
    qs = parse_qs(parsed.query)
    view = qs.get("view", [""])[0]

    # Take last 3 meaningful path segments
    parts = [p for p in path.split("/") if p]
    slug = "-".join(parts[-3:]) if len(parts) >= 3 else "-".join(parts)

    if view:
        slug = f"{slug}-{view}"

    # Sanitise: lowercase, replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)

    return f"{slug}.md"


def output_path(url: str) -> Path:
    """Return the full output path for a URL."""
    version = detect_version(url)
    filename = url_to_filename(url)
    return DOCS_DIR / version / filename


# ── Content extraction ─────────────────────────────────────────────────────

def extract_with_trafilatura(html: str, url: str) -> str | None:
    """Primary extractor — trafilatura removes boilerplate automatically."""
    result = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=False,
        output_format="markdown",
        favor_recall=True,           # capture more content from tech docs
    )
    return result


def extract_with_bs4(html: str, url: str) -> str | None:
    """Fallback extractor using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for sel in (
        "header", "footer", "nav", "aside",
        ".nav-bar", ".sidebar", ".feedback-section",
        ".page-footer", ".action-menu", ".alert",
        "script", "style",
    ):
        for tag in soup.select(sel):
            tag.decompose()

    # Find main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="main")
        or soup.find(class_="content")
        or soup.body
    )
    if not main:
        return None

    lines: list[str] = []
    for el in main.find_all(
        ["h1", "h2", "h3", "h4", "h5", "p", "li", "pre", "code"]
    ):
        text = el.get_text(separator=" ", strip=True)
        if not text or len(text) < 3:
            continue
        tag = el.name
        if tag == "h1":
            lines.append(f"\n# {text}")
        elif tag == "h2":
            lines.append(f"\n## {text}")
        elif tag == "h3":
            lines.append(f"\n### {text}")
        elif tag in ("h4", "h5"):
            lines.append(f"\n#### {text}")
        elif tag == "p":
            lines.append(text)
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag in ("pre", "code"):
            lines.append(f"\n```\n{text}\n```\n")

    content = "\n".join(lines)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip() or None


def build_markdown(content: str, url: str, version: str) -> str:
    """Wrap extracted content with metadata header."""
    return (
        f"<!-- source: {url} -->\n"
        f"<!-- version: {version} -->\n"
        f"<!-- fetched by: scripts/fetch_docs.py -->\n\n"
        f"{content}\n"
    )


# ── Fetching ───────────────────────────────────────────────────────────────

async def fetch_one(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
    dry_run: bool = False,
) -> bool:
    """Fetch one URL and write markdown to dest. Returns True on success."""
    if dry_run:
        print(f"  [dry-run] {url}")
        print(f"            → {dest.relative_to(Path.cwd())}")
        return True

    try:
        print(f"  ↓ {url}")
        response = await client.get(url, headers=HEADERS, follow_redirects=True)
        response.raise_for_status()
        html = response.text

        # Try trafilatura first, then BeautifulSoup
        content: str | None = None
        if HAS_TRAFILATURA:
            content = extract_with_trafilatura(html, url)
        if not content and HAS_BS4:
            content = extract_with_bs4(html, url)
        if not content:
            print(f"  ✗ Could not extract content from {url}")
            return False

        if len(content) < 200:
            print(f"  ⚠ Very short content ({len(content)} chars) — page may be empty")

        version = detect_version(url)
        markdown = build_markdown(content, url, version)

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown, encoding="utf-8")  # noqa: ASYNC240

        rel = dest.relative_to(Path.cwd())
        print(f"  ✓ {len(content):>7,} chars  →  {rel}")
        return True

    except httpx.HTTPStatusError as exc:
        print(f"  ✗ HTTP {exc.response.status_code}: {url}")
        return False
    except httpx.TimeoutException:
        print(f"  ✗ Timeout: {url}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ Error ({type(exc).__name__}): {exc}")
        return False


def load_urls(path: Path) -> list[str]:
    """Read URLs from a file, skipping blank lines and comments."""
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        # Allow optional label after whitespace: url  label
        url = line.split()[0]
        if url.startswith("http"):
            urls.append(url)
    return urls


# ── CLI ────────────────────────────────────────────────────────────────────

async def run(args: argparse.Namespace) -> None:
    # Resolve URLs
    if args.url:
        urls = [args.url]
    elif URLS_FILE.exists():  # noqa: ASYNC240
        urls = load_urls(URLS_FILE)
    else:
        print(f"Error: {URLS_FILE} not found. Create it or pass --url.")
        sys.exit(1)

    if not urls:
        print("No URLs to fetch.")
        sys.exit(0)

    # Check extractors
    if not HAS_TRAFILATURA and not HAS_BS4:
        print(
            "Error: install at least one extractor:\n"
            "  pip install trafilatura     ← recommended\n"
            "  pip install beautifulsoup4  ← fallback"
        )
        sys.exit(1)

    extractor = "trafilatura" if HAS_TRAFILATURA else "beautifulsoup4 (fallback)"
    mode = "DRY RUN" if args.dry_run else "FETCHING"

    print(f"\n{'═' * 60}")
    print(f"  {mode} — {len(urls)} documentation pages")
    print(f"  Extractor : {extractor}")
    print(f"  Output    : {DOCS_DIR}/")
    print(f"{'═' * 60}\n")

    success = failed = 0

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for i, url in enumerate(urls):
            dest = output_path(url)

            if args.skip_existing and dest.exists():
                rel = dest.relative_to(Path.cwd())
                print(f"  ⏭  Already exists, skipping → {rel}")
                success += 1
                continue

            ok = await fetch_one(client, url, dest, dry_run=args.dry_run)
            if ok:
                success += 1
            else:
                failed += 1

            # Polite rate-limiting between requests
            if not args.dry_run and i < len(urls) - 1:
                await asyncio.sleep(RATE_LIMIT_SECONDS)

    print(f"\n{'═' * 60}")
    if args.dry_run:
        print(f"  Dry run complete — {success} URLs would be fetched")
    else:
        print(f"  Done — {success} succeeded, {failed} failed")
        if success > 0:
            print("\n  ✅ Next step: make ingest")
            print("     This indexes the downloaded docs into ChromaDB.")
    print(f"{'═' * 60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Microsoft .NET docs for RAG ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="Fetch a single URL instead of reading docs-urls.txt",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output paths without downloading anything",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip URLs whose output file already exists on disk (only fetch new URLs)",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()