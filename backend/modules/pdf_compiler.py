"""
PDF Compiler: compiles a .tex file to PDF using pdflatex or latexmk.
Falls back to a helpful error message if LaTeX is not installed.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFCompiler:
    def __init__(self):
        self._latex_cmd = self._find_latex()

    def _find_latex(self) -> str | None:
        for cmd in ("latexmk", "pdflatex"):
            if shutil.which(cmd):
                logger.info("Found LaTeX compiler: %s", cmd)
                return cmd
        logger.warning(
            "No LaTeX compiler found. PDF generation will fail unless Docker is used."
        )
        return None

    def compile(self, tex_path: Path) -> Path:
        """Compile .tex → .pdf. Returns path to the generated PDF."""
        if self._latex_cmd is None:
            raise RuntimeError(
                "LaTeX is not installed. "
                "Install TeX Live (Linux/Mac) or MiKTeX (Windows), "
                "or use the provided Docker image."
            )

        pdf_path = tex_path.with_suffix(".pdf")

        # Run in a temp dir to keep aux files out of outputs/
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_tex = Path(tmpdir) / tex_path.name
            shutil.copy(tex_path, tmp_tex)

            if self._latex_cmd == "latexmk":
                cmd = [
                    "latexmk",
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    str(tmp_tex),
                ]
            else:
                # Run pdflatex twice for proper rendering
                cmd = [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    str(tmp_tex),
                ]

            for run in range(2 if self._latex_cmd == "pdflatex" else 1):
                result = subprocess.run(
                    cmd,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    log_snippet = result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
                    logger.error("LaTeX compilation failed:\n%s", log_snippet)
                    raise RuntimeError(
                        f"LaTeX compilation failed. Check your template.\n\n{log_snippet}"
                    )

            tmp_pdf = tmp_tex.with_suffix(".pdf")
            if not tmp_pdf.exists():
                raise RuntimeError("PDF was not generated despite successful compilation.")

            shutil.copy(tmp_pdf, pdf_path)

        logger.info("PDF compiled: %s", pdf_path)
        return pdf_path
