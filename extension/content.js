/**
 * Rizzume – Content Script
 * Auto-detects job descriptions on LinkedIn and other job boards.
 */

(function () {
  "use strict";
  if (window.__rizzume_injected__) return;
  window.__rizzume_injected__ = true;

  // ── LinkedIn extractors ───────────────────────────────────

  function extractLinkedIn() {
    // Try known selectors first (ordered by reliability)
    const selectors = [
      ".jobs-description__content .jobs-description-content__text",
      ".jobs-description-content__text--stretch",
      ".jobs-description-content__text",
      ".jobs-description__container",
      ".jobs-box__html-content",
      ".jobs-description__content",
      "#job-details",
      "[data-test-id='job-details']",
      ".job-view-layout .jobs-description",
      ".scaffold-layout__detail .jobs-description",
    ];

    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        const text = el.innerText?.trim();
        if (text && text.length > 100) return text;
      }
    }

    // Heading scan: "About the job" / "Job Description" / "About this role"
    const headings = document.querySelectorAll("h1, h2, h3, h4, [class*='title'], [class*='heading']");
    for (const h of headings) {
      const txt = h.innerText?.trim().toLowerCase();
      if (!txt) continue;
      if (["about the job", "job description", "about this role", "about the role", "the role"].some(k => txt.includes(k))) {
        // Walk siblings and parent siblings looking for content
        const candidates = [h.nextElementSibling, h.parentElement?.nextElementSibling];
        for (let el of candidates) {
          while (el) {
            const content = el.innerText?.trim();
            if (content && content.length > 150) return content;
            el = el.nextElementSibling;
          }
        }
      }
    }

    // Broadest fallback: find any large text block that looks like a JD
    const JD_SIGNALS = ["responsibilities", "requirements", "qualifications", "experience", "skills"];
    const allDivs = document.querySelectorAll("div, section, article");
    let best = null;
    let bestScore = 0;

    for (const div of allDivs) {
      // Skip tiny or deeply nested containers
      if (div.children.length > 30) continue;
      const text = div.innerText?.trim() || "";
      if (text.length < 200 || text.length > 15000) continue;

      const lower = text.toLowerCase();
      const score = JD_SIGNALS.filter(s => lower.includes(s)).length;
      if (score >= 2 && text.length > bestScore) {
        best = text;
        bestScore = text.length;
      }
    }

    return best;
  }

  function extractLinkedInTitle() {
    const sel = [
      ".job-details-jobs-unified-top-card__job-title h1",
      ".jobs-unified-top-card__job-title h1",
      ".jobs-unified-top-card__job-title",
      ".topcard__title",
      "h1.t-24",
      "h1[class*='job-title']",
      "h1",
    ];
    for (const s of sel) {
      const el = document.querySelector(s);
      const txt = el?.innerText?.trim();
      if (txt && txt.length < 120) return txt;
    }
    return null;
  }

  function extractLinkedInCompany() {
    const sel = [
      ".job-details-jobs-unified-top-card__company-name a",
      ".jobs-unified-top-card__company-name a",
      ".topcard__org-name-link",
      ".topcard__flavor a",
      "[class*='company-name'] a",
      "[class*='company-name']",
    ];
    for (const s of sel) {
      const el = document.querySelector(s);
      const txt = el?.innerText?.trim();
      if (txt && txt.length < 80) return txt;
    }
    return null;
  }

  // ── Generic extractors ────────────────────────────────────
  const GENERIC_SELECTORS = [
    "#jobDescriptionText",
    ".jobsearch-jobDescriptionText",
    ".job-post-content",
    "#content .job",
    ".posting-description",
    "[data-automation-id='jobPostingDescription']",
    ".ashby-job-posting-brief-description",
    "[class*='job-description']",
    "[id*='job-description']",
    "[class*='JobDescription']",
    "[class*='jobDescription']",
  ];

  function extractGeneric() {
    for (const sel of GENERIC_SELECTORS) {
      const el = document.querySelector(sel);
      if (el) {
        const text = el.innerText?.trim();
        if (text && text.length > 100) return text;
      }
    }
    return null;
  }

  // ── Main extraction ───────────────────────────────────────
  function runExtraction() {
    const host = location.hostname;
    let jd = null;
    let jobTitleVal = null;
    let companyVal = null;

    if (host.includes("linkedin.com")) {
      jd = extractLinkedIn();
      jobTitleVal = extractLinkedInTitle();
      companyVal = extractLinkedInCompany();
    } else {
      jd = extractGeneric();
    }

    if (jd) {
      chrome.storage.local.set({
        rizzume_page_jd: jd,
        rizzume_page_url: location.href,
        rizzume_page_title: jobTitleVal,
        rizzume_page_company: companyVal,
        rizzume_page_detected_at: Date.now(),
      });
      injectBadge();
    }

    return { jd, jobTitle: jobTitleVal, company: companyVal };
  }

  // ── Badge ─────────────────────────────────────────────────
  function injectBadge() {
    if (document.getElementById("rizzume-badge")) return;
    const badge = document.createElement("div");
    badge.id = "rizzume-badge";
    badge.innerHTML = "⚡ Rizzume: JD detected";
    Object.assign(badge.style, {
      position: "fixed",
      bottom: "20px",
      right: "20px",
      background: "linear-gradient(135deg, #6c63ff, #a855f7)",
      color: "#fff",
      padding: "8px 16px",
      borderRadius: "20px",
      fontSize: "12px",
      fontWeight: "600",
      fontFamily: "system-ui, sans-serif",
      zIndex: "2147483647",
      boxShadow: "0 4px 20px rgba(108,99,255,0.5)",
      cursor: "pointer",
      userSelect: "none",
      transition: "opacity 0.3s",
    });
    badge.addEventListener("click", () => {
      badge.style.opacity = "0";
      setTimeout(() => badge.remove(), 300);
    });
    document.body.appendChild(badge);
    setTimeout(() => {
      if (badge.isConnected) {
        badge.style.opacity = "0";
        setTimeout(() => badge.remove(), 300);
      }
    }, 5000);
  }

  // ── Message listener ──────────────────────────────────────
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "EXTRACT_JD") {
      const result = runExtraction();
      sendResponse(result);
      return true;
    }
  });

  // ── Run on load + SPA observer ────────────────────────────
  runExtraction();

  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(runExtraction, 1500);
    }
  });
  observer.observe(document.body, { subtree: true, childList: true });

})();
