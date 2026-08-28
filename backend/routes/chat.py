"""Master Brain Chat — Live AI assistant with RAG context from all knowledge bases.

Uses Ollama (llama3.1) for LLM generation + ChromaDB RAG for context retrieval.
The assistant can search alerts, incidents, MITRE techniques, CVEs, threat intel,
compliance mappings, and CMDB assets — all from a single chat interface.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

try:
    from config import settings
    from state import pending_decisions
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.config import settings
    from backend.state import pending_decisions
    from backend.rag_engine.rag_server import rag_server

logger = logging.getLogger("ageixaisoc.routes.chat")
router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


SYSTEM_PROMPT = """You are AgeixAI Master Brain, the central AI assistant for the AgeixAISOC Security Operations Center platform.

You have access to real-time SOC data including:
- Active alerts and pending HITL decisions
- MITRE ATT&CK technique descriptions (from RAG)
- Past incident reports (from RAG)
- Threat intelligence feeds (Feodo Tracker C2 IPs)
- CVE database (NVD lookups)
- Sigma detection rules
- CMDB asset inventory
- Compliance mappings (NIST CSF / ISO 27001)

When the user asks about threats, alerts, or security topics:
1. Use the provided RAG context to give accurate, evidence-based answers
2. Reference specific MITRE technique IDs, CVE IDs, or alert IDs when relevant
3. If asked to block an IP or take SOAR action, explain that it requires HITL approval
4. Be concise but thorough — SOC analysts need quick, actionable answers

If the RAG context is empty or irrelevant, use your general security knowledge but note that no specific SOC data was found.

Always respond in the same language the user is speaking (English or Arabic)."""


@router.post("/api/chat")
async def master_brain_chat(msg: ChatMessage):
    """Live chat with the Master Brain AI — RAG-augmented responses from Ollama."""
    
    # ── Step 1: Search RAG knowledge bases for relevant context ──
    rag_context = []
    rag_sources = []
    try:
        results = rag_server.search(msg.message, top_k=5)
        for r in results:
            meta = r.get("metadata", {})
            kb = meta.get("kb", "unknown")
            text = r.get("text", "")[:500]
            rag_context.append(f"[{kb}] {text}")
            rag_sources.append({
                "kb": kb,
                "text": text[:200],
                "score": r.get("score", 0),
            })
    except Exception as e:
        logger.warning(f"RAG search failed for chat: {e}")

    # ── Step 2: Gather live SOC context (alerts, metrics) ──
    live_context = []
    try:
        alert_count = len(pending_decisions)
        pending = sum(1 for d in pending_decisions.values() if d.get("status") == "pending")
        live_context.append(f"Active alerts: {alert_count}, Pending HITL decisions: {pending}")
        
        # Add recent alert summaries
        recent = list(pending_decisions.values())[-3:]
        for a in recent:
            live_context.append(
                f"Alert {a.get('alert_id', '?')}: {a.get('threat_analysis', {}).get('summary', 'N/A')[:100]} "
                f"| Risk: {a.get('risk_level', '?')} | MITRE: {a.get('mitre_id', '?')}"
            )
    except Exception as e:
        logger.warning(f"Live context gather failed: {e}")

    # ── Step 3: Build the full prompt for Ollama ──
    context_block = ""
    if rag_context:
        context_block += "\n\n--- RAG Knowledge Base Context ---\n" + "\n\n".join(rag_context)
    if live_context:
        context_block += "\n\n--- Live SOC Status ---\n" + "\n".join(live_context)

    # Build conversation history
    history_block = ""
    if msg.history:
        history_block = "\n\n--- Conversation History ---\n"
        for h in msg.history[-5:]:  # last 5 messages
            role = h.get("role", "user")
            content = h.get("content", "")
            history_block += f"{role}: {content}\n"

    user_prompt = f"""{SYSTEM_PROMPT}

{context_block}
{history_block}

User question: {msg.message}

Provide a helpful, accurate answer based on the available context. If you reference specific data, mention which knowledge base it came from."""

    # ── Step 4: Query Ollama ──
    answer = ""
    model_used = settings.OLLAMA_MODEL_GENERAL
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/v1/chat/completions",
                json={
                    "model": model_used,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"Master Brain chat response generated ({len(answer)} chars)")
    except Exception as e:
        logger.error(f"Ollama chat failed: {e}")
        answer = f"I couldn't reach the LLM backend (Ollama). Error: {str(e)[:100]}. Please ensure Ollama is running on {settings.OLLAMA_BASE_URL}."

    return {
        "answer": answer,
        "model": model_used,
        "rag_sources": rag_sources,
        "rag_context_count": len(rag_context),
        "live_context_count": len(live_context),
        "timestamp": datetime.utcnow().isoformat(),
        "label": "🟢 Live — Ollama LLM + RAG knowledge bases",
    }


@router.get("/api/chat/history")
async def chat_history():
    """Return chat history placeholder — chat history is client-side for now."""
    return {
        "history": [],
        "message": "Chat history is stored client-side in the browser.",
        "timestamp": datetime.utcnow().isoformat(),
    }