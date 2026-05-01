# Rizzume ⚡ — AI Resume Tailor

Generate FAANG-style tailored resumes and cover letters in one click.
Powered by RAG + LLM + LaTeX.

---

## Architecture

```
extension/          Chrome Extension (MV3)
backend/            FastAPI + Python backend
  modules/
    resume_parser   PDF/DOCX → text
    jd_parser       JD → structured keywords/skills
    rag_system      FAISS vector search over resume chunks
    llm_processor   GPT rewrite + STAR bullets + ATS scoring
    latex_generator Structured data → FAANG LaTeX
    pdf_compiler    pdflatex/latexmk → PDF
    cover_letter    Tailored cover letter generator
  templates/
    faang_resume.tex  LaTeX template
```

---

## Quick Start

### 1. Backend (Python)

```bash
cd backend
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> **No LaTeX?** Use Docker instead (recommended):
> ```bash
> docker compose up --build
> ```

### 2. Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer Mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder

---

## How to Use

1. **Upload your master resume** (PDF/DOCX/TXT) in the popup
2. **Go to any LinkedIn job posting** — the extension auto-detects "About the job"
3. Click **✨ Generate Tailored Resume**
4. Get:
   - **ATS Match Score** (0–100)
   - **Matched / Missing keywords**
   - **Downloadable PDF resume** (FAANG LaTeX style)
   - **Tailored Cover Letter**

---

## LaTeX Setup (local, no Docker)

- **Windows:** Install [MiKTeX](https://miktex.org/download)
- **Mac:** `brew install --cask mactex`
- **Linux:** `sudo apt install texlive-latex-extra texlive-fonts-extra latexmk`

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | required |
| `OPENAI_MODEL` | Chat model | `gpt-4o-mini` |
| `OPENAI_EMBED_MODEL` | Embedding model | `text-embedding-3-small` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload_resume` | Upload + index resume |
| `POST` | `/generate` | Generate tailored resume + cover letter |
| `GET`  | `/download/{session_id}` | Download PDF |
| `DELETE` | `/session/{session_id}` | Clean up session |

### Example request

```bash
# 1. Upload
curl -X POST http://localhost:8000/upload_resume \
  -F "file=@resume.pdf"
# → {"session_id": "abc-123", ...}

# 2. Generate
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "job_description": "We are looking for a Senior Backend Engineer...",
    "job_title": "Senior Backend Engineer",
    "company_name": "Stripe"
  }'
```

### Example response

```json
{
  "session_id": "abc-123",
  "match_score": 84,
  "matched_keywords": ["Python", "distributed systems", "PostgreSQL", "AWS"],
  "missing_keywords": ["Kafka", "Go"],
  "resume_download_url": "/download/abc-123",
  "cover_letter": "Dear Hiring Manager...",
  "processing_time_ms": 8432
}
```

---

## CV Bullet (copy this)

> Built a Chrome extension that auto-detects LinkedIn job descriptions and generates FAANG-style tailored resumes and cover letters using LLMs and RAG, reducing job application time by ~90%. Integrated FastAPI backend, FAISS vector search, and LaTeX PDF generation.
