"""Tests for LLMProcessor (fully mocked — no OpenAI calls)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from modules.llm_processor import LLMProcessor

SAMPLE_RESUME = "John Doe | Python, AWS, Docker | Built APIs at Stripe"
SAMPLE_JD_DATA = {
    "role": "Senior Backend Engineer",
    "keywords": ["Python", "AWS", "Docker", "microservices"],
    "responsibilities": ["Build scalable APIs", "Own infrastructure"],
    "seniority": "senior",
}
SAMPLE_SECTIONS = [
    "Built REST APIs handling 5M requests/day using Python and FastAPI",
    "Deployed infrastructure on AWS EKS with Docker and Kubernetes",
]

MOCK_LLM_RESPONSE = {
    "match_score": 82,
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
    "summary": "Senior engineer with expertise in Python, AWS, and distributed systems.",
    "skills": {
        "languages": ["Python"],
        "frameworks": ["FastAPI"],
        "tools": ["Docker"],
        "databases": ["PostgreSQL"],
        "cloud": ["AWS"],
    },
    "experience": [
        {
            "company": "Stripe",
            "title": "Senior Engineer",
            "location": "New York, NY",
            "start_date": "Jan 2022",
            "end_date": "Present",
            "bullets": ["Built payment APIs processing $1B/year"],
        }
    ],
    "projects": [],
    "education": [
        {
            "institution": "MIT",
            "degree": "B.S. CS",
            "graduation": "2019",
            "gpa": "",
            "coursework": [],
        }
    ],
    "certifications": [],
}


def make_mock_model(response_dict: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(response_dict)
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_resp
    return mock_model


class TestLLMProcessor:
    def setup_method(self):
        self.processor = LLMProcessor()
        self.processor._model = make_mock_model(MOCK_LLM_RESPONSE)

    def test_process_returns_dict(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert isinstance(result, dict)

    def test_match_score_present(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert "match_score" in result
        assert 0 <= result["match_score"] <= 100

    def test_matched_keywords_list(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert isinstance(result["matched_keywords"], list)

    def test_missing_keywords_list(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert isinstance(result["missing_keywords"], list)

    def test_candidate_fields(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        c = result["candidate"]
        assert "name" in c
        assert "email" in c

    def test_experience_is_list(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert isinstance(result["experience"], list)

    def test_score_clamped_above_100(self):
        bad_response = dict(MOCK_LLM_RESPONSE)
        bad_response["match_score"] = 150
        self.processor._model = make_mock_model(bad_response)
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert result["match_score"] == 100

    def test_score_clamped_below_0(self):
        bad_response = dict(MOCK_LLM_RESPONSE)
        bad_response["match_score"] = -10
        self.processor._model = make_mock_model(bad_response)
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert result["match_score"] == 0

    def test_missing_keys_filled_with_defaults(self):
        minimal = {"match_score": 50}  # missing all other keys
        self.processor._model = make_mock_model(minimal)
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS
        )
        assert "matched_keywords" in result
        assert "experience" in result
        assert "education" in result

    def test_optional_job_title_passed(self):
        result = self.processor.process(
            SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS,
            job_title="Staff Engineer", company_name="Google"
        )
        # Verify the LLM was called
        assert self.processor._model.generate_content.called

    def test_prompt_contains_jd_keywords(self):
        self.processor.process(SAMPLE_RESUME, SAMPLE_JD_DATA, SAMPLE_SECTIONS)
        call_args = self.processor._model.generate_content.call_args
        prompt = str(call_args)
        assert "Python" in prompt or "microservices" in prompt
