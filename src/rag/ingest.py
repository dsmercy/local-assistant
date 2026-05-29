from __future__ import annotations

import contextlib
from pathlib import Path

import chromadb
import structlog
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.options import RagOptions

logger = structlog.get_logger(__name__)


async def ingest_collection(
    source_dir: Path,
    glob: str,
    collection_name: str,
    chunk_size: int,
    options: RagOptions,
) -> int:
    """Chunk, embed, and store documents. Returns chunk count."""
    if not source_dir.exists():  # noqa: ASYNC240
        print(f"{collection_name}: 0 chunks from 0 files")
        return 0

    loader = DirectoryLoader(
        str(source_dir),
        glob=glob,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        use_multithreading=False,
        silent_errors=True,
    )
    raw_docs = loader.load()

    if not raw_docs:
        print(f"{collection_name}: 0 chunks from 0 files")
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=options.chunk_overlap,
    )
    chunks = splitter.split_documents(raw_docs)

    for chunk in chunks:
        chunk.metadata["collection"] = collection_name
        source_path = Path(chunk.metadata.get("source", ""))
        with contextlib.suppress(ValueError):
            chunk.metadata["source"] = str(source_path.relative_to(source_dir))

    embeddings = OllamaEmbeddings(model=options.embed_model)

    chroma_client = chromadb.PersistentClient(path=str(options.chroma_db_path))
    with contextlib.suppress(Exception):
        chroma_client.delete_collection(collection_name)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        client=chroma_client,
    )

    file_count = len({doc.metadata.get("source", "") for doc in raw_docs})
    print(f"{collection_name}: {len(chunks)} chunks from {file_count} files")
    logger.info("ingest_complete", collection=collection_name, chunks=len(chunks), files=file_count)
    return len(chunks)
