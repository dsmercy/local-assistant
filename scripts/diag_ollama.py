import asyncio
import httpx
import time

ENDPOINT = "http://127.0.0.1:11434"
MODEL = "qwen2.5-coder:7b"


async def run() -> None:
    async with httpx.AsyncClient(timeout=120) as c:
        for prompt in ["Say hi", "Say hi in 5 words"]:
            t = time.time()
            r = await c.post(
                f"{ENDPOINT}/api/chat",
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
            )
            d = r.json()
            elapsed = time.time() - t
            eval_count = d.get("eval_count", 0)
            eval_ns = d.get("eval_duration", 1)
            tok_s = eval_count / max(eval_ns / 1e9, 0.001)
            content = d.get("message", {}).get("content", "")
            print(f'Prompt: "{prompt}"')
            print(f"  Time   : {elapsed:.1f}s")
            print(f"  Tokens : {eval_count}  ({tok_s:.1f} tok/s)")
            print(f"  Reply  : {content[:80]}")
            print()

        # GPU/CPU check
        r2 = await c.get(f"{ENDPOINT}/api/ps")
        for m in r2.json().get("models", []):
            size_vram = m.get("size_vram", 0)
            size = m.get("size", 1)
            gpu_pct = round(size_vram / max(size, 1) * 100)
            print(f"Model in memory: {m.get('name')}  GPU: {gpu_pct}%  CPU: {100 - gpu_pct}%")


asyncio.run(run())
