"""
JD Parser: extracts structured data from a job description using NLP + LLM.
Returns a dict with: keywords, skills, responsibilities, role, company signals.
"""

import re
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Common tech skills for keyword extraction fallback
TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "react", "angular", "vue", "node.js", "django", "fastapi", "flask", "spring",
    "kubernetes", "docker", "aws", "gcp", "azure", "terraform", "ansible",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
    "spark", "hadoop", "airflow", "dbt", "snowflake", "bigquery",
    "machine learning", "deep learning", "nlp", "llm", "pytorch", "tensorflow",
    "scikit-learn", "pandas", "numpy", "opencv",
    "git", "ci/cd", "jenkins", "github actions", "graphql", "rest api",
    "microservices", "distributed systems", "system design", "sql",
    "linux", "bash", "agile", "scrum", "jira",
}

SOFT_SKILLS = {
    "communication", "leadership", "collaboration", "problem solving",
    "analytical", "detail-oriented", "ownership", "mentoring", "mentor",
    "cross-functional",
}


class JDParser:
    def parse(self, jd_text: str) -> dict:
        """
        Parse a job description and return structured data.
        Uses LLM if available, falls back to regex-based extraction.
        """
        try:
            return self._parse_with_llm(jd_text)
        except Exception as e:
            logger.warning("LLM JD parsing failed (%s), using fallback", e)
            return self._parse_with_regex(jd_text)

    def _parse_with_llm(self, jd_text: str) -> dict:
        import google.generativeai as genai
        import json

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            generation_config={"response_mime_type": "application/json"},
        )

        prompt = f"""Analyze this job description and return a JSON object with exactly these keys:
{{
  "role": "job title",
  "company": "company name if mentioned, else null",
  "keywords": ["top 15 ATS keywords"],
  "technical_skills": ["specific tools/languages/frameworks required"],
  "soft_skills": ["soft skills mentioned"],
  "responsibilities": ["3-5 core responsibilities as concise phrases"],
  "years_experience": "X years if mentioned, else null",
  "seniority": "junior/mid/senior/staff/principal",
  "industry_signals": ["any domain-specific signals like fintech, healthcare, etc."]
}}

Job Description:
{jd_text[:4000]}

Return ONLY valid JSON, no markdown fences."""

        response = model.generate_content(prompt)
        data = json.loads(response.text)
        # Normalize
        data.setdefault("keywords", [])
        data.setdefault("technical_skills", [])
        data.setdefault("soft_skills", [])
        data.setdefault("responsibilities", [])
        data.setdefault("industry_signals", [])
        return data

    def _parse_with_regex(self, jd_text: str) -> dict:
        """Fallback regex-based JD parser."""
        text_lower = jd_text.lower()

        # Extract keywords by matching known tech/soft skill terms
        found_tech = [skill for skill in TECH_SKILLS if skill in text_lower]
        found_soft = [skill for skill in SOFT_SKILLS if skill in text_lower]

        # Extract bullet-point responsibilities
        responsibilities = []
        lines = jd_text.split("\n")
        for line in lines:
            line = line.strip()
            if re.match(r"^[\-•\*]\s+.{20,}", line):
                responsibilities.append(re.sub(r"^[\-•\*]\s+", "", line))
            if len(responsibilities) >= 6:
                break

        # Try to find role
        role_match = re.search(
            r"(?:job title|position|role)[:\s]+([^\n]+)",
            jd_text, re.IGNORECASE
        )
        role = role_match.group(1).strip() if role_match else "Software Engineer"

        # Combine keywords
        keywords = list(dict.fromkeys(found_tech + found_soft))[:15]

        return {
            "role": role,
            "company": None,
            "keywords": keywords,
            "technical_skills": found_tech,
            "soft_skills": found_soft,
            "responsibilities": responsibilities,
            "years_experience": None,
            "seniority": self._infer_seniority(text_lower),
            "industry_signals": [],
        }

    def _infer_seniority(self, text_lower: str) -> str:
        if any(k in text_lower for k in ["staff engineer", "principal", "distinguished"]):
            return "staff"
        if any(k in text_lower for k in ["senior", "sr.", "lead"]):
            return "senior"
        if any(k in text_lower for k in ["junior", "jr.", "entry level", "new grad"]):
            return "junior"
        return "mid"
