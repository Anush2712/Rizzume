"""Tests for RAGSystem module (keyword fallback path — no FAISS/embeddings needed)."""

import pytest
from unittest.mock import patch, MagicMock

from modules.rag_system import RAGSystem, _chunk_resume


SAMPLE_RESUME = """
John Doe
john@example.com | github.com/johndoe

EXPERIENCE

Senior Software Engineer – Acme Corp (2021–Present)
- Built a distributed caching layer using Redis that reduced API latency by 40%
- Designed microservices on Kubernetes and AWS EKS handling 10M requests/day
- Led migration from monolith to microservices architecture

Software Engineer – StartupXYZ (2018–2021)
- Developed ML pipeline using Python, Scikit-learn, and Airflow
- Optimised PostgreSQL queries reducing p99 latency from 800ms to 120ms

PROJECTS

Resume AI – Python, FastAPI, FAISS
- Built RAG system for resume matching using FAISS and OpenAI embeddings

EDUCATION
B.S. Computer Science – MIT (2018)
"""


class TestChunkResume:
    def test_produces_non_empty_chunks(self):
        chunks = _chunk_resume(SAMPLE_RESUME)
        assert len(chunks) > 0

    def test_filters_short_chunks(self):
        chunks = _chunk_resume(SAMPLE_RESUME)
        for chunk in chunks:
            assert len(chunk) > 30

    def test_bullet_points_become_individual_chunks(self):
        text = "- Built a distributed caching layer using Redis that reduced API latency by 40%\n- Designed microservices on Kubernetes"
        chunks = _chunk_resume(text)
        assert any("Redis" in c for c in chunks)
        assert any("Kubernetes" in c for c in chunks)

    def test_empty_string_returns_empty(self):
        chunks = _chunk_resume("")
        assert chunks == []

    def test_only_short_lines_filtered(self):
        text = "Hi\n\nHello\n\nThis is a much longer line that should pass the 30 char filter easily."
        chunks = _chunk_resume(text)
        assert any("longer line" in c for c in chunks)


class TestRAGSystemKeywordFallback:
    """Tests using keyword backend (no FAISS / OpenAI required)."""

    def setup_method(self):
        # Force keyword backend by patching the embedding fn to None
        self.rag = RAGSystem.__new__(RAGSystem)
        self.rag._indexes = {}
        self.rag._embedding_fn = None  # triggers keyword fallback

    def test_index_resume_stores_chunks(self):
        self.rag.index_resume("sess1", SAMPLE_RESUME)
        assert "sess1" in self.rag._indexes
        assert len(self.rag._indexes["sess1"]["chunks"]) > 0
        assert self.rag._indexes["sess1"]["backend"] == "keyword"

    def test_retrieve_returns_relevant_chunks(self):
        self.rag.index_resume("sess1", SAMPLE_RESUME)
        results = self.rag.retrieve("sess1", ["redis", "caching"], top_k=3)
        assert len(results) > 0
        # The Redis bullet should rank highly
        assert any("Redis" in r or "redis" in r.lower() for r in results)

    def test_retrieve_top_k_respected(self):
        self.rag.index_resume("sess1", SAMPLE_RESUME)
        results = self.rag.retrieve("sess1", ["python", "kubernetes", "ml"], top_k=2)
        assert len(results) <= 2

    def test_retrieve_unknown_session_returns_empty(self):
        results = self.rag.retrieve("nonexistent", ["python"], top_k=3)
        assert results == []

    def test_delete_index_removes_session(self):
        self.rag.index_resume("sess_del", SAMPLE_RESUME)
        assert "sess_del" in self.rag._indexes
        self.rag.delete_index("sess_del")
        assert "sess_del" not in self.rag._indexes

    def test_delete_nonexistent_index_no_error(self):
        self.rag.delete_index("ghost_session")  # should not raise

    def test_retrieve_empty_keywords(self):
        self.rag.index_resume("sess2", SAMPLE_RESUME)
        results = self.rag.retrieve("sess2", [], top_k=3)
        # With no keywords, all scores are 0; still returns up to top_k
        assert isinstance(results, list)

    def test_multiple_sessions_isolated(self):
        resume_a = "Python developer with Django and PostgreSQL experience at scale"
        resume_b = "Java engineer with Spring Boot and Kafka experience"
        self.rag.index_resume("sess_a", resume_a)
        self.rag.index_resume("sess_b", resume_b)
        results_a = self.rag.retrieve("sess_a", ["python"], top_k=1)
        results_b = self.rag.retrieve("sess_b", ["java"], top_k=1)
        assert any("Python" in r or "python" in r.lower() for r in results_a)
        assert any("Java" in r or "java" in r.lower() for r in results_b)
