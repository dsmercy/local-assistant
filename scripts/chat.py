"""Interactive CLI for the local AI agent. Bypasses the FastAPI server entirely.

Usage:
    python scripts/chat.py                        # interactive mode
    python scripts/chat.py "Your question here"   # single query
"""

import asyncio
import sys
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.loop import AgentLoop
from src.agent.options import AgentOptions
from src.ollama.client import OllamaClient
from src.ollama.options import OllamaOptions
from src.tools.registry import ToolRegistry


async def ask(message: str) -> None:
    opts = OllamaOptions()
    client = OllamaClient(opts)

    if not await client.is_ready():
        print("ERROR: Ollama is not running. Start it with: ollama serve")
        await client.aclose()
        return

    # The full system-prompt.md is 44K chars — too large for a local 14B model to
    # process in reasonable time. The RAG pipeline injects only relevant sections;
    # for the CLI we use a compact prompt.
    system_prompt = (
        "You are a local AI coding assistant specialising in C#, ASP.NET Core, "
        "Entity Framework, React, TypeScript, Node.js, and Python. "
        "Be concise, accurate, and include code examples when helpful."
    )

    registry = ToolRegistry([], max_depth=AgentOptions().max_tool_call_depth)
    agent = AgentLoop(
        client=client,
        registry=registry,
        options=AgentOptions(),
        system_prompt=system_prompt,
    )

    print(f"\nModel : {opts.model_name}")
    print(f"Query : {message}")
    print("-" * 60)

    async for token in agent.run(message):
        print(token, end="", flush=True)

    print("\n" + "-" * 60)
    await client.aclose()


async def interactive() -> None:
    print("Local AI Agent — type 'exit' or Ctrl+C to quit\n")
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            break
        await ask(message)
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(ask(" ".join(sys.argv[1:])))
    else:
        asyncio.run(interactive())
