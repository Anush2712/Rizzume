/**
 * Rizzume – Background Service Worker (Manifest V3)
 * Handles cross-tab messaging and session cleanup.
 */

const API_BASE = "http://localhost:8000";
const SESSION_KEY = "rizzume_session";

// ── Lifecycle ─────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === "install") {
    console.log("[Rizzume] Installed. Open the popup to get started.");
  }
});

// ── Message Listener ──────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CLEAR_SESSION") {
    clearSession().then(() => sendResponse({ ok: true }));
    return true; // keep channel open for async
  }

  if (msg.type === "GET_API_BASE") {
    sendResponse({ apiBase: API_BASE });
    return;
  }
});

// ── Session helpers ───────────────────────────────────────
async function clearSession() {
  const stored = await chrome.storage.local.get(SESSION_KEY);
  const sessionId = stored[SESSION_KEY];
  if (sessionId) {
    try {
      await fetch(`${API_BASE}/session/${sessionId}`, { method: "DELETE" });
    } catch (err) {
      console.warn("[Rizzume] Could not delete remote session:", err.message);
    }
    await chrome.storage.local.remove(SESSION_KEY);
    console.log("[Rizzume] Session cleared:", sessionId);
  }
}

// ── Context Menu ─────────────────────────────────────────
chrome.contextMenus?.create({
  id: "rizzume-extract",
  title: "Extract JD with Rizzume",
  contexts: ["page", "selection"],
});

chrome.contextMenus?.onClicked?.addListener((info, tab) => {
  if (info.menuItemId === "rizzume-extract") {
    // Send selected text to popup via storage so popup can pick it up
    const selectedText = info.selectionText || "";
    if (selectedText) {
      chrome.storage.local.set({ rizzume_pending_jd: selectedText });
    }
    // Open popup (no programmatic way in MV3, so we just notify via storage)
  }
});
