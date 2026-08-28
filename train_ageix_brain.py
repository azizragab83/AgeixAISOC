from unsloth import FastLanguageModel
"""
AgeixAISOC — Fine-tune a local model using Unsloth for the SOC platform.
=======================================================================
Fine-tunes Llama-3-8B-Instruct (4-bit QLoRA) on SOC alert analysis data.
Fits in 16 GB VRAM.  Saves as local weights + 8-bit GGUF for Ollama.

Requirements (Python 3.10+):
    pip install torch --index-url https://download.pytorch.org/whl/cu124
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install bitsandbytes trl transformers accelerate datasets

Usage:
    1. Place your SOC scenarios in soc_training_data.jsonl (one JSON per line):
       {"instruction": "Analyze alert: ...", "output": "Threat: ... MITRE: ..."}
    2. Run:  python train_ageix_brain.py
    3. After training, register the GGUF in Ollama:
       ollama create ageix-brain-custom -f ./ageix_finetuned_model/Modelfile
"""

import json
import os
from typing import Iterator

import torch
from datasets import Dataset, load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template, standardize_sharegpt


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration  —  tweak these values before running
# ═══════════════════════════════════════════════════════════════════════════════

# Base model to fine-tune.
# Llama-3-8B:     "unsloth/llama-3-8b-Instruct-bnb-4bit"
# Qwen2.5-7B:     "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
BASE_MODEL = "unsloth/llama-3-8b-Instruct-bnb-4bit"

# Path to your training data (JSONL, one JSON object per line)
DATA_PATH = "soc_training_data.jsonl"

# Where to save the final model
OUTPUT_DIR = "ageix_finetuned_model"

# Sequence length — 2048 fits comfortably in 16 GB VRAM
MAX_SEQ_LENGTH = 2048

# 4-bit QLoRA quantization
DTYPE = None          # Auto-detect: float16 or bfloat16
LOAD_IN_4BIT = True

# ── LoRA hyper-parameters ────────────────────────────────────────────────────
# r=16, alpha=16 targets the attention projection matrices only.
# This is the standard QLoRA recipe: keeps memory low while adapting the
# model's core reasoning capabilities for SOC alert analysis.
LORA_R = 16
LORA_ALPHA = 16
LORA_DROPOUT = 0
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]

# ── Training hyper-parameters ────────────────────────────────────────────────
BATCH_SIZE = 2          # Per-device batch size (2 fits 16 GB at seq_len=2048)
GRADIENT_ACCUM = 4      # Effective batch = BATCH_SIZE * GRADIENT_ACCUM = 8
LR = 2e-4
EPOCHS = 3
WARMUP_STEPS = 5
LOGGING_STEPS = 10
SAVE_TOTAL_LIMIT = 2


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Dataset loader
# ═══════════════════════════════════════════════════════════════════════════════

def load_soc_dataset(path: str) -> Dataset:
    """
    Read soc_training_data.jsonl where each line is:
        {"instruction": "Analyze alert: ...", "output": "Threat: ... MITRE: ..."}

    Converts to ShareGPT conversation format for Unsloth's chat template.

    If the file does not exist, generates a small mock dataset so you can
    test the pipeline end-to-end before preparing real data.
    """
    if not os.path.exists(path):
        print(f"[!] {path} not found — generating mock dataset for testing.")
        _generate_mock_dataset(path)

    dataset = load_dataset("json", data_files=path, split="train")

    def to_sharegpt(example: dict) -> dict:
        # If the JSONL has "instruction" + "output" (no "input" field).
        # If "input" exists, append it after the instruction.
        user_msg = example["instruction"]
        if example.get("input"):
            user_msg += "\n\n" + example["input"]
        return {
            "conversations": [
                {"from": "user",      "value": user_msg},
                {"from": "assistant", "value": example["output"]},
            ]
        }

    dataset = dataset.map(to_sharegpt, remove_columns=dataset.column_names)
    return dataset


def _generate_mock_dataset(path: str) -> None:
    """Write 12 synthetic SOC scenarios for testing."""
    mock = [
        {
            "instruction": "Analyze alert: Multiple failed logins followed by success from IP 5.6.7.8. OS: Windows.",
            "output": "Threat: Brute Force Success. MITRE: T1110.002. Risk: 85. Action: Isolate host and reset credentials.",
        },
        {
            "instruction": "Analyze alert: DNS query surge to 'evil-update.tk' from 3 internal hosts. OS: Linux.",
            "output": "Threat: C2 Beaconing. MITRE: T1071.004. Risk: 90. Action: Block domain at DNS sinkhole. Isolate hosts.",
        },
        {
            "instruction": "Analyze alert: File 'invoice.exe' written to C:\\Users\\Public on host SRV-045. Antivirus: Trojan detected.",
            "output": "Threat: Malware Drop. MITRE: T1204.002. Risk: 92. Action: Isolate SRV-045. Capture memory image.",
        },
        {
            "instruction": "Analyze alert: Outbound connection from DB-01 to 203.0.113.55:4444. No scheduled jobs.",
            "output": "Threat: C2 Connection. MITRE: T1572. Risk: 80. Action: Kill connection. Block IP. Scan DB-01.",
        },
        {
            "instruction": "Analyze alert: WAF detected 15 SQLi attempts from IP 198.51.100.77 targeting internal-app.",
            "output": "Threat: Web Application Attack. MITRE: T1190. Risk: 70. Action: Block IP at WAF. Prioritize patch for CVE.",
        },
        {
            "instruction": "Analyze alert: User john.doe enabled 10 times in 5 minutes. Source: VPN gateway.",
            "output": "Threat: Account Replay / Session Hijacking. MITRE: T1528. Risk: 88. Action: Disable VPN session. Force password reset.",
        },
        {
            "instruction": "Analyze alert: LSASS access attempt from non-standard process on DC-01. Process: mallory.exe.",
            "output": "Threat: Credential Dumping. MITRE: T1003.001. Risk: 95. Action: Isolate DC-01. Investigate mallory.exe origin.",
        },
        {
            "instruction": "Analyze alert: New scheduled task 'SysCheck' created on WORKSTATION-23. Runs powershell -enc ...",
            "output": "Threat: Persistence via Scheduled Task. MITRE: T1053.005. Risk: 75. Action: Disable task. Review parent process.",
        },
        {
            "instruction": "Analyze alert: SMB enumeration from 10.0.30.50 against DC-01 — 5000+ requests in 2 minutes.",
            "output": "Threat: Reconnaissance. MITRE: T1049. Risk: 55. Action: Investigate source. Check for other lateral movement.",
        },
        {
            "instruction": "Analyze alert: Powershell encoded command executed on WS-022. ScriptBlock: -enc CAB...",
            "output": "Threat: PowerShell Abuse. MITRE: T1059.001. Risk: 85. Action: Isolate WS-022. Review process tree for persistence.",
        },
        {
            "instruction": "Analyze alert: EDR telemetry — svchost.exe making outbound HTTPS to IP known to TrickBot C2.",
            "output": "Threat: C2 Communication / TrickBot. MITRE: T1071.001. Risk: 90. Action: Block C2 IP. Isolate host. Scan for TrickBot modules.",
        },
        {
            "instruction": "Analyze alert: 200 phishing emails reported in 1 hour. Attachment: 'Q4_Report.xlsm' with malicious macro.",
            "output": "Threat: Phishing Campaign. MITRE: T1566.001. Risk: 80. Action: Block attachment hash in mail gateway. Notify all recipients.",
        },
    ]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in mock:
            f.write(json.dumps(ex) + "\n")
    print(f"[+] Generated {len(mock)} mock examples in {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Load base model with 4-bit QLoRA
# ═══════════════════════════════════════════════════════════════════════════════

def load_base_model():
    """Load the base model in 4-bit quantized format to fit 16 GB VRAM."""
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=LOAD_IN_4BIT,
        device_map="auto",
    )
    return model, tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Apply LoRA adapters
# ═══════════════════════════════════════════════════════════════════════════════

def apply_lora(model):
    """
    Attach trainable LoRA adapters to the attention projection matrices.
    Only ~0.1% of parameters are trained — the rest stay frozen in 4-bit.
    """
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        use_gradient_checkpointing="unsloth",  # saves ~30% VRAM
        use_rslora=False,
        loftq_config=None,
    )
    return model


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Main training routine
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("AgeixAISOC — Unsloth Fine-tuning Pipeline")
    print("=" * 60)

    # ── Step 1: Load dataset ──────────────────────────────────────────────
    print(f"\n[1/5] Loading dataset from {DATA_PATH}")
    dataset = load_soc_dataset(DATA_PATH)
    print(f"      Dataset size: {len(dataset)} examples")
    print(f"      Example keys: {dataset[0].keys()}")

    # ── Step 2: Load base model ───────────────────────────────────────────
    print(f"\n[2/5] Loading base model: {BASE_MODEL}")
    model, tokenizer = load_base_model()
    print("      Base model loaded successfully.")

    # ── Step 3: Apply LoRA ────────────────────────────────────────────────
    print(f"\n[3/5] Applying LoRA (r={LORA_R}, alpha={LORA_ALPHA})")
    model = apply_lora(model)
    model.print_trainable_parameters()

    # ── Step 4: Apply chat template ───────────────────────────────────────
    print("\n[4/5] Applying chat template for Llama-3 / Qwen2.5")
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="llama-3",  # works for both Llama-3 and Qwen2.5
        mapping={
            "role": "from",
            "content": "value",
            "user": "user",
            "assistant": "assistant",
        },
    )
    dataset = standardize_sharegpt(dataset)

    # ── Training arguments ────────────────────────────────────────────────
    # Key settings for 16 GB VRAM:
    #   - per_device_train_batch_size=2
    #   - max_seq_length=2048
    #   - gradient_accumulation_steps=4  (effective batch = 8)
    #   - fp16 mixed precision (bf16 if supported)
    #   - adamw_8bit optimizer reduces optimizer memory by ~50%
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUM,
        warmup_steps=WARMUP_STEPS,
        num_train_epochs=EPOCHS,
        learning_rate=LR,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=LOGGING_STEPS,
        save_strategy="no",
        save_total_limit=SAVE_TOTAL_LIMIT,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
    )

  # — Step 5: Train —
    print("\n[5/5] Initialising SFTTrainer & starting training")
    print(f"      max_seq_length={MAX_SEQ_LENGTH}  batch_size={BATCH_SIZE}")
    print(f"      epochs={EPOCHS}  lr={LR}  effective_batch={BATCH_SIZE * GRADIENT_ACCUM}")

    def formatting_prompts_func(examples):
        convs = examples["conversations"]
        if isinstance(convs, list) and len(convs) > 0 and isinstance(convs[0], dict):
            return [tokenizer.apply_chat_template(convs, tokenize=False, add_generation_prompt=False)]
        return [
            tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False)
            for convo in convs
        ]

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        dataset_kwargs={
            "add_special_tokens": False,
        },
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
        formatting_func=formatting_prompts_func,
    )

    # — GO! —
    trainer.train()

    # ── Save local weights ─────────────────────────────────────────────────
    print(f"\nSaving fine-tuned model to '{OUTPUT_DIR}' ...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[OK] LoRA adapters saved to '{OUTPUT_DIR}'")

    # ── Save as 8-bit GGUF for Ollama ──────────────────────────────────────
    # After training, you can load this GGUF directly into Ollama:
    #   $ ollama create ageix-brain-custom -f ./{OUTPUT_DIR}/Modelfile
    # The Modelfile is auto-generated alongside the GGUF.
    print("\nExporting to 8-bit GGUF (for Ollama as 'ageix-brain-custom') ...")
    model.save_pretrained_gguf(
        OUTPUT_DIR,
        tokenizer,
        quantization_method="q8_0",
    )
    print(f"[OK] 8-bit GGUF saved to '{OUTPUT_DIR}/'")
    print()

    # ── Instructions for Ollama ────────────────────────────────────────────
    print("=" * 60)
    print("NEXT STEPS — Load into Ollama:")
    print("=" * 60)
    print()
    print("  1. Create the Ollama model:")
    print(f"     ollama create ageix-brain-custom -f {OUTPUT_DIR}/Modelfile")
    print()
    print("  2. Test it:")
    print('     ollama run ageix-brain-custom "Analyze alert: 47 failed RDP logins from IP 185.130.5.23"')
    print()
    print("  3. Use in AgeixAISOC (update llm_config.py):")
    print('     MASTER_BRAIN_MODEL = "ageix-brain-custom"')
    print("=" * 60)


if __name__ == "__main__":
    main()
