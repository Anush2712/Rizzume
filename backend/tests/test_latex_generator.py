"""Tests for LaTeXGenerator module."""

import pytest
from modules.latex_generator import LaTeXGenerator, _escape


class TestEscape:
    def test_ampersand(self):
        assert _escape("A & B") == r"A \& B"

    def test_percent(self):
        assert _escape("50%") == r"50\%"

    def test_dollar(self):
        assert _escape("$100k") == r"\$100k"

    def test_underscore(self):
        assert _escape("snake_case") == r"snake\_case"

    def test_hash(self):
        assert _escape("#1") == r"\#1"

    def test_empty_string(self):
        assert _escape("") == ""

    def test_no_special_chars(self):
        assert _escape("Hello World") == "Hello World"

    def test_multiple_specials(self):
        result = _escape("50% & $100")
        assert r"\%" in result
        assert r"\&" in result
        assert r"\$" in result


SAMPLE_DATA = {
    "candidate": {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1-555-000-1234",
        "linkedin": "linkedin.com/in/janesmith",
        "github": "github.com/janesmith",
        "location": "San Francisco, CA",
    },
    "summary": "Senior engineer with 7 years building distributed systems at scale.",
    "skills": {
        "languages": ["Python", "Go"],
        "frameworks": ["FastAPI", "gRPC"],
        "tools": ["Docker", "Kubernetes"],
        "databases": ["PostgreSQL", "Redis"],
        "cloud": ["AWS", "GCP"],
    },
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
            "location": "San Francisco, CA",
            "start_date": "Jan 2021",
            "end_date": "Present",
            "bullets": [
                "Built caching layer reducing latency by 40%",
                "Led migration to microservices handling 10M RPD",
            ],
        }
    ],
    "projects": [
        {
            "name": "ResumeAI",
            "tech_stack": ["Python", "FAISS"],
            "bullets": ["Built RAG resume tailor with 90% match accuracy"],
            "url": "github.com/janesmith/resumeai",
        }
    ],
    "education": [
        {
            "institution": "MIT",
            "degree": "B.S. Computer Science",
            "graduation": "May 2017",
            "gpa": "3.9",
            "coursework": ["Algorithms", "Distributed Systems"],
        }
    ],
    "certifications": ["AWS Solutions Architect"],
    "match_score": 85,
    "matched_keywords": [],
    "missing_keywords": [],
}


class TestLaTeXGenerator:
    def setup_method(self):
        self.gen = LaTeXGenerator()

    def test_generate_returns_string(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_candidate_name_in_output(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "Jane Smith" in result

    def test_candidate_email_in_output(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "jane@example.com" in result

    def test_summary_in_output(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "distributed systems" in result

    def test_skills_rendered(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "Python" in result
        assert "Kubernetes" in result

    def test_experience_rendered(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "Acme Corp" in result
        assert "latency by 40" in result

    def test_project_rendered(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "ResumeAI" in result

    def test_education_rendered(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "MIT" in result
        assert "3.9" in result

    def test_certification_rendered(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert "AWS Solutions Architect" in result

    def test_valid_latex_document_structure(self):
        result = self.gen.generate(SAMPLE_DATA)
        assert r"\documentclass" in result
        assert r"\begin{document}" in result
        assert r"\end{document}" in result

    def test_special_chars_escaped_in_bullets(self):
        data = dict(SAMPLE_DATA)
        data["experience"] = [
            {
                "company": "Acme & Co",
                "title": "Engineer",
                "location": "NY",
                "start_date": "2020",
                "end_date": "Present",
                "bullets": ["Saved $2M via 50% cost reduction"],
            }
        ]
        result = self.gen.generate(data)
        assert r"\&" in result
        assert r"\$" in result
        assert r"\%" in result

    def test_empty_experience_no_crash(self):
        data = dict(SAMPLE_DATA)
        data["experience"] = []
        result = self.gen.generate(data)
        assert isinstance(result, str)

    def test_empty_skills_no_crash(self):
        data = dict(SAMPLE_DATA)
        data["skills"] = {}
        result = self.gen.generate(data)
        assert isinstance(result, str)

    def test_no_certifications_no_crash(self):
        data = dict(SAMPLE_DATA)
        data["certifications"] = []
        result = self.gen.generate(data)
        assert isinstance(result, str)
