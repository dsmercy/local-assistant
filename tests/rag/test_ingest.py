from pathlib import Path

import chromadb
import pytest

from src.rag.ingest import ingest_collection
from src.rag.options import RagOptions


class _FakeEmbeddings:
    def embed_documents(self, texts: list) -> list:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, text: str) -> list:
        return [0.1, 0.2, 0.3, 0.4]


@pytest.fixture(autouse=True)
def _patch_embeddings(monkeypatch):
    monkeypatch.setattr("src.rag.ingest.OllamaEmbeddings", lambda **kwargs: _FakeEmbeddings())


@pytest.fixture()
def source_dir(tmp_path):
    d = tmp_path / "source"
    d.mkdir()
    return d


@pytest.fixture()
def opts(tmp_path, source_dir):
    return RagOptions(
        chroma_db_path=tmp_path / "chroma",
        instructions_dir=source_dir,
        codebase_dir=source_dir,
        samples_dir=source_dir,
    )


async def test_ingest_returns_correct_chunk_count_for_small_file(source_dir, opts):
    (source_dir / "readme.md").write_text("# Test\n\nShort content for testing.", encoding="utf-8")
    count = await ingest_collection(source_dir, "**/*.md", "instructions", 512, opts)
    assert count >= 1


async def test_ingest_tags_each_chunk_with_collection_name(source_dir, opts):
    (source_dir / "readme.md").write_text("# Test\n\nSome content.", encoding="utf-8")
    await ingest_collection(source_dir, "**/*.md", "instructions", 512, opts)

    client = chromadb.PersistentClient(path=str(opts.chroma_db_path))
    col = client.get_collection("instructions")
    results = col.get(include=["metadatas"])
    assert all(m["collection"] == "instructions" for m in results["metadatas"])


async def test_ingest_tags_each_chunk_with_relative_source_path(source_dir, opts):
    (source_dir / "readme.md").write_text("# Test\n\nSome content.", encoding="utf-8")
    await ingest_collection(source_dir, "**/*.md", "instructions", 512, opts)

    client = chromadb.PersistentClient(path=str(opts.chroma_db_path))
    col = client.get_collection("instructions")
    results = col.get(include=["metadatas"])
    sources = [m["source"] for m in results["metadatas"]]
    assert all(not Path(s).is_absolute() for s in sources)
    assert any("readme.md" in s for s in sources)


async def test_ingest_twice_does_not_duplicate_chunks(source_dir, opts):
    (source_dir / "readme.md").write_text("# Test\n\nSome content.", encoding="utf-8")
    count1 = await ingest_collection(source_dir, "**/*.md", "instructions", 512, opts)
    count2 = await ingest_collection(source_dir, "**/*.md", "instructions", 512, opts)
    assert count1 == count2

    client = chromadb.PersistentClient(path=str(opts.chroma_db_path))
    col = client.get_collection("instructions")
    assert col.count() == count1
