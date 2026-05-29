from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from src.rag.context_builder import ContextBuilder


def _doc(content: str) -> Document:
    return Document(page_content=content, metadata={})


def _make_retriever(
    instructions: list | None = None,
    codebase: list | None = None,
    samples: list | None = None,
) -> MagicMock:
    r = MagicMock()
    r.retrieve.return_value = {
        "instructions": instructions or [],
        "codebase": codebase or [],
        "samples": samples or [],
    }
    return r


@pytest.fixture()
def base_prompt_file(tmp_path: Path) -> Path:
    f = tmp_path / "system-prompt.md"
    f.write_text("# Base System Prompt\n\nBase content.", encoding="utf-8")
    return f


def test_build_base_only_returns_system_prompt(base_prompt_file):
    builder = ContextBuilder(base_prompt_path=base_prompt_file, retriever=_make_retriever())
    result = builder.build("query")
    assert "# Base System Prompt" in result
    assert "## Relevant standards" not in result
    assert "## Canonical patterns to follow" not in result
    assert "## Related code in this codebase" not in result


def test_build_with_phase_includes_phase_section(base_prompt_file, tmp_path):
    phases_dir = tmp_path / "phases"
    phases_dir.mkdir()
    (phases_dir / "phase-01.md").write_text("# Phase 01 content.", encoding="utf-8")

    builder = ContextBuilder(
        base_prompt_path=base_prompt_file,
        retriever=_make_retriever(),
        phase_prompts_dir=phases_dir,
    )
    result = builder.build("query", phase="phase-01")
    assert "# Phase 01 content." in result


def test_build_with_rag_includes_all_three_section_headers(base_prompt_file):
    retriever = _make_retriever(
        instructions=[_doc("instruction chunk")],
        codebase=[_doc("codebase chunk")],
        samples=[_doc("samples chunk")],
    )
    builder = ContextBuilder(base_prompt_path=base_prompt_file, retriever=retriever)
    result = builder.build("query")
    assert "## Relevant standards" in result
    assert "## Canonical patterns to follow" in result
    assert "## Related code in this codebase" in result


def test_build_caps_total_length_and_does_not_crash(base_prompt_file):
    huge_chunk = "X" * 200_000
    retriever = _make_retriever(
        instructions=[_doc(huge_chunk)],
        codebase=[_doc(huge_chunk)],
        samples=[_doc(huge_chunk)],
    )
    builder = ContextBuilder(base_prompt_path=base_prompt_file, retriever=retriever)
    result = builder.build("query")
    assert len(result) <= 28_000 * 4


def test_system_prompt_read_from_agent_instructions_path(tmp_path):
    custom_prompt = tmp_path / "custom-system.md"
    custom_prompt.write_text("# Custom System", encoding="utf-8")
    builder = ContextBuilder(base_prompt_path=custom_prompt, retriever=_make_retriever())
    result = builder.build("query")
    assert "# Custom System" in result
