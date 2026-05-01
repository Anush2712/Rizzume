"""
Cover Letter Generator: generates a tailored, professional cover letter.
Uses company signals from the JD to craft an intelligent narrative—
without fabricating specific company facts.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

COVER_LETTER_SYSTEM = """You are an expert career coach and professional writer.
You write compelling, personalized cover letters that:
- Sound human and genuine, not templated
- Reference the company's domain and likely challenges intelligently (no fake specifics)
- Connect the candidate's actual experience to what the role needs
- Are concise (3 paragraphs, under 350 words)
- End with a confident call to action"""


class CoverLetterGenerator:
    def __init__(self):
        self._model = None
        self._model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self._model = genai.GenerativeModel(
                self._model_name,
                system_instruction=COVER_LETTER_SYSTEM,
            )
        return self._model

    def generate(
        self,
        resume_text: str,
        jd_data: dict,
        llm_result: dict,
        job_title: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> str:
        target_role = job_title or jd_data.get("role", "Software Engineer")
        target_company = company_name or jd_data.get("company") or "your organization"
        seniority = jd_data.get("seniority", "mid")
        industry_signals = jd_data.get("industry_signals", [])
        matched_keywords = llm_result.get("matched_keywords", [])[:8]
        candidate = llm_result.get("candidate", {})
        summary = llm_result.get("summary", "")

        # Pick 2 most relevant experiences to highlight
        top_exp = llm_result.get("experience", [])[:2]
        exp_highlights = []
        for job in top_exp:
            bullets = job.get("bullets", [])
            if bullets:
                exp_highlights.append(f"At {job.get('company', 'my previous company')}: {bullets[0]}")

        exp_str = "\n".join(exp_highlights)
        industry_str = ", ".join(industry_signals) if industry_signals else "technology"
        keywords_str = ", ".join(matched_keywords)

        prompt = f"""Write a professional cover letter for:
Role: {target_role} ({seniority} level)
Company: {target_company}
Industry signals: {industry_str}

Candidate summary: {summary}

Top experience highlights:
{exp_str}

Shared keywords with JD: {keywords_str}

Structure:
1. Opening paragraph: Express genuine enthusiasm for the specific role. Mention one specific thing about what companies in {industry_str} are solving right now (scaling, AI adoption, reliability, developer experience—pick what's most relevant). Do NOT mention specific company metrics or financials you cannot verify.

2. Middle paragraph: Connect 2-3 of the candidate's actual experiences to what the role needs. Reference specific technologies or accomplishments from the highlights above.

3. Closing paragraph: Reinforce fit, express eagerness to discuss, professional sign-off.

Use the candidate's name: {candidate.get('name', '[Your Name]')}
Sign off with: {candidate.get('email', '')}

Keep it under 350 words. Sound confident and direct, not sycophantic."""

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error("Cover letter generation failed: %s", e)
            return self._fallback_cover_letter(
                candidate, target_role, target_company, summary
            )

    def _fallback_cover_letter(
        self, candidate: dict, role: str, company: str, summary: str
    ) -> str:
        name = candidate.get("name", "[Your Name]")
        email = candidate.get("email", "")
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {role} position at {company}. {summary}

Throughout my career, I have consistently delivered high-impact results by combining technical depth with a focus on business outcomes. I am excited by the opportunity to bring this experience to {company} and contribute to your team's goals.

I would welcome the chance to discuss how my background aligns with what you're looking for. Please feel free to reach me at {email}.

Sincerely,
{name}"""
