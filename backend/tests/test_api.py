"""
API integration tests using FastAPI TestClient.
All LLM/external calls are mocked.
"""

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Mock heavy modules before importing main ──────────────
import sys

# Patch heavy modules so import doesn't fail if keys/libs are missing
sys.modules.setdefault("google.generativeai", MagicMock())
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("faiss", MagicMock())
sys.modules.setdefault("sentence_transformers", MagicMock())

from main import app, sessions, rag_system

# Force keyword-backend on the RAG system so upload doesn't crash
# when faiss/openai are mocked stubs
rag_system._embedding_fn = None

client = TestClient(app)

# ── Shared fixtures ───────────────────────────────────────

SAMPLE_RESUME_TEXT = """
John Doe | john@example.com | github.com/johndoe

EXPERIENCE
Senior Engineer – Stripe (2021–Present)
- Built payment APIs in Python handling $1B/year
- Deployed on AWS EKS with Docker and Kubernetes

SKILLS: Python, AWS, Docker, PostgreSQL, FastAPI
"""

SAMPLE_JD = """
We are hiring a Senior Backend Engineer.
Requirements: Python, AWS, Docker, microservices, PostgreSQL.
You will design scalable APIs and own cloud infrastructure.
5+ years experience required.
"""

MOCK_LLM_RESULT = {
    "match_score": 78,
    "matched_keywords": ["Python", "AWS", "Docker"],
    "missing_keywords": ["microservices"],
    "candidate": {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-000-0000",
        "linkedin": "linkedin.com/in/johndoe",
        "github": "github.com/johndoe",
        "location": "New York, NY",
    },
    "summary": "Senior engineer with expertise in Python and AWS.",
    "skills": {"languages": ["Python"], "frameworks": ["FastAPI"],
                "tools": ["Docker"], "databases": ["PostgreSQL"], "cloud": ["AWS"]},
    "experience": [{
        "company": "Stripe", "title": "Senior Engineer",
        "location": "NY", "start_date": "2021", "end_date": "Present",
        "bullets": ["Built APIs processing $1B/year"],
    }],
    "projects": [],
    "education": [{"institution": "MIT", "degree": "B.S. CS",
                   "graduation": "2019", "gpa": "", "coursework": []}],
    "certifications": [],
}


def make_txt_upload(content: str = SAMPLE_RESUME_TEXT, filename: str = "resume.txt"):
    return ("file", (filename, io.BytesIO(content.encode()), "text/plain"))


# ── Health ────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_has_version(self):
        resp = client.get("/health")
        assert "version" in resp.json()


# ── Upload Resume ─────────────────────────────────────────

class TestUploadResume:
    def test_upload_txt_success(self):
        resp = client.post("/upload_resume", files=[make_txt_upload()])
        assert resp.status_code == 200
        body = resp.json()
        assert "session_id" in body
        assert body["char_count"] > 0

    def test_upload_creates_session(self):
        resp = client.post("/upload_resume", files=[make_txt_upload()])
        session_id = resp.json()["session_id"]
        assert session_id in sessions

    def test_upload_unsupported_type_returns_400(self):
        resp = client.post(
            "/upload_resume",
            files=[("file", ("resume.exe", io.BytesIO(b"binary"), "application/octet-stream"))],
        )
        assert resp.status_code == 400

    def test_upload_empty_file_returns_422(self):
        resp = client.post(
            "/upload_resume",
            files=[("file", ("resume.txt", io.BytesIO(b"   "), "text/plain"))],
        )
        assert resp.status_code == 422

    def test_upload_returns_filename(self):
        resp = client.post("/upload_resume", files=[make_txt_upload(filename="my_cv.txt")])
        assert resp.json()["filename"] == "my_cv.txt"


# ── Generate ──────────────────────────────────────────────

class TestGenerate:
    def _upload_and_get_session(self):
        resp = client.post("/upload_resume", files=[make_txt_upload()])
        return resp.json()["session_id"]

    @patch("main.llm_processor")
    @patch("main.cover_letter_generator")
    @patch("main.pdf_compiler")
    @patch("main.latex_generator")
    def test_generate_success(self, mock_latex, mock_pdf, mock_cover, mock_llm):
        mock_llm.process.return_value = MOCK_LLM_RESULT
        mock_latex.generate.return_value = "\\documentclass{article}\\begin{document}Test\\end{document}"
        mock_pdf.compile.return_value = Path(tempfile.mktemp(suffix=".pdf"))
        mock_pdf.compile.return_value.write_bytes(b"%PDF-1.4 fake pdf")
        mock_cover.generate.return_value = "Dear Hiring Manager, I am excited..."

        session_id = self._upload_and_get_session()
        resp = client.post("/generate", json={
            "session_id": session_id,
            "job_description": SAMPLE_JD,
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["match_score"] == 78
        assert "Python" in body["matched_keywords"]
        assert "resume_download_url" in body
        assert "cover_letter" in body

    def test_generate_unknown_session_returns_404(self):
        resp = client.post("/generate", json={
            "session_id": "does-not-exist",
            "job_description": SAMPLE_JD,
        })
        assert resp.status_code == 404

    def test_generate_empty_jd_returns_400(self):
        session_id = self._upload_and_get_session()
        resp = client.post("/generate", json={
            "session_id": session_id,
            "job_description": "   ",
        })
        assert resp.status_code == 400

    @patch("main.llm_processor")
    @patch("main.cover_letter_generator")
    @patch("main.pdf_compiler")
    @patch("main.latex_generator")
    def test_generate_with_optional_fields(self, mock_latex, mock_pdf, mock_cover, mock_llm):
        mock_llm.process.return_value = MOCK_LLM_RESULT
        mock_latex.generate.return_value = "\\documentclass{article}\\begin{document}X\\end{document}"
        mock_pdf.compile.return_value = Path(tempfile.mktemp(suffix=".pdf"))
        mock_pdf.compile.return_value.write_bytes(b"%PDF-1.4 fake")
        mock_cover.generate.return_value = "Cover letter text"

        session_id = self._upload_and_get_session()
        resp = client.post("/generate", json={
            "session_id": session_id,
            "job_description": SAMPLE_JD,
            "job_title": "Staff Engineer",
            "company_name": "Google",
        })
        assert resp.status_code == 200

    @patch("main.llm_processor")
    @patch("main.cover_letter_generator")
    @patch("main.pdf_compiler")
    @patch("main.latex_generator")
    def test_generate_returns_processing_time(self, mock_latex, mock_pdf, mock_cover, mock_llm):
        mock_llm.process.return_value = MOCK_LLM_RESULT
        mock_latex.generate.return_value = "\\documentclass{article}\\begin{document}X\\end{document}"
        mock_pdf.compile.return_value = Path(tempfile.mktemp(suffix=".pdf"))
        mock_pdf.compile.return_value.write_bytes(b"%PDF")
        mock_cover.generate.return_value = "Letter"

        session_id = self._upload_and_get_session()
        resp = client.post("/generate", json={
            "session_id": session_id,
            "job_description": SAMPLE_JD,
        })
        assert "processing_time_ms" in resp.json()
        assert resp.json()["processing_time_ms"] >= 0


# ── Download ──────────────────────────────────────────────

class TestDownload:
    def test_download_nonexistent_returns_404(self):
        resp = client.get("/download/ghost-session-123")
        assert resp.status_code == 404


# ── Delete Session ─────────────────────────────────────────

class TestDeleteSession:
    def test_delete_existing_session(self):
        upload_resp = client.post("/upload_resume", files=[make_txt_upload()])
        session_id = upload_resp.json()["session_id"]

        del_resp = client.delete(f"/session/{session_id}")
        assert del_resp.status_code == 200
        assert session_id not in sessions

    def test_delete_nonexistent_session_no_error(self):
        resp = client.delete("/session/ghost-999")
        assert resp.status_code == 200
