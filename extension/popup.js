/**
 * Rizzume – Popup Script v2
 */

const API_BASE = "http://localhost:8000";
const SESSION_KEY = "rizzume_session";

// ── DOM refs ──────────────────────────────────────────────
const uploadArea    = document.getElementById("upload-area");
const resumeFile    = document.getElementById("resume-file");
const uploadText    = document.getElementById("upload-text");
const resumeStatus  = document.getElementById("resume-status");
const btnUpload     = document.getElementById("btn-upload");
const btnExtract    = document.getElementById("btn-extract");
const jdTextarea    = document.getElementById("jd-text");
const jobTitle      = document.getElementById("job-title");
const companyName   = document.getElementById("company-name");
const btnGenerate   = document.getElementById("btn-generate");
const generateHint  = document.querySelector(".generate-hint");
const sectionResult = document.getElementById("section-results");
const matchBadge    = document.getElementById("match-score-badge");
const scoreBar      = document.getElementById("score-bar");
const scoreValue    = document.getElementById("score-value");
const scoreDesc     = document.getElementById("score-desc");
const ringFill      = document.getElementById("ring-fill");
const matchedKw     = document.getElementById("matched-kw");
const missingKw     = document.getElementById("missing-kw");
const btnDownload   = document.getElementById("btn-download");
const btnCover      = document.getElementById("btn-cover");
const coverModal    = document.getElementById("cover-modal");
const coverText     = document.getElementById("cover-letter-text");
const btnModalClose = document.getElementById("btn-modal-close");
const btnCopyCover  = document.getElementById("btn-copy-cover");
const loadingOverlay= document.getElementById("loading-overlay");
const loadingText   = document.getElementById("loading-text");
const errorToast    = document.getElementById("error-toast");
const toastMsg      = document.getElementById("toast-msg");
const dot1          = document.getElementById("dot-1");
const dot2          = document.getElementById("dot-2");
const dot3          = document.getElementById("dot-3");

// SVG ring circumference for r=34: 2πr ≈ 213.6
const RING_C = 213.6;

let state = {
  sessionId: null,
  file: null,
  coverLetter: "",
  downloadUrl: null,
};

// ── Init ──────────────────────────────────────────────────
(async () => {
  const stored = await chrome.storage.local.get([
    SESSION_KEY,
    "rizzume_page_jd",
    "rizzume_page_title",
    "rizzume_page_company",
    "rizzume_page_detected_at",
    "rizzume_pending_jd",
  ]);

  if (stored[SESSION_KEY]) {
    state.sessionId = stored[SESSION_KEY];
    showStatus("Resume ready ✓", "success");
    uploadText.innerHTML = `<strong style="color:var(--success)">✓ Resume uploaded</strong><br/><span class="upload-sub">Click to replace</span>`;
    uploadArea.classList.add("has-file");
    btnUpload.disabled = false;
    setDot(dot1, "done");
  }

  const detectedAt = stored["rizzume_page_detected_at"] || 0;
  const fresh = Date.now() - detectedAt < 5 * 60 * 1000;
  const pageJD = fresh ? stored["rizzume_page_jd"] : null;
  const pending = stored["rizzume_pending_jd"];
  const jdToFill = pageJD || pending;

  if (jdToFill) {
    jdTextarea.value = jdToFill;
    jdTextarea.style.borderColor = "var(--success)";
    if (stored["rizzume_page_title"]) jobTitle.value = stored["rizzume_page_title"];
    if (stored["rizzume_page_company"]) companyName.value = stored["rizzume_page_company"];
    await chrome.storage.local.remove("rizzume_pending_jd");
    setDot(dot2, "done");
  }

  updateGenerateBtn();
})();

// ── Step dots ─────────────────────────────────────────────
function setDot(dot, state) {
  dot.className = `step-dot ${state}`;
}

// ── Upload Area ───────────────────────────────────────────
uploadArea.addEventListener("click", () => resumeFile.click());
uploadArea.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") resumeFile.click(); });
uploadArea.addEventListener("dragover", (e) => { e.preventDefault(); uploadArea.classList.add("drag-over"); });
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) setFile(file);
});
resumeFile.addEventListener("change", () => { if (resumeFile.files?.[0]) setFile(resumeFile.files[0]); });

function setFile(file) {
  const allowed = [".pdf", ".docx", ".txt"];
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(ext)) { showError("Use a PDF, DOCX, or TXT file."); return; }
  state.file = file;
  uploadArea.classList.add("has-file");
  uploadText.innerHTML = `<strong>${file.name}</strong><br/><span class="upload-sub">${formatSize(file.size)}</span>`;
  btnUpload.disabled = false;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/1048576).toFixed(1)} MB`;
}

// ── Upload Resume ─────────────────────────────────────────
btnUpload.addEventListener("click", async () => {
  if (!state.file) return;
  showLoading("Uploading & indexing resume…");
  try {
    const fd = new FormData();
    fd.append("file", state.file);
    const resp = await fetch(`${API_BASE}/upload_resume`, { method: "POST", body: fd });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    state.sessionId = data.session_id;
    await chrome.storage.local.set({ [SESSION_KEY]: state.sessionId });
    showStatus(`✓ Indexed · ${data.char_count.toLocaleString()} chars`, "success");
    setDot(dot1, "done");
    updateGenerateBtn();
  } catch (err) {
    showStatus(`Upload failed: ${err.message}`, "error");
    showError(err.message.includes("fetch") ? "Can't reach backend. Is it running on localhost:8000?" : err.message);
  } finally {
    hideLoading();
  }
});

// ── Extract JD ────────────────────────────────────────────
btnExtract.addEventListener("click", async () => {
  showLoading("Scanning page for job description…");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    let result = null;
    try {
      result = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_JD" });
    } catch {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
      await new Promise(r => setTimeout(r, 1000));
      result = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_JD" }).catch(() => null);
    }

    if (result?.jd && result.jd.length > 100) {
      jdTextarea.value = result.jd;
      jdTextarea.style.borderColor = "var(--success)";
      if (result.jobTitle) jobTitle.value = result.jobTitle;
      if (result.company)  companyName.value = result.company;
      setDot(dot2, "done");
      updateGenerateBtn();
    } else {
      showError("Couldn't detect a job description on this page. Try scrolling to the full JD first, or paste it manually.");
    }
  } catch (err) {
    showError(`Extraction error: ${err.message}`);
  } finally {
    hideLoading();
  }
});

// ── JD textarea ───────────────────────────────────────────
jdTextarea.addEventListener("input", () => {
  jdTextarea.style.borderColor = "";
  if (jdTextarea.value.trim().length > 50) setDot(dot2, "done");
  updateGenerateBtn();
});

function updateGenerateBtn() {
  const ready = state.sessionId && jdTextarea.value.trim().length > 50;
  btnGenerate.disabled = !ready;
  if (generateHint) generateHint.style.opacity = ready ? "0" : "1";
}

// ── Generate ──────────────────────────────────────────────
btnGenerate.addEventListener("click", generate);

async function generate() {
  if (!state.sessionId || !jdTextarea.value.trim()) return;

  const steps = [
    "Analyzing job description…",
    "Matching your skills via RAG…",
    "Rewriting bullets in STAR format…",
    "Scoring ATS match…",
    "Generating FAANG LaTeX resume…",
    "Compiling PDF…",
    "Writing cover letter…",
  ];

  let stepIdx = 0;
  showLoading(steps[0]);
  const stepTimer = setInterval(() => {
    stepIdx = Math.min(stepIdx + 1, steps.length - 1);
    loadingText.textContent = steps[stepIdx];
  }, 4000);

  try {
    const resp = await fetch(`${API_BASE}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        job_description: jdTextarea.value.trim(),
        job_title: jobTitle.value.trim() || null,
        company_name: companyName.value.trim() || null,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    state.downloadUrl = `${API_BASE}${data.resume_download_url}`;
    state.coverLetter = data.cover_letter;

    renderResults(data);
    setDot(dot3, "done");
    sectionResult.classList.remove("hidden");
    sectionResult.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showError(err.message.includes("fetch") ? "Can't reach backend. Is it running on localhost:8000?" : `Generation failed: ${err.message}`);
  } finally {
    clearInterval(stepTimer);
    hideLoading();
  }
}

// ── Render Results ────────────────────────────────────────
function renderResults(data) {
  const score = Math.max(0, Math.min(100, data.match_score ?? 0));

  // Badge
  const label = score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Fair" : "Low";
  const color = scoreColor(score);
  matchBadge.textContent = `${score}% · ${label}`;
  matchBadge.style.color = color;
  matchBadge.style.background = `${color}18`;
  matchBadge.style.borderColor = `${color}30`;

  // Score ring
  requestAnimationFrame(() => {
    const offset = RING_C - (score / 100) * RING_C;
    ringFill.style.strokeDashoffset = offset;
    ringFill.style.stroke = color;
  });

  scoreValue.textContent = score;
  scoreValue.style.color = color;
  scoreBar.style.width = `${score}%`;
  scoreBar.style.background = `linear-gradient(90deg, ${color}, ${color}aa)`;

  if (scoreDesc) {
    scoreDesc.textContent = label;
    scoreDesc.style.color = color;
  }

  renderChips(matchedKw, data.matched_keywords ?? [], "matched");
  renderChips(missingKw, data.missing_keywords ?? [], "missing");
}

function scoreColor(score) {
  if (score >= 70) return "#22c55e";
  if (score >= 45) return "#f59e0b";
  return "#ef4444";
}

function renderChips(container, keywords, type) {
  container.innerHTML = "";
  if (!keywords.length) {
    container.innerHTML = `<span style="color:var(--text-muted);font-size:11px">None detected</span>`;
    return;
  }
  for (const kw of keywords) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = kw;
    container.appendChild(chip);
  }
}

// ── Download ──────────────────────────────────────────────
btnDownload.addEventListener("click", () => {
  if (state.downloadUrl) chrome.tabs.create({ url: state.downloadUrl });
});

// ── Cover Letter Modal ────────────────────────────────────
btnCover.addEventListener("click", () => {
  coverText.value = state.coverLetter;
  coverModal.classList.remove("hidden");
});
btnModalClose.addEventListener("click", () => coverModal.classList.add("hidden"));
coverModal.addEventListener("click", (e) => { if (e.target === coverModal) coverModal.classList.add("hidden"); });
btnCopyCover.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(state.coverLetter);
    btnCopyCover.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
    setTimeout(() => {
      btnCopyCover.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy to Clipboard`;
    }, 2000);
  } catch { showError("Clipboard write failed."); }
});

// ── Helpers ───────────────────────────────────────────────
function showStatus(msg, type) {
  resumeStatus.textContent = msg;
  resumeStatus.className = `status-badge ${type}`;
  resumeStatus.classList.remove("hidden");
}

function showLoading(msg = "Processing…") {
  loadingText.textContent = msg;
  loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  loadingOverlay.classList.add("hidden");
}

let toastTimer = null;
function showError(msg) {
  if (toastMsg) toastMsg.textContent = msg;
  else errorToast.textContent = msg;
  errorToast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => errorToast.classList.add("hidden"), 5000);
}
