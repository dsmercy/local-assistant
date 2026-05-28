# Phase 07 — Fine-Tuning Checklist (Optional)

> Reference: `agent-instructions/phases/phase-07-finetune.md`
> This phase requires a CUDA GPU. Skip if no GPU is available.

---

## Pre-flight: GPU check

```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

- [ ] `CUDA: True`
- [ ] GPU name prints (not `none`)
- [ ] GPU has ≥ 16 GB VRAM for 14b model (check: `nvidia-smi`)

---

## Step 1 — Finetune venv & dependencies

```bash
python -m venv .venv-finetune
source .venv-finetune/bin/activate
pip install "unsloth[cu121]" trl datasets transformers
python -c "from unsloth import FastLanguageModel; print('Unsloth OK')"
```

- [ ] Unsloth installs without error
- [ ] `from unsloth import FastLanguageModel` prints `Unsloth OK`

---

## Step 2 — Training data

```bash
wc -l data/training.jsonl
head -1 data/training.jsonl | python3 -m json.tool
```

- [ ] At least 500 lines in `data/training.jsonl`
- [ ] First line is valid JSON with a `"text"` key
- [ ] Text value uses Qwen chat template (`<|im_start|>user\n...<|im_end|>`)

**Data quality check — no secrets:**
```bash
grep -i "password\|api_key\|secret\|token\|bearer" data/training.jsonl | wc -l
```
- [ ] Output is `0` — no sensitive data in training set

---

## Step 3 — Run fine-tuning

```bash
python scripts/finetune.py 2>&1 | tee finetune.log
```

- [ ] Training starts without error
- [ ] Loss decreases over first 50 steps (check `finetune.log`)
- [ ] Training completes (or is stopped early intentionally)
- [ ] `lora_output/` directory created
- [ ] GGUF file created: `ls my-qwen-coder-Q4_K_M.gguf`

---

## Step 4 — Import into Ollama

```bash
ollama create my-coder -f modelfiles/Modelfile.custom-coder
ollama list | grep my-coder
```

- [ ] `my-coder` appears in `ollama list`
- [ ] `ollama run my-coder "Write a C# record type for an Order"` — responds correctly

---

## Step 5 — Update environment

```bash
# Edit .env
grep OLLAMA_MODEL_NAME .env
```

- [ ] `OLLAMA_MODEL_NAME=my-coder` set in `.env`
- [ ] `make serve` starts without error using the new model
- [ ] Continue.dev shows `my-coder` as available model

---

## Step 6 — Regression check

```bash
# Run full test suite with the fine-tuned model
OLLAMA_MODEL_NAME=my-coder pytest --tb=short -q
```

- [ ] All tests still pass with the fine-tuned model
- [ ] Streaming confirmed working

---

## Gitignore check

```bash
git check-ignore lora_output/ my-qwen-coder-Q4_K_M.gguf data/training.jsonl
```

- [ ] All three are git-ignored (each line prints the path)

---

## Phase 07 EXIT GATE ✓

- [ ] `my-coder` appears in `ollama list`
- [ ] Model responds correctly to a coding prompt
- [ ] Full test suite passes with fine-tuned model
- [ ] Training data has no secrets (grep confirms)
- [ ] `lora_output/`, `*.gguf`, `data/training.jsonl` all in `.gitignore`
- [ ] Published binary sizes (if distributing) documented in README
