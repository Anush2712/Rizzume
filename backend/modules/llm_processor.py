"""
LLM Processor: orchestrates LLM calls to:
  1. Compute match score
  2. Rewrite resume bullets in STAR format
  3. Extract structured resume data for LaTeX
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert resume writer and ATS optimization specialist.
You help candidates tailor their resumes for specific job descriptions.
Rules:
- Never hallucinate experience or skills the candidate doesn't have
- Use STAR format for bullet points (Situation/Task, Action, Result)
- Quantify impact wherever possible (%, $, x faster, N users, etc.)
- Be concise: each bullet ≤ 2 lines
- Optimize for ATS keyword matching
- Keep tone professional and confident"""


class LLMProcessor:
    def __init__(self):
        self._model = None
        self._model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self._model = genai.GenerativeModel(
                self._model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config={"response_mime_type": "application/json"},
            )
        return self._model

    def process(
        self,
        resume_text: str,
        jd_data: dict,
        relevant_sections: list[str],
        job_title: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> dict:
        """
        Full LLM processing pipeline.
        Returns a dict with all data needed for LaTeX generation.
        """
        model = self._get_model()
        target_role = job_title or jd_data.get("role", "Software Engineer")
        target_company = company_name or jd_data.get("company", "the company")

        prompt = self._build_prompt(
            resume_text, jd_data, relevant_sections, target_role, target_company
        )

        logger.info("Calling Gemini for resume tailoring...")
        response = model.generate_content(prompt)

        raw = response.text
        result = json.loads(raw)
        self._validate_and_normalize(result, jd_data)
        return result

    def _build_prompt(
        self,
        resume_text: str,
        jd_data: dict,
        relevant_sections: list[str],
        target_role: str,
        target_company: str,
    ) -> str:
        keywords_str = ", ".join(jd_data.get("keywords", []))
        responsibilities_str = "\n".join(
            f"- {r}" for r in jd_data.get("responsibilities", [])
        )
        relevant_str = "\n".join(f"• {s}" for s in relevant_sections)

        return f"""
Tailor the following resume for this role: **{target_role}** at **{target_company}**.

## Target JD Keywords
{keywords_str}

## Core Responsibilities in JD
{responsibilities_str}

## Most Relevant Resume Sections (RAG-retrieved)
{relevant_str}

## Full Resume Text
{resume_text[:6000]}

---

Return a JSON object with EXACTLY this structure:
{{
  "match_score": <integer 0-100>,
  "matched_keywords": ["keywords that appear in both resume and JD"],
  "missing_keywords": ["important JD keywords NOT in the resume"],

  "candidate": {{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1-xxx-xxx-xxxx",
    "linkedin": "linkedin.com/in/handle",
    "github": "github.com/handle",
    "location": "City, State"
  }},

  "summary": "2-3 sentence professional summary tailored for {target_role} with keywords woven in",

  "skills": {{
    "languages": ["Python", "Java", ...],
    "frameworks": ["React", "FastAPI", ...],
    "tools": ["Docker", "Kubernetes", ...],
    "databases": ["PostgreSQL", "Redis", ...],
    "cloud": ["AWS", "GCP", ...]
  }},

  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "location": "City, State",
      "start_date": "Jan 2022",
      "end_date": "Present",
      "bullets": [
        "Rewritten STAR-format bullet with quantified impact and JD keywords",
        "Another strong bullet"
      ]
    }}
  ],

  "projects": [
    {{
      "name": "Project Name",
      "tech_stack": ["Python", "AWS"],
      "bullets": [
        "What you built and the measurable impact"
      ],
      "url": "github.com/..."
    }}
  ],

  "education": [
    {{
      "institution": "University Name",
      "degree": "B.S. Computer Science",
      "graduation": "May 2021",
      "gpa": "3.8",
      "coursework": ["Algorithms", "ML", "Distributed Systems"]
    }}
  ],

  "certifications": ["AWS Solutions Architect", "..."]
}}

IMPORTANT:
- Only include experience/projects that actually exist in the resume
- Rewrite bullets to emphasize skills matching the JD, but do NOT invent new accomplishments
- Prioritize most-relevant experience first
- Keep bullet count to 3-4 per role (max 5)
"""

    def _validate_and_normalize(self, result: dict, jd_data: dict):
        """Fill in defaults for any missing fields."""
        result.setdefault("match_score", 0)
        result.setdefault("matched_keywords", [])
        result.setdefault("missing_keywords", [])
        result.setdefault("candidate", {})
        result.setdefault("summary", "")
        result.setdefault("skills", {})
        result.setdefault("experience", [])
        result.setdefault("projects", [])
        result.setdefault("education", [])
        result.setdefault("certifications", [])

        # Clamp score
        result["match_score"] = max(0, min(100, int(result["match_score"])))
