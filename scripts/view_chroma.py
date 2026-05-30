#!/usr/bin/env python3
"""
Browse and search ChromaDB collections.

Usage:
    python scripts/view_chroma.py                    # show all collections summary
    python scripts/view_chroma.py --collection instructions
    python scripts/view_chroma.py --search "EF Core migration"
    python scripts/view_chroma.py --search "minimal API" --collection instructions
    python scripts/view_chroma.py --doc 0            # show full document by index
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import chromadb

CHROMA_PATH = Path("./chroma_db")
COLLECTIONS = ["instructions", "codebase", "samples"]
PAGE_WIDTH  = 80


def get_client() -> chromadb.ClientAPI:
    if not CHROMA_PATH.exists():
        print(f"\n  ✗  ChromaDB not found at '{CHROMA_PATH}'")
        print("     Run:  python scripts/ingest.py   to build the index first.\n")
        raise SystemExit(1)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def divider(char: str = "─", title: str = "") -> None:
    if title:
        pad = (PAGE_WIDTH - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print("─" * PAGE_WIDTH)


def show_summary(client: chromadb.ClientAPI) -> None:
    """Print a summary of all collections."""
    divider(title="ChromaDB — Collection Summary")
    print(f"  Path: {CHROMA_PATH.resolve()}\n")

    existing = {c.name for c in client.list_collections()}
    total_chunks = 0

    for name in COLLECTIONS:
        if name not in existing:
            print(f"  {name:<20} —  not yet created (run ingest)")
            continue

        col   = client.get_collection(name)
        count = col.count()
        total_chunks += count

        # Sample a few docs to show sources
        if count > 0:
            sample = col.get(limit=min(5, count), include=["metadatas"])
            sources = sorted({
                m.get("source", m.get("collection", "?"))
                for m in (sample["metadatas"] or [])
            })
            src_display = ", ".join(str(s)[:40] for s in sources[:3])
            if len(sources) > 3:
                src_display += f" … +{len(sources)-3} more"
        else:
            src_display = "(empty)"

        print(f"  {name:<20}  {count:>5} chunks   {src_display}")

    divider()
    print(f"  Total: {total_chunks} chunks across {len(COLLECTIONS)} collections\n")


def show_collection(client: chromadb.ClientAPI, name: str, limit: int = 20) -> None:
    """Print chunks from a specific collection."""
    col   = client.get_collection(name)
    count = col.count()

    divider(title=f"Collection: {name}  ({count} chunks total)")

    if count == 0:
        print("  (empty — run ingest)\n")
        return

    results = col.get(
        limit=limit,
        include=["documents", "metadatas"],
    )

    docs      = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    ids       = results.get("ids") or []

    for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metadatas)):
        source  = meta.get("source", meta.get("collection", "unknown"))
        version = meta.get("version", "")
        preview = textwrap.shorten(doc or "", width=120, placeholder="…")

        print(f"\n  [{i}] id: {doc_id[:24]}…")
        print(f"      source : {source}")
        if version:
            print(f"      version: {version}")
        print(f"      length : {len(doc or '')} chars")
        print(f"      preview: {preview}")

    if count > limit:
        print(f"\n  … showing {limit} of {count} chunks. Use --limit N to see more.\n")


def search_collection(
    client: chromadb.ClientAPI,
    query: str,
    collection_name: str | None,
    top_k: int = 5,
) -> None:
    """Semantic search across one or all collections."""
    # Need embeddings — use the same model as ingest
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        query_vec = embeddings.embed_query(query)
    except Exception as exc:
        print(f"\n  ✗  Could not embed query: {exc}")
        print("     Make sure Ollama is running and nomic-embed-text is pulled.\n")
        raise SystemExit(1)

    names = [collection_name] if collection_name else COLLECTIONS
    existing = {c.name for c in client.list_collections()}

    divider(title=f'Search: "{query}"')

    for name in names:
        if name not in existing:
            continue
        col = client.get_collection(name)
        if col.count() == 0:
            continue

        results = col.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, col.count()),
            include=["documents", "metadatas", "distances"],
        )

        docs      = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        print(f"\n  ── {name} ──")
        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
            source  = meta.get("source", "unknown")[:70]
            score   = 1 - dist          # convert distance → similarity (0–1)
            preview = textwrap.shorten(doc or "", width=160, placeholder="…")
            print(f"\n  [{i+1}] score: {score:.3f}")
            print(f"       source : {source}")
            print(f"       preview: {preview}")

    print()


def show_document(client: chromadb.ClientAPI, name: str, index: int) -> None:
    """Print a full document by its position in the collection."""
    col   = client.get_collection(name)
    count = col.count()

    if index >= count:
        print(f"\n  ✗  Index {index} out of range (collection has {count} items)\n")
        return

    results = col.get(
        limit=1,
        offset=index,
        include=["documents", "metadatas"],
    )

    doc  = (results.get("documents") or [""])[0]
    meta = (results.get("metadatas") or [{}])[0]

    divider(title=f"Document [{index}] from '{name}'")
    for k, v in meta.items():
        print(f"  {k}: {v}")
    divider()
    print(doc)
    divider()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Browse ChromaDB collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--collection", "-c",
        choices=COLLECTIONS,
        help="Filter to a specific collection",
    )
    parser.add_argument(
        "--search", "-s",
        metavar="QUERY",
        help="Semantic search across collections",
    )
    parser.add_argument(
        "--doc", "-d",
        type=int,
        metavar="INDEX",
        help="Show full document by index (use with --collection)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=20,
        help="Max chunks to show (default: 20)",
    )
    args = parser.parse_args()

    client = get_client()

    if args.search:
        search_collection(client, args.search, args.collection, top_k=args.limit)
    elif args.doc is not None:
        col = args.collection or "instructions"
        show_document(client, col, args.doc)
    elif args.collection:
        show_collection(client, args.collection, limit=args.limit)
    else:
        show_summary(client)
        print("  Tips:")
        print("    python scripts/view_chroma.py --collection instructions")
        print('    python scripts/view_chroma.py --search "EF Core migration"')
        print("    python scripts/view_chroma.py --doc 3 --collection instructions\n")


if __name__ == "__main__":
    main()
