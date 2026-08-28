# -*- coding: utf-8 -*-
"""Generate the AgeixAISOC architecture diagram PNG."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BUILD_DIR, "architecture.png")

BG = "#0f172a"
BOX = "#1e293b"
EDGE = "#06b6d4"
TXT = "#e2e8f0"
RED = "#ef4444"
GREEN = "#22c55e"
AMBER = "#f59e0b"

fig, ax = plt.subplots(figsize=(16, 6.4), dpi=160)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 34)
ax.axis("off")


def box(x, y, w, h, label, sub="", edge=EDGE, fs=11):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35",
                       fc=BOX, ec=edge, lw=2)
    ax.add_patch(p)
    if sub:
        ax.text(x + w / 2, y + h * 0.66, label, ha="center", va="center",
                color=TXT, fontsize=fs, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                color="#94a3b8", fontsize=fs - 3)
    else:
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                color=TXT, fontsize=fs, fontweight="bold")


def arrow(x1, y1, x2, y2, color=TXT, style="-|>", ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=18, color=color, lw=2, linestyle=ls)
    ax.add_patch(a)


# Title
ax.text(50, 32.3, "AgeixAISOC  -  AI-Orchestrated Cyber Defense Loop",
        ha="center", va="center", color=TXT, fontsize=15, fontweight="bold")

# Row of main pipeline
box(1, 20, 13, 8, "Kali Linux", "Nmap / Hydra attacks\nvia SSH bridge", edge=RED)
box(17, 20, 14, 8, "Wazuh SIEM", "custom webhook\nalerts level 7+", edge=AMBER)
box(34, 20, 15, 8, "FastAPI Backend", "webhook :8000\nLangGraph orchestrator")
box(52, 20, 16, 8, "Agent Pipeline", "7 CrewAI agents\ncognitive synthesis")
box(71, 20, 13, 8, "Decision Package", "risk score + MITRE\n+ recommendation")
box(87, 20, 12, 8, "HITL Dashboard", "React - WebSocket\nApprove / Reject", edge=GREEN)

arrow(14.2, 24, 16.8, 24, RED)
arrow(31.2, 24, 33.8, 24, AMBER)
arrow(49.2, 24, 51.8, 24)
arrow(68.2, 24, 70.8, 24)
arrow(84.2, 24, 86.8, 24, GREEN)

# SOAR row
box(74, 7, 12, 8, "n8n SOAR", "workflow engine", edge=GREEN)
box(88, 7, 11, 8, "FortiGate", "REST API block", edge=RED)
arrow(93, 19.6, 93.5, 15.4, GREEN)   # dashboard -> n8n
ax.text(96.5, 17.5, "Approve", color=GREEN, fontsize=9, rotation=-90, va="center")
arrow(86.2, 11, 87.8, 11, GREEN)     # n8n -> fortigate

# fallback arrow
a = FancyArrowPatch((80, 15.2), (90.5, 6.6), arrowstyle="-|>", mutation_scale=14,
                    color="#f59e0b", lw=1.6, linestyle="dashed")
ax.add_patch(a)
ax.text(83.5, 10.0, "fallback:\ndirect API call", color="#f59e0b", fontsize=8,
        ha="center", va="top")

# RAG memory
box(40, 7, 16, 8, "ChromaDB RAG Memory", "learned decisions\nsuppress FP patterns",
    edge="#a78bfa")
arrow(48, 15.2, 51, 19.6, "#a78bfa")     # memory feeds pipeline
arrow(58.5, 19.6, 54.5, 15.4, "#a78bfa") # decisions saved back
ax.text(62.5, 17.4, "recall", color="#a78bfa", fontsize=8)
ax.text(43.5, 17.4, "store", color="#a78bfa", fontsize=8)

# Audit trail
box(22, 7, 14, 8, "Audit Trail", "every decision logged")
arrow(29, 15.2, 36.5, 19.6)

# Reject loop label
ax.text(60, 30.6, "Reject -> decision closed as False Positive -> stored in RAG for future auto-suppression",
        ha="center", color="#94a3b8", fontsize=9, style="italic")

plt.tight_layout()
plt.savefig(OUT, facecolor=BG, bbox_inches="tight")
print("[OK]", OUT)
