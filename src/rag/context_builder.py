from __future__ import annotations

from pathlib import Path

import structlog

from src.rag.retriever import RagRetriever

logger = structlog.get_logger(__name__)

_MAX_CHARS = 28_000 * 4


class ContextBuilder:
    """Assembles BASE_SYSTEM_PROMPT + optional PHASE_PROMPT + RAG chunks."""

    def __init__(
        self,
        base_prompt_path: Path,
        retriever: RagRetriever,
        phase_prompts_dir: Path | None = None,
    ) -> None:
        self._base_prompt = base_prompt_path.read_text(encoding="utf-8")
        self._retriever = retriever
        self._phase_prompts_dir = phase_prompts_dir

    def build(self, query: str, phase: str | None = None) -> str:
        """Return base_prompt + phase_prompt (if provided) + retrieved chunks."""
        parts: list[str] = [self._base_prompt]

        if phase and self._phase_prompts_dir:
            phase_file = self._phase_prompts_dir / f"{phase}.md"
            if phase_file.exists():
                parts.append(phase_file.read_text(encoding="utf-8"))

        results = self._retriever.retrieve(query)
        instructions = results.get("instructions", [])
        samples = results.get("samples", [])
        codebase = results.get("codebase", [])

        if instructions:
            parts.append(
                "## Relevant standards\n"
                + "\n\n".join(doc.page_content for doc in instructions)
            )
        if samples:
            parts.append(
                "## Canonical patterns to follow\n"
                + "\n\n".join(doc.page_content for doc in samples)
            )
        if codebase:
            parts.append(
                "## Related code in this codebase\n"
                + "\n\n".join(doc.page_content for doc in codebase)
            )

        combined = "\n\n---\n\n".join(parts)
        if len(combined) > _MAX_CHARS:
            combined = combined[:_MAX_CHARS]

        logger.info(
            "context_built",
            query_length=len(query),
            instructions_chunks=len(instructions),
            samples_chunks=len(samples),
            codebase_chunks=len(codebase),
            total_length=len(combined),
        )
        return combined
