"""RAG API endpoints for knowledge base stats, search, and ingestion."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from rag_engine.rag_server import rag_server
    from rag_engine.knowledge_base import get_kb_names, get_kb_metadata
except ImportError:
    from backend.rag_engine.rag_server import rag_server
    from backend.rag_engine.knowledge_base import get_kb_names, get_kb_metadata


logger = logging.getLogger("ageixaisoc.routes.rag")

router = APIRouter()


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    kb_filter: Optional[str] = None


class RAGIngestRequest(BaseModel):
    text: str
    kb_name: str = "learned_decisions"
    metadata: Optional[Dict[str, Any]] = {}


@router.get("/api/rag/stats")
async def rag_stats():
    kbs = rag_server.list_knowledge_bases()
    doc_count = rag_server.count()
    return {
        "collections": kbs,
        "total_documents": doc_count,
        "provider": rag_server.provider,
        "chroma_ready": rag_server._initialized not in (None, False),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/rag/search")
async def rag_search(request: RAGSearchRequest):
    results = rag_server.search(request.query, top_k=request.top_k)
    kb_info = get_kb_metadata(request.kb_filter) if request.kb_filter else None
    return {
        "query": request.query,
        "results": results,
        "total": len(results),
        "kb_filter": request.kb_filter,
        "kb_info": kb_info,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/rag/ingest")
async def rag_ingest(request: RAGIngestRequest):
    if request.kb_name not in get_kb_names():
        raise HTTPException(status_code=400, detail=f"Unknown KB: {request.kb_name}. Available: {get_kb_names()}")

    metadata = {**request.metadata, "kb": request.kb_name, "ingested_at": datetime.utcnow().isoformat()}
    doc_id = rag_server.insert(request.text, metadata=metadata)

    if doc_id is None:
        raise HTTPException(status_code=500, detail="Failed to ingest document")

    return {"status": "ok", "doc_id": doc_id, "kb_name": request.kb_name, "timestamp": datetime.utcnow().isoformat()}
