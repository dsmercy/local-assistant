from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.loop import AgentLoop
from src.agent.options import AgentOptions
from src.ollama.client import OllamaClient
from src.ollama.options import OllamaOptions
from src.rag.context_builder import ContextBuilder
from src.rag.options import RagOptions
from src.rag.retriever import RagRetriever
from src.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)

_BASE_PROMPT_PATH = Path("agent-instructions/system-prompt.md")
_PHASE_PROMPTS_DIR = Path("agent-instructions/phases")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = OllamaClient(OllamaOptions())
    try:
        if not await client.is_ready():
            raise RuntimeError("Ollama is not running. Run 'ollama serve' to start it.")
    finally:
        await client.aclose()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"vscode-webview://.*|https?://localhost(:\d+)?|https?://127\.0\.0\.1(:\d+)?"
    ),
    allow_methods=["POST"],
    allow_headers=["*"],
)


# ── Dependency factories ──────────────────────────────────────────────────────


def get_ollama_options() -> OllamaOptions:
    return OllamaOptions()


def get_agent_options() -> AgentOptions:
    return AgentOptions()


def get_rag_options() -> RagOptions:
    return RagOptions()


async def get_agent_loop(
    ollama_opts: OllamaOptions = Depends(get_ollama_options),
    agent_opts: AgentOptions = Depends(get_agent_options),
    rag_opts: RagOptions = Depends(get_rag_options),
) -> AgentLoop:
    retriever = RagRetriever(rag_opts)
    builder = ContextBuilder(
        base_prompt_path=_BASE_PROMPT_PATH,
        retriever=retriever,
        phase_prompts_dir=_PHASE_PROMPTS_DIR,
    )
    try:
        system_prompt = builder.build(query="")
    except Exception:
        system_prompt = _BASE_PROMPT_PATH.read_text(encoding="utf-8")  # noqa: ASYNC240
    client = OllamaClient(ollama_opts)
    registry = ToolRegistry([], max_depth=agent_opts.max_tool_call_depth)
    return AgentLoop(
        client=client,
        registry=registry,
        options=agent_opts,
        system_prompt=system_prompt,
    )


# ── Models ────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    phase: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────


@app.post("/chat")
async def chat(
    request: ChatRequest,
    agent: AgentLoop = Depends(get_agent_loop),
) -> StreamingResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    async def token_stream() -> AsyncGenerator[str, None]:
        try:
            async for token in agent.run(request.message):
                yield f"data: {token}\n\n"
        except Exception as exc:
            logger.error("stream_error", error=str(exc))
            yield f"data: [Agent error: {exc}]\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
