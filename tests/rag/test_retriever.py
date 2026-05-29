from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from src.rag.options import RagOptions
from src.rag.retriever import RagRetriever


def _doc(content: str) -> Document:
    return Document(page_content=content, metadata={})


def _make_retriever(
    instructions: list | None = None,
    codebase: list | None = None,
    samples: list | None = None,
) -> RagRetriever:
    opts = RagOptions()
    r: RagRetriever = object.__new__(RagRetriever)
    r._opts = opts

    r._instructions = MagicMock()
    r._instructions.similarity_search.return_value = instructions or []

    r._codebase = MagicMock()
    r._codebase.similarity_search.return_value = codebase or []

    r._samples = MagicMock()
    r._samples.similarity_search.return_value = samples or []

    return r


@pytest.fixture()
def retriever() -> RagRetriever:
    return _make_retriever(
        instructions=[_doc("instruction chunk")],
        codebase=[_doc("codebase chunk")],
        samples=[_doc("samples chunk")],
    )


def test_retrieve_returns_results_from_all_three_collections(retriever):
    results = retriever.retrieve("test query")
    assert "instructions" in results
    assert "codebase" in results
    assert "samples" in results
    assert len(results["instructions"]) == 1
    assert len(results["codebase"]) == 1
    assert len(results["samples"]) == 1


def test_retrieve_instructions_uses_separate_collection(retriever):
    retriever.retrieve("query")
    retriever._instructions.similarity_search.assert_called_once_with(
        "query", k=retriever._opts.retrieval_k
    )


def test_retrieve_codebase_uses_separate_collection(retriever):
    retriever.retrieve("query")
    retriever._codebase.similarity_search.assert_called_once_with("query", k=3)


def test_retrieve_samples_uses_separate_collection(retriever):
    retriever.retrieve("query")
    retriever._samples.similarity_search.assert_called_once_with("query", k=2)
