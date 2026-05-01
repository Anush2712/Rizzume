"""
LaTeX Generator: populates a FAANG-style LaTeX template with LLM-structured data.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "faang_resume.tex"


def _escape(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


class LaTeXGenerator:
    def generate(self, data: dict) -> str:
        """Generate complete LaTeX source from structured resume data."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        c = data.get("candidate", {})
        template = template.replace("%%NAME%%", _escape(c.get("name", "Your Name")))
        template = template.replace("%%EMAIL%%", _escape(c.get("email", "")))
        template = template.replace("%%PHONE%%", _escape(c.get("phone", "")))
        template = template.replace("%%LINKEDIN%%", _escape(c.get("linkedin", "")))
        template = template.replace("%%GITHUB%%", _escape(c.get("github", "")))
        template = template.replace("%%LOCATION%%", _escape(c.get("location", "")))
        template = template.replace("%%SUMMARY%%", _escape(data.get("summary", "")))

        template = template.replace("%%SKILLS%%", self._render_skills(data.get("skills", {})))
        template = template.replace("%%EXPERIENCE%%", self._render_experience(data.get("experience", [])))
        template = template.replace("%%PROJECTS%%", self._render_projects(data.get("projects", [])))
        template = template.replace("%%EDUCATION%%", self._render_education(data.get("education", [])))
        template = template.replace("%%CERTIFICATIONS%%", self._render_certs(data.get("certifications", [])))

        return template

    def _render_skills(self, skills: dict) -> str:
        lines = []
        label_map = {
            "languages": "Languages",
            "frameworks": "Frameworks",
            "tools": "Tools",
            "databases": "Databases",
            "cloud": "Cloud",
        }
        for key, label in label_map.items():
            vals = skills.get(key, [])
            if vals:
                items = ", ".join(_escape(v) for v in vals)
                lines.append(
                    rf"\textbf{{{label}:}} {items} \\"
                )
        return "\n".join(lines)

    def _render_experience(self, experience: list) -> str:
        blocks = []
        for job in experience:
            title = _escape(job.get("title", ""))
            company = _escape(job.get("company", ""))
            location = _escape(job.get("location", ""))
            start = _escape(job.get("start_date", ""))
            end = _escape(job.get("end_date", "Present"))
            bullets = job.get("bullets", [])

            bullet_lines = "\n".join(
                rf"      \item {_escape(b)}" for b in bullets
            )
            block = rf"""
  \resumeSubheading
    {{{title}}}{{{start} -- {end}}}
    {{{company}}}{{{location}}}
  \resumeItemListStart
{bullet_lines}
  \resumeItemListEnd"""
            blocks.append(block)
        return "\n".join(blocks)

    def _render_projects(self, projects: list) -> str:
        blocks = []
        for proj in projects:
            name = _escape(proj.get("name", ""))
            tech = ", ".join(_escape(t) for t in proj.get("tech_stack", []))
            url = _escape(proj.get("url", ""))
            bullets = proj.get("bullets", [])

            header = rf"\resumeProjectHeading{{\textbf{{{name}}} $|$ \emph{{{tech}}}}}{{{url}}}"
            bullet_lines = "\n".join(
                rf"      \item {_escape(b)}" for b in bullets
            )
            block = rf"""
  {header}
  \resumeItemListStart
{bullet_lines}
  \resumeItemListEnd"""
            blocks.append(block)
        return "\n".join(blocks)

    def _render_education(self, education: list) -> str:
        blocks = []
        for edu in education:
            inst = _escape(edu.get("institution", ""))
            degree = _escape(edu.get("degree", ""))
            grad = _escape(edu.get("graduation", ""))
            gpa = edu.get("gpa", "")
            gpa_str = f" $|$ GPA: {_escape(gpa)}" if gpa else ""
            courses = edu.get("coursework", [])
            courses_str = ""
            if courses:
                courses_str = rf"\\ \small\textit{{Relevant Coursework: {', '.join(_escape(c) for c in courses)}}}"

            block = rf"""
  \resumeSubheading
    {{{inst}}}{{{grad}}}
    {{{degree}{gpa_str}}}{{}}
  {courses_str}"""
            blocks.append(block)
        return "\n".join(blocks)

    def _render_certs(self, certs: list) -> str:
        if not certs:
            return ""
        items = ", ".join(_escape(c) for c in certs)
        return rf"\resumeItemListStart \item {items} \resumeItemListEnd"
