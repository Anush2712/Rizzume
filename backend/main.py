"""
Rizzume Backend - FastAPI Application
AI-powered resume tailoring with RAG and LLM processing
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from modules.resume_parser import ResumeParser
from modules.jd_parser import JDParser
from modules.rag_system import RAGSystem
from modules.llm_processor import LLMProcessor
from modules.latex_generator import LaTeXGenerator
from modules.pdf_compiler import PDFCompiler
from modules.cover_letter import CoverLetterGenerator

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rizzume API",
    description="AI Resume Tailoring Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (use Redis in production)
sessions: dict[str, dict] = {}

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize modules
resume_parser = ResumeParser()
jd_parser = JDParser()
rag_system = RAGSystem()
llm_processor = LLMProcessor()
latex_generator = LaTeXGenerator()
pdf_compiler = PDFCompiler()
cover_letter_generator = CoverLetterGenerator()


class GenerateRequest(BaseModel):
    session_id: str
    job_description: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None


class GenerateResponse(BaseModel):
    session_id: str
    match_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    resume_download_url: str
    cover_letter: str
    processing_time_ms: int


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume (PDF or DOCX). Returns a session_id."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(400, f"Unsupported file type: {ext}. Use PDF, DOCX, or TXT.")

    session_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{session_id}{ext}"

    try:
        content = await file.read()
        save_path.write_bytes(content)
        logger.info("Saved resume to %s", save_path)

        resume_text = resume_parser.parse(save_path)
        if not resume_text.strip():
            raise HTTPException(422, "Could not extract text from resume. Ensure the file is not scanned/image-only.")

        # Build RAG index for this session
        rag_system.index_resume(session_id, resume_text)

        sessions[session_id] = {
            "resume_text": resume_text,
            "file_path": str(save_path),
        }

        return {
            "session_id": session_id,
            "filename": file.filename,
            "char_count": len(resume_text),
            "message": "Resume uploaded and indexed successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process resume")
        raise HTTPException(500, f"Resume processing failed: {str(e)}")


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Main endpoint: given a session_id and JD text, returns a tailored PDF + cover letter.
    """
    import time
    start = time.time()

    if request.session_id not in sessions:
        raise HTTPException(404, "Session not found. Please upload your resume first.")

    session = sessions[request.session_id]
    resume_text = session["resume_text"]
    jd_text = request.job_description

    if not jd_text.strip():
        raise HTTPException(400, "Job description cannot be empty.")

    try:
        # 1. Parse JD
        logger.info("Parsing JD...")
        jd_data = jd_parser.parse(jd_text)

        # 2. RAG: retrieve relevant resume sections
        logger.info("Retrieving relevant resume sections...")
        relevant_sections = rag_system.retrieve(request.session_id, jd_data["keywords"], top_k=5)

        # 3. LLM: match score + rewrite bullets
        logger.info("Running LLM processing...")
        llm_result = llm_processor.process(
            resume_text=resume_text,
            jd_data=jd_data,
            relevant_sections=relevant_sections,
            job_title=request.job_title,
            company_name=request.company_name,
        )

        # 4. Generate LaTeX
        logger.info("Generating LaTeX...")
        tex_content = latex_generator.generate(llm_result)
        tex_path = OUTPUT_DIR / f"{request.session_id}.tex"
        tex_path.write_text(tex_content, encoding="utf-8")

        # 5. Compile PDF
        logger.info("Compiling PDF...")
        pdf_path = pdf_compiler.compile(tex_path)

        # 6. Cover letter
        logger.info("Generating cover letter...")
        cover_letter = cover_letter_generator.generate(
            resume_text=resume_text,
            jd_data=jd_data,
            llm_result=llm_result,
            job_title=request.job_title,
            company_name=request.company_name,
        )

        elapsed_ms = int((time.time() - start) * 1000)

        return GenerateResponse(
            session_id=request.session_id,
            match_score=llm_result["match_score"],
            matched_keywords=llm_result["matched_keywords"],
            missing_keywords=llm_result["missing_keywords"],
            resume_download_url=f"/download/{request.session_id}",
            cover_letter=cover_letter,
            processing_time_ms=elapsed_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(500, f"Generation failed: {str(e)}")


@app.get("/download/{session_id}")
async def download_resume(session_id: str):
    """Download the compiled PDF resume."""
    pdf_path = OUTPUT_DIR / f"{session_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "PDF not found. Run /generate first.")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="tailored_resume.pdf"
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up session data."""
    sessions.pop(session_id, None)
    rag_system.delete_index(session_id)
    for path in [
        UPLOAD_DIR / f"{session_id}.pdf",
        UPLOAD_DIR / f"{session_id}.docx",
        UPLOAD_DIR / f"{session_id}.txt",
        OUTPUT_DIR / f"{session_id}.tex",
        OUTPUT_DIR / f"{session_id}.pdf",
    ]:
        if path.exists():
            path.unlink()
    return {"message": "Session deleted."}
