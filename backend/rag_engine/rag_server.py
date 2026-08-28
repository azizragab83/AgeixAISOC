"""RAG server using ChromaDB with local Ollama embeddings."""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, List, Optional

try:
    from rag_engine.knowledge_base import get_kb_names, list_knowledge_bases, KNOWLEDGE_BASES
except ImportError:
    from backend.rag_engine.knowledge_base import get_kb_names, list_knowledge_bases, KNOWLEDGE_BASES

try:
    from config import settings as _settings
except ImportError:
    from backend.config import settings as _settings

logger = logging.getLogger(__name__)


def _ollama_base_url() -> str:
    """Resolve the Ollama base URL from settings so it works both locally and
    inside Docker (where Ollama lives on host.docker.internal)."""
    return getattr(_settings, "OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"

CHROMA_DIR = os.path.join(tempfile.gettempdir(), "ageixai_rag")
COLLECTION_NAME = "ageixai_knowledge"


def _get_embedding(text: str) -> List[float]:
    """Get embedding vector from Ollama (nomic-embed-text), fallback to zero vector."""
    import httpx
    payload = {"model": "nomic-embed-text", "prompt": text}
    base = _ollama_base_url().rstrip("/")
    # /api/embed is the modern route; /api/embeddings is the legacy one
    for url in (f"{base}/api/embed", f"{base}/api/embeddings"):
        try:
            resp = httpx.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "embeddings" in data and data["embeddings"]:
                    return data["embeddings"][0]
                if "embedding" in data:
                    return data["embedding"]
        except Exception as e:
            logger.warning(f"Ollama embedding failed ({url}): {e}")
    return [0.0] * 768


class RAGServer:
    """Lightweight RAG server backed by ChromaDB."""

    def __init__(self, provider: str = "chroma"):
        self.provider = provider
        self._collection = None
        self._initialized = False

    def _ensure_client(self):
        if self._initialized:
            return
        try:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(CHROMA_DIR, exist_ok=True)
            client = chromadb.PersistentClient(
                path=CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(f"ChromaDB ready: {CHROMA_DIR}")
        except Exception as e:
            logger.warning(f"ChromaDB init failed, using memory store: {e}")
            self._memory_store = []
            self._initialized = "memory"

    def insert(self, text: str, metadata: Optional[dict] = None):
        self._ensure_client()
        embedding = _get_embedding(text)
        doc_id = f"doc-{hash(text) % 10**8}"

        if self._initialized == "memory":
            self._memory_store.append({"id": doc_id, "text": text, "metadata": metadata or {}})
            return doc_id

        try:
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )
            return doc_id
        except Exception as e:
            logger.error(f"ChromaDB insert failed: {e}")
            return None

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        self._ensure_client()

        if self._initialized == "memory":
            results = sorted(self._memory_store, key=lambda x: -len(set(query.lower().split()) & set(x["text"].lower().split())))[:top_k]
            return [{"id": r["id"], "text": r["text"], "metadata": r["metadata"], "distance": 0.0} for r in results]

        try:
            embedding = _get_embedding(query)
            results = self._collection.query(query_embeddings=[embedding], n_results=top_k)
            documents = []
            for i in range(len(results["ids"][0])):
                documents.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
            return documents
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []

    def search_kb(self, kb: str, query: str, top_k: int = 5) -> List[dict]:
        """Search within a single knowledge base using the metadata 'kb' filter.

        Falls back to keyword scanning in memory-store mode (the memory mode
        cannot meaningfully compute cosine distance, so a conservative
        keyword-overlap is left to the caller).
        """
        self._ensure_client()

        if self._initialized == "memory":
            pool = [r for r in self._memory_store if (r.get("metadata") or {}).get("kb") == kb]
            q_tokens = set(query.lower().split())
            scored = []
            for r in pool:
                text_tokens = set(r["text"].lower().split())
                overlap = len(q_tokens & text_tokens)
                similarity = overlap / len(q_tokens) if q_tokens else 0.0
                scored.append({"id": r["id"], "text": r["text"], "metadata": r["metadata"], "distance": similarity})
            scored.sort(key=lambda x: x["distance"], reverse=True)
            return scored[:top_k]

        try:
            embedding = _get_embedding(query)
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where={"kb": kb},
            )
            documents = []
            for i in range(len(results["ids"][0])):
                documents.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
            return documents
        except Exception as e:
            logger.error(f"ChromaDB search_kb({kb}) failed: {e}")
            return []

    def count(self) -> int:
        self._ensure_client()
        if self._initialized == "memory":
            return len(self._memory_store)
        try:
            return self._collection.count()
        except Exception:
            return 0

    def count_kb(self, kb: str) -> int:
        """Count documents belonging to a specific knowledge base (via metadata filter)."""
        self._ensure_client()
        if self._initialized == "memory":
            return sum(1 for d in self._memory_store if d["metadata"].get("kb") == kb)
        try:
            return len(self._collection.get(where={"kb": kb}, include=[])["ids"])
        except TypeError:
            # Older chromadb: count() has no 'where' support — fall back to get()
            try:
                return len(self._collection.get(include=[])["ids"])
            except Exception:
                return 0
        except Exception:
            return 0

    def list_knowledge_bases(self) -> list:
        return list_knowledge_bases()

    def ingest(self, kb: str, documents: List[dict]) -> List[str]:
        """Ingest a list of documents into a specific knowledge base.
        
        Args:
            kb: Knowledge base name (e.g. 'learned_decisions')
            documents: List of dicts with alert data to ingest
        
        Returns:
            List of document IDs inserted
        """
        doc_ids = []
        for doc in documents:
            text = json.dumps(doc, default=str)
            metadata = {"kb": kb, "ingested_at": datetime.utcnow().isoformat()}
            # Copy select fields into metadata for searchability
            if isinstance(doc, dict):
                for key in ("alert_id", "action", "decision_id"):
                    if key in doc:
                        metadata[key] = str(doc[key])
            doc_id = self.insert(text, metadata=metadata)
            if doc_id:
                doc_ids.append(doc_id)
        logger.info(f"Ingested {len(doc_ids)}/{len(documents)} documents into KB '{kb}'")
        return doc_ids


rag_server = RAGServer()
