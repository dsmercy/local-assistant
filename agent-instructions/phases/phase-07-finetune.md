# Phase 07 — Fine-Tuning with Unsloth (Optional)

## Phase goal
Fine-tune Qwen2.5-Coder on your own codebase using LoRA, export as GGUF,
and import back into Ollama as a named custom model.

## Entry criteria
- [ ] Phase 06 exit gates passed
- [ ] CUDA GPU available: `python -c "import torch; print(torch.cuda.is_available())"`
- [ ] At minimum 500 training examples prepared in JSONL format

## Install (separate venv recommended)

```bash
python -m venv .venv-finetune && source .venv-finetune/bin/activate
pip install "unsloth[cu121]" trl datasets transformers
```

## Dataset format

Each line in `data/training.jsonl`:
```json
{"text": "<|im_start|>user\nWrite a Python function to read a file safely\n<|im_end|>\n<|im_start|>assistant\nfrom pathlib import Path\n\ndef read_file(path: Path) -> str:\n    ...\n<|im_end|>"}
```

Rules:
- Use Qwen's `<|im_start|>` / `<|im_end|>` chat template exactly
- Include `role: user` and `role: assistant` turns
- Aim for 500–2000 examples for meaningful improvement
- Never include secrets, tokens, passwords, or PII in training data

## Fine-tuning script — `scripts/finetune.py`

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import torch

MODEL_NAME = "unsloth/Qwen2.5-Coder-7B-Instruct"
MAX_SEQ_LEN = 4096
OUTPUT_DIR = "./lora_output"

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
)

dataset = load_dataset("json", data_files="data/training.jsonl", split="train")

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    args=TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        save_steps=100,
        warmup_ratio=0.03,
    ),
)
trainer.train()

# Export to GGUF (Q4_K_M = best quality/size tradeoff)
model.save_pretrained_gguf("./my-qwen-coder", tokenizer, quantization_method="q4_k_m")
print("Exported: ./my-qwen-coder-Q4_K_M.gguf")
```

## Import into Ollama

**`modelfiles/Modelfile.custom-coder`:**
```
FROM ./my-qwen-coder-Q4_K_M.gguf

SYSTEM """
You are a specialized coding assistant fine-tuned on this project's codebase.
Follow the standards and conventions you have learned.
Always use full type annotations. Use structlog for logging.
Never hardcode secrets.
"""

PARAMETER temperature 0.1
PARAMETER num_ctx 32768
```

```bash
ollama create my-coder -f modelfiles/Modelfile.custom-coder
ollama run my-coder "Write a Python async function to read a file safely"

# Update .env to use the fine-tuned model
OLLAMA_MODEL_NAME=my-coder
```

## Update Continue.dev config

Add to `~/.continue/config.json` `models` array:
```json
{
  "title": "My Fine-tuned Coder",
  "provider": "ollama",
  "model": "my-coder",
  "apiBase": "http://localhost:11434"
}
```

## Validation gate

```bash
# Test the fine-tuned model responds correctly
ollama run my-coder "Write a Pydantic v2 model for a user"

# Verify it appears in Ollama
ollama list | grep my-coder

# Run the test suite with the new model
OLLAMA_MODEL_NAME=my-coder pytest -v
```

## Exit criteria

- [ ] `my-coder` appears in `ollama list`
- [ ] `my-coder` responds to a basic Python prompt correctly
- [ ] `OLLAMA_MODEL_NAME=my-coder` works in `.env` — no code changes needed
- [ ] Continue.dev shows "My Fine-tuned Coder" as a selectable model
- [ ] Training data has no secrets, tokens, or PII (manual review)

## What not to do
- Do not use `shell=True` anywhere in the fine-tuning pipeline
- Do not commit `lora_output/` or `*.gguf` files to git (add to `.gitignore`)
- Do not commit `data/training.jsonl` if it contains proprietary code
- Do not add `--resume-from-checkpoint` without verifying checkpoint integrity
