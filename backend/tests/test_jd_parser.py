"""Tests for JDParser module (regex fallback path — no Gemini needed)."""

import sys
import pytest
from unittest.mock import patch, MagicMock

# Pre-mock google.generativeai so import doesn't fail if SDK is not installed
sys.modules.setdefault("google.generativeai", MagicMock())
sys.modules.setdefault("google", MagicMock())

from modules.jd_parser import JDParser


SAMPLE_JD = """
Senior Backend Engineer – Payments Platform

About the Role:
We are looking for a Senior Backend Engineer to join our Payments team.

Responsibilities:
- Design and build scalable microservices using Python and Go
- Own and operate PostgreSQL and Redis infrastructure on AWS
- Collaborate cross-functionally with product and design teams
- Drive technical decisions and mentor junior engineers

Requirements:
- 5+ years of experience with distributed systems
- Strong knowledge of Python, Docker, Kubernetes
- Experience with Kafka or similar message queues
- AWS certification preferred
"""


class TestJDParserRegex:
    def setup_method(self):
        self.parser = JDParser()

    def test_returns_dict_with_required_keys(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        for key in ("role", "company", "keywords", "technical_skills",
                    "soft_skills", "responsibilities", "seniority"):
            assert key in result, f"Missing key: {key}"

    def test_detects_technical_skills(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        skills_lower = [s.lower() for s in result["technical_skills"]]
        assert "python" in skills_lower
        assert "docker" in skills_lower
        assert "kubernetes" in skills_lower

    def test_detects_soft_skills(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        soft_lower = [s.lower() for s in result["soft_skills"]]
        assert any(s in soft_lower for s in ("mentoring", "mentor", "leadership", "cross-functional"))

    def test_infers_senior_seniority(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        assert result["seniority"] == "senior"

    def test_infers_junior_seniority(self):
        jd = "We are looking for a junior engineer / new grad to join our team."
        result = self.parser._parse_with_regex(jd)
        assert result["seniority"] == "junior"

    def test_infers_staff_seniority(self):
        jd = "Principal Engineer or Staff Engineer with 10+ years experience."
        result = self.parser._parse_with_regex(jd)
        assert result["seniority"] == "staff"

    def test_keywords_list_is_non_empty(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        assert len(result["keywords"]) > 0

    def test_keywords_capped_at_15(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        assert len(result["keywords"]) <= 15

    def test_responsibilities_extracted(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        assert len(result["responsibilities"]) > 0

    def test_empty_jd_returns_defaults(self):
        result = self.parser._parse_with_regex("   ")
        assert isinstance(result["keywords"], list)
        assert isinstance(result["technical_skills"], list)

    def test_company_is_none_when_not_found(self):
        result = self.parser._parse_with_regex(SAMPLE_JD)
        assert result["company"] is None


class TestJDParserLLMFallback:
    """Ensure that if OpenAI raises, we fall back to regex gracefully."""

    def test_falls_back_to_regex_on_gemini_error(self):
        parser = JDParser()
        with patch.object(parser, "_parse_with_llm", side_effect=Exception("API down")):
            result = parser.parse(SAMPLE_JD)
        # Should still return a valid dict via regex fallback
        assert "keywords" in result
        assert isinstance(result["keywords"], list)

    def test_llm_result_normalized(self):
        import json
        parser = JDParser()

        expected = {
            "role": "SWE",
            "keywords": ["python"],
            "technical_skills": [],
            "soft_skills": [],
            "responsibilities": [],
            "industry_signals": [],
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(expected)

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        import google.generativeai as genai
        with patch.object(genai, "configure"), \
             patch.object(genai, "GenerativeModel", return_value=mock_model), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = parser._parse_with_llm(SAMPLE_JD)

        assert result["role"] == "SWE"
        assert "python" in result["keywords"]
