from __future__ import annotations

import structlog
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from src.rag.options import RagOptions

logger = structlog.get_logger(__name__)


class RagRetriever:
    def __init__(self, options: RagOptions) -> None:
        embeddings = OllamaEmbeddings(model=options.embed_model)
        self._opts = options
        self._instructions: Chroma = Chroma(
            persist_directory=str(options.chroma_db_path),
            embedding_function=embeddings,
            collection_name="instructions",
        )
        self._codebase: Chroma = Chroma(
            persist_directory=str(options.chroma_db_path),
            embedding_function=embeddings,
            collection_name="codebase",
        )
        self._samples: Chroma = Chroma(
            persist_directory=str(options.chroma_db_path),
            embedding_function=embeddings,
            collection_name="samples",
        )

    def retrieve(self, query: str) -> dict[str, list[Document]]:
        """Retrieve from all three collections independently."""
        logger.debug("retrieve_started", query_length=len(query))
        return {
            "instructions": self._instructions.similarity_search(query, k=self._opts.retrieval_k),
            "codebase": self._codebase.similarity_search(query, k=3),
            "samples": self._samples.similarity_search(query, k=2),
        }
