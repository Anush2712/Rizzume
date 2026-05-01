"""Tests for CoverLetterGenerator (mocked OpenAI)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from modules.cover_letter import CoverLetterGenerator

SAMPLE_JD_DATA = {
    "role": "Senior Backend Engineer",
    "company": "Stripe",
    "seniority": "senior",
    "industry_signals": ["fintech", "payments"],
    "keywords": ["Python", "AWS", "microservices"],
}

SAMPLE_LLM_RESULT = {
    "matched_keywords": ["Python", "AWS", "Docker"],
    "candidate": {"name": "Jane Smith", "email": "jane@example.com"},
    "summary": "Senior engineer with 7 years in payments infrastructure.",
    "experience": [
        {
            "company": "Acme",
            "bullets": ["Built payment APIs processing $500M/year"],
        }
    ],
}

SAMPLE_RESUME = "Jane Smith | Python, AWS, FastAPI | Payments at Acme"


def make_mock_client(response_text: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.text = response_text
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_resp
    return mock_model


MOCK_COVER_LETTER = """Dear Hiring Manager,

I am excited to apply for the Senior Backend Engineer role at Stripe.
With 7 years building payments infrastructure, I bring deep expertise in Python and AWS.

At Acme, I built payment APIs processing $500M/year, reducing latency by 40%.
My experience aligns closely with Stripe's mission to expand the GDP of the internet.

I would love to discuss how I can contribute. Please reach me at jane@example.com.

Sincerely,
Jane Smith"""


class TestCoverLetterGenerator:
    def setup_method(self):
        self.gen = CoverLetterGenerator()
        self.gen._model = make_mock_client(MOCK_COVER_LETTER)

    def test_generate_returns_string(self):
        result = self.gen.generate(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT
        )
        assert isinstance(result, str)
        assert len(result) > 50

    def test_generate_uses_llm_output(self):
        result = self.gen.generate(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT
        )
        assert "Jane Smith" in result or "Stripe" in result

    def test_generate_with_explicit_title_and_company(self):
        result = self.gen.generate(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT,
            job_title="Staff Engineer", company_name="Google"
        )
        assert isinstance(result, str)

    def test_fallback_on_api_error(self):
        gen = CoverLetterGenerator()
        gen._model = MagicMock()
        gen._model.generate_content.side_effect = Exception("API timeout")

        result = gen.generate(SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT)
        # Should return the fallback letter, not raise
        assert isinstance(result, str)
        assert len(result) > 30

    def test_fallback_contains_candidate_name(self):
        gen = CoverLetterGenerator()
        gen._model = MagicMock()
        gen._model.generate_content.side_effect = Exception("Error")

        result = gen.generate(SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT)
        assert "Jane Smith" in result

    def test_fallback_contains_role(self):
        gen = CoverLetterGenerator()
        gen._model = MagicMock()
        gen._model.generate_content.side_effect = Exception("Error")

        result = gen.generate(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT,
            job_title="Senior Backend Engineer"
        )
        assert "Senior Backend Engineer" in result

    def test_llm_called_once(self):
        self.gen.generate(SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_LLM_RESULT)
        assert self.gen._model.generate_content.call_count == 1

    def test_no_company_uses_default(self):
        jd_no_company = dict(SAMPLE_JD_DATA)
        jd_no_company["company"] = None
        result = self.gen.generate(SAMPLE_RESUME, jd_no_company, SAMPLE_LLM_RESULT)
        assert isinstance(result, str)
