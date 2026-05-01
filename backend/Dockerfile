# ── Rizzume Backend – Docker Image ────────────────────────
# Includes Python, FastAPI, and a full TeX Live installation
# for reliable PDF compilation.

FROM python:3.11-slim

# Install LaTeX — fonts-extra omitted (saves ~500MB, not needed for FAANG template)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    latexmk \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create output dirs
RUN mkdir -p uploads outputs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
