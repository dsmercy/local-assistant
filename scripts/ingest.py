"""Run RAG ingestion: index context_store/ into ChromaDB."""

import asyncio

from src.rag.ingest import ingest_collection
from src.rag.options import RagOptions


async def main() -> None:
    opts = RagOptions()
    await ingest_collection(
        opts.instructions_dir, "**/*.md", "instructions", opts.instructions_chunk_size, opts
    )
    await ingest_collection(
        opts.codebase_dir, "**/*.py", "codebase", opts.codebase_chunk_size, opts
    )
    await ingest_collection(
        opts.samples_dir, "**/*.py", "samples", opts.samples_chunk_size, opts
    )


if __name__ == "__main__":
    asyncio.run(main())
