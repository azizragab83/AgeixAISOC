"""
AgeixAISOC Core Brain — Local LLM Fine-tuning with Unsloth (QLoRA)
=================================================================
Fine-tunes Llama-3-8B-Instruct (4-bit) on a synthetic SOC alert dataset
using QLoRA.  Runs on a single GPU with >= 16 GB VRAM.

Install dependencies (Python 3.10+ recommended):
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install bitsandbytes trl transformers accelerate datasets

Usage:
    python train_soc_brain.py
"""

import json
import os
from typing import Iterator

import torch
from datasets import Dataset, load_dataset
from transformers import TrainingArguments, BitsAndBytesConfig
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template, standardize_sharegpt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_MODEL = "unsloth/llama-3-8b-Instruct-bnb-4bit"
DATA_PATH = "soc_training_data.jsonl"
OUTPUT_DIR = "soc-brain-model"

MAX_SEQ_LENGTH = 2048
DTYPE = None  # Auto-detect (float16 / bfloat16)
LOAD_IN_4BIT = True

# LoRA hyper-parameters
LORA_R = 16
LORA_ALPHA = 16
LORA_DROPOUT = 0
TARGET_MODULES = [  # all linear layers
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
    "embed_tokens", "lm_head",
]

# Training hyper-parameters
BATCH_SIZE = 2         # Per-device — 16 GB VRAM can handle 2-4
GRADIENT_ACCUM = 4     # Effective batch = BATCH_SIZE * GRADIENT_ACCUM = 8
LR = 2e-4
EPOCHS = 3
WARMUP_STEPS = 5
LOGGING_STEPS = 10
SAVE_STEPS = 50
SAVE_TOTAL_LIMIT = 2   # Keep only the 2 most recent checkpoints

# ---------------------------------------------------------------------------
# 1.  Mock dataset generator (run once to create soc_training_data.jsonl)
# ---------------------------------------------------------------------------

MOCK_EXAMPLES = [
    {
        "instruction": (
            "You are the Core AI Brain of the AgeixAISOC platform. "
            "Analyse the following security alert and OSINT context. "
            "Output a JSON object with keys: threat_analysis (2-3 sentences) "
            "and recommended_action (1-2 sentences)."
        ),
        "input": (
            "Alert: 47 failed RDP logins from IP 185.130.5.23 in 3 minutes, "
            "then a successful login from the same IP. "
            "OSINT: IP 185.130.5.23 appears on AlienVault OTX pulse "
            "'Emotet C2 Infrastructure — January 2026', tagged as C2 beacon."
        ),
        "output": json.dumps({
            "threat_analysis": (
                "The sequence of 47 failed RDP logins followed by a successful "
                "authentication strongly indicates a brute-force compromise. "
                "The source IP (185.130.5.23) is actively listed on AlienVault OTX "
                "as an Emotet C2 beacon, elevating this from a routine brute-force "
                "event to a probable initial-access-for-ransomware scenario."
            ),
            "recommended_action": (
                "Immediately isolate the compromised host from the network, revoke "
                "any active RDP sessions from 185.130.5.23, and initiate the "
                "ransomware incident response playbook (IRP-003)."
            ),
        }),
    },
    {
        "instruction": (
            "You are the Core AI Brain of the AgeixAISOC platform. "
            "Analyse the following security alert and OSINT context. "
            "Output a JSON object with keys: threat_analysis (2-3 sentences) "
            "and recommended_action (1-2 sentences)."
        ),
        "input": (
            "Alert: DNS query volume for 'update-package.tk' spiked to "
            "1 200 requests/hour from 3 internal hosts. "
            "OSINT: Domain 'update-package.tk' is 3 days old and registered "
            "to a known phishing actor group tracked by CISA."
        ),
        "output": json.dumps({
            "threat_analysis": (
                "A sudden DNS spike to a newly registered .tk domain from "
                "multiple internal hosts is characteristic of malware beaconing. "
                "CISA attribution links this domain to a phishing actor group, "
                "suggesting the hosts may be part of a botnet under active "
                "C2 communication."
            ),
            "recommended_action": (
                "Block domain 'update-package.tk' at the DNS sinkhole and egress "
                "proxy. Isolate the three affected hosts for forensic imaging and "
                "scan for additional C2 infrastructure using the IOC feed from CISA."
            ),
        }),
    },
    {
        "instruction": (
            "You are the Core AI Brain of the AgeixAISOC platform. "
            "Analyse the following security alert and OSINT context. "
            "Output a JSON object with keys: threat_analysis (2-3 sentences) "
            "and recommended_action (1-2 sentences)."
        ),
        "input": (
            "Alert: File 'invoice_jan2026.exe' written to C:\\Users\\public\\ "
            "on host SRV-045. Windows Defender flagged it as 'Trojan:Win32/"
            "VoidCrypt!ml'.  OSINT: VoidCrypt is a new ransomware variant "
            "using intermittent encryption. First observed in December 2025."
        ),
        "output": json.dumps({
            "threat_analysis": (
                "A trojan downloader for the VoidCrypt ransomware family was "
                "written to disk but Defender has not been able to remove it. "
                "Given VoidCrypt's intermittent-encryption technique, traditional "
                "file-recovery may be partially ineffective if encryption proceeds."
            ),
            "recommended_action": (
                "Disconnect SRV-045 from the network immediately. Verify whether "
                "the file executed — if so, initiate IRP-004 (Ransomware Response) "
                "and capture a memory image before powering down."
            ),
        }),
    },
    {
        "instruction": (
            "You are the Core AI Brain of the AgeixAISOC platform. "
            "Analyse the following security alert and OSINT context. "
            "Output a JSON object with keys: threat_analysis (2-3 sentences) "
            "and recommended_action (1-2 sentences)."
        ),
        "input": (
            "Alert: Outbound connection from DB-01 to unusual external IP "
            "203.0.113.55 on port 4444.  No database replication jobs were "
            "scheduled.  OSINT: 203.0.113.55 is listed on Shodan as a 'Mirai "
            "C2 server' and reported by 3 other threat feeds in the last 24 hours."
        ),
        "output": json.dumps({
            "threat_analysis": (
                "A production database server initiated an outbound connection "
                "to a known Mirai C2 server on a non-standard port. This is "
                "highly anomalous — database servers should not initiate "
                "outbound connections over port 4444. The host may be running "
                "a Mirai variant or similar IoT malware."
            ),
            "recommended_action": (
                "Kill the outbound connection and block 203.0.113.55 at the "
                "firewall. Scan DB-01 for Mirai-related processes and check "
                "for any unauthorised SSH keys or cron jobs."
            ),
        }),
    },
    {
        "instruction": (
            "You are the Core AI Brain of the AgeixAISOC platform. "
            "Analyse the following security alert and OSINT context. "
            "Output a JSON object with keys: threat_analysis (2-3 sentences) "
            "and recommended_action (1-2 sentences)."
        ),
        "input": (
            "Alert:  CVE-2026-3312 (SQLi in internal-app) detected by WAF "
            "— 15 attempts in 2 seconds from IP 198.51.100.77.  "
            "OSINT: IP 198.51.100.77 belongs to a known scanning-as-a-service "
            "platform used by penetration testers and threat actors alike."
        ),
        "output": json.dumps({
            "threat_analysis": (
                "The WAF is correctly blocking SQL injection attempts targeting "
                "CVE-2026-3312, but the source IP is associated with a "
                "scanning service that could indicate automated recon by a "
                "threat actor. 15 attempts in 2 seconds suggests a scripted "
                "attack rather than manual probing."
            ),
            "recommended_action": (
                "Rate-limit or block 198.51.100.77 at the edge firewall. "
                "Prioritise the CVE-2026-3312 patch within the next 4 hours "
                "since the WAF is the only control between the attacker and "
                "the application."
            ),
        }),
    },
]


def generate_mock_dataset(path: str) -> None:
    """Write MOCK_EXAMPLES to a JSONL file for training."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in MOCK_EXAMPLES:
            f.write(json.dumps(ex) + "\n")
    print(f"[✓] Mock dataset written to {path}  ({len(MOCK_EXAMPLES)} examples)")


# ---------------------------------------------------------------------------
# 2.  Dataset loader
# ---------------------------------------------------------------------------

def load_soc_dataset(path: str) -> Dataset:
    """
    Read a JSONL file where each line is:
        {
            "instruction": "...",
            "input": "...",
            "output": "..."
        }

    Returns a Hugging Face Dataset formatted for chat template training.
    """
    if not os.path.exists(path):
        print(f"[!] {path} not found — generating mock dataset.")
        generate_mock_dataset(path)

    dataset = load_dataset("json", data_files=path, split="train")

    def format_chat(example: dict) -> dict:
        return {
            "conversations": [
                {"from": "user", "value": example["instruction"] + "\n\n" + example["input"]},
                {"from": "assistant", "value": example["output"]},
            ]
        }

    dataset = dataset.map(format_chat, remove_columns=dataset.column_names)
    return dataset


# ---------------------------------------------------------------------------
# 3.  Load base model with 4-bit QLoRA
# ---------------------------------------------------------------------------

def load_base_model():
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=LOAD_IN_4BIT,
        device_map="auto",
    )
    return model, tokenizer


# ---------------------------------------------------------------------------
# 4.  Apply LoRA adapters
# ---------------------------------------------------------------------------

def apply_lora(model):
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        use_gradient_checkpointing="unsloth",
        use_rslora=False,
        loftq_config=None,
    )
    return model


# ---------------------------------------------------------------------------
# 5.  Main training routine
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AgeixAISOC Core Brain — Fine-tuning Pipeline")
    print("=" * 60)

    # ---- Load dataset ----
    print(f"\n[1/5] Loading dataset from {DATA_PATH}")
    dataset = load_soc_dataset(DATA_PATH)
    print(f"     Dataset size: {len(dataset)} examples")

    # ---- Load base model ----
    print(f"\n[2/5] Loading base model: {BASE_MODEL}")
    model, tokenizer = load_base_model()
    print("     Base model loaded.")

    # ---- Apply LoRA ----
    print(f"\n[3/5] Applying LoRA (r={LORA_R}, alpha={LORA_ALPHA})")
    model = apply_lora(model)
    model.print_trainable_parameters()
    print("     LoRA adapters attached.")

    # ---- Apply chat template ----
    print(f"\n[4/5] Applying chat template")
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="llama-3",
        mapping={
            "role": "from",
            "content": "value",
            "user": "user",
            "assistant": "assistant",
        },
    )
    dataset = standardize_sharegpt(dataset)

    # ---- Training arguments ----
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
        save_steps=SAVE_STEPS,
        save_total_limit=SAVE_TOTAL_LIMIT,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
    )

    # ---- Trainer ----
    print(f"\n[5/5] Initialising SFTTrainer & starting training")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        dataset_kwargs={
            "add_special_tokens": False,
        },
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="",
    )

    # ---- GO! ----
    trainer.train()

    # ---- Save final model ----
    print(f"\nSaving fine-tuned model to '{OUTPUT_DIR}' ...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[✓] Model saved to '{OUTPUT_DIR}'")

    # Also save in GGUF / merged-16bit format for inference
    print("\nSaving merged 16-bit weights (for production inference) ...")
    model.save_pretrained_merged(OUTPUT_DIR + "-merged", tokenizer, save_method="merged_16bit")
    print(f"[✓] Merged model saved to '{OUTPUT_DIR}-merged'")

    # Save to GGUF for Ollama (4-bit and 8-bit quantized)
    print("\nSaving GGUF quantized formats (for Ollama) ...")
    model.save_pretrained_gguf("soc_brain_model_gguf", tokenizer, quantization_method="q4_k_m")
    print("[✓] GGUF q4_k_m saved to 'soc_brain_model_gguf/' (4-bit, recommended for 16GB VRAM)")
    model.save_pretrained_gguf("soc_brain_model_gguf", tokenizer, quantization_method="q8_0")
    print("[✓] GGUF q8_0 saved to 'soc_brain_model_gguf/' (8-bit, higher quality at ~8GB)")


if __name__ == "__main__":
    main()
