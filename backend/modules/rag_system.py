"""
RAG System: indexes resume sections as embeddings and retrieves
the most relevant ones given JD keywords.
Uses FAISS for vector search and OpenAI embeddings (or sentence-transformers fallback).
"""

import os
import logging
import re
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _chunk_resume(text: str) -> list[str]:
    """Split resume into meaningful chunks (sections / bullet points)."""
    chunks = []
    current_section: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if current_section:
                chunks.append(" ".join(current_section))
                current_section = []
        else:
            # Bullet points become individual chunks
            if re.match(r"^[\-•\*]\s+", line):
                if current_section:
                    chunks.append(" ".join(current_section))
                    current_section = []
                chunks.append(re.sub(r"^[\-•\*]\s+", "", line))
            else:
                current_section.append(line)

    if current_section:
        chunks.append(" ".join(current_section))

    # Filter out very short chunks (headers, etc.)
    return [c for c in chunks if len(c) > 30]


class RAGSystem:
    def __init__(self):
        self._indexes: dict[str, dict] = {}  # session_id -> {chunks, embeddings, index}
        self._embedding_fn = self._get_embedding_fn()

    def _get_embedding_fn(self):
        """Return an embedding function. Prefers sentence-transformers, falls back to keyword."""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Using sentence-transformers (all-MiniLM-L6-v2)")
            return lambda texts: model.encode(texts, convert_to_numpy=True).astype("float32")
        except ImportError:
            pass

        # Trivial TF-IDF fallback (no GPU/API needed)
        logger.warning("No embedding library found — using TF-IDF keyword matching")
        return None

    def index_resume(self, session_id: str, resume_text: str):
        """Chunk the resume and build a FAISS index (or keyword store)."""
        chunks = _chunk_resume(resume_text)
        if not chunks:
            chunks = [resume_text]

        if self._embedding_fn is not None:
            try:
                import faiss
                embeddings = self._embedding_fn(chunks)
                dim = embeddings.shape[1]
                index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalization
                faiss.normalize_L2(embeddings)
                index.add(embeddings)
                self._indexes[session_id] = {
                    "chunks": chunks,
                    "index": index,
                    "backend": "faiss",
                }
                logger.info("FAISS index built for session %s (%d chunks)", session_id, len(chunks))
                return
            except ImportError:
                logger.warning("faiss not installed, falling back to numpy cosine search")
                embeddings = self._embedding_fn(chunks)
                self._indexes[session_id] = {
                    "chunks": chunks,
                    "embeddings": embeddings,
                    "backend": "numpy",
                }
                return

        # Keyword-based fallback
        self._indexes[session_id] = {
            "chunks": chunks,
            "backend": "keyword",
        }

    def retrieve(self, session_id: str, keywords: list[str], top_k: int = 5) -> list[str]:
        """Retrieve top-k resume chunks most relevant to the JD keywords."""
        store = self._indexes.get(session_id)
        if not store:
            return []

        chunks = store["chunks"]
        backend = store["backend"]

        if backend == "faiss":
            import faiss
            query_text = " ".join(keywords)
            q_embed = self._embedding_fn([query_text])
            faiss.normalize_L2(q_embed)
            _, indices = store["index"].search(q_embed, min(top_k, len(chunks)))
            return [chunks[i] for i in indices[0] if i < len(chunks)]

        if backend == "numpy":
            query_text = " ".join(keywords)
            q_embed = self._embedding_fn([query_text])
            # Cosine similarity
            norms_store = np.linalg.norm(store["embeddings"], axis=1, keepdims=True)
            norms_q = np.linalg.norm(q_embed, axis=1, keepdims=True)
            sim = (store["embeddings"] / (norms_store + 1e-8)) @ (q_embed / (norms_q + 1e-8)).T
            top_indices = np.argsort(sim[:, 0])[::-1][:top_k]
            return [chunks[i] for i in top_indices]

        # Keyword fallback: score by overlap
        kw_set = {k.lower() for k in keywords}
        scored = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for kw in kw_set if kw in chunk_lower)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def delete_index(self, session_id: str):
        self._indexes.pop(session_id, None)
