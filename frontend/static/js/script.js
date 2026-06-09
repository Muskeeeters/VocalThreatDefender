/**
 * VoiceShield AI — script.js
 * ==========================
 * Handles all frontend logic:
 *   - Mode tab switching (upload / record / transcript)
 *   - Audio file upload with drag-and-drop
 *   - Browser microphone recording via MediaRecorder API
 *   - Transcript input with character counter
 *   - API call to POST /api/analyze/
 *   - Animated result rendering (risk meter, score cards, verdict)
 *   - Error toasts and loading states
 */

"use strict";

/* ── Constants ──────────────────────────────────────────────── */
const API_ENDPOINT = "/api/analyze/";
const MAX_CHARS    = 5000;

/* ── State ──────────────────────────────────────────────────── */
let currentMode     = "upload";   // "upload" | "record" | "transcript"
let selectedFile    = null;       // File object from upload
let recordedBlob    = null;       // Blob from MediaRecorder
let mediaRecorder   = null;
let audioChunks     = [];
let isRecording     = false;
let vizInterval     = null;
let toastTimeout    = null;

/* ── DOM References ─────────────────────────────────────────── */
const DOM = {
  // Tabs
  tabs:           document.querySelectorAll(".mode-tab"),
  panels:         document.querySelectorAll(".input-panel"),

  // Upload
  uploadZone:     document.getElementById("upload-zone"),
  fileInput:      document.getElementById("audio-file-input"),
  fileSelected:   document.getElementById("file-selected"),
  fileName:       document.getElementById("file-name"),

  // Record
  btnRecord:      document.getElementById("btn-record"),
  btnStop:        document.getElementById("btn-stop"),
  recordStatus:   document.getElementById("record-status"),
  audioPlayback:  document.getElementById("audio-playback"),
  audioPlayer:    document.getElementById("audio-player"),
  vizBars:        document.querySelectorAll(".viz-bar"),

  // Transcript
  transcriptText: document.getElementById("transcript-text"),
  charCounter:    document.getElementById("char-counter"),

  // Analyze
  btnAnalyze:     document.getElementById("btn-analyze"),
  btnLabel:       document.getElementById("btn-label"),
  btnIcon:        document.getElementById("btn-icon"),
  spinner:        document.getElementById("spinner"),
  progressTrack:  document.getElementById("progress-track"),
  progressFill:   document.getElementById("progress-fill"),
  progressLabel:  document.getElementById("progress-label"),

  // Results
  resultsSection: document.getElementById("results-section"),
  verdictBanner:  document.getElementById("verdict-banner"),
  verdictTitle:   document.getElementById("verdict-title"),
  verdictRec:     document.getElementById("verdict-rec"),
  scoreNumber:    document.getElementById("score-number"),
  riskFill:       document.getElementById("risk-fill"),
  riskPctLabel:   document.getElementById("risk-pct-label"),

  audioRiskVal:   document.getElementById("audio-risk-val"),
  audioRiskBar:   document.getElementById("audio-risk-bar"),
  audioRiskCard:  document.getElementById("audio-risk-card"),

  textRiskVal:    document.getElementById("text-risk-val"),
  textRiskBar:    document.getElementById("text-risk-bar"),
  textRiskCard:   document.getElementById("text-risk-card"),

  procTime:       document.getElementById("proc-time"),

  // Toast
  toast:          document.getElementById("error-toast"),
  toastMsg:       document.getElementById("toast-msg"),
};

/* ══════════════════════════════════════════════════════════════
   INITIALISATION
══════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initUpload();
  initRecord();
  initTranscript();
  initAnalyze();
});

/* ══════════════════════════════════════════════════════════════
   MODE TABS
══════════════════════════════════════════════════════════════ */
function initTabs() {
  DOM.tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const mode = tab.dataset.mode;
      switchMode(mode);
    });
  });
}

function switchMode(mode) {
  currentMode = mode;

  // Update tab active state
  DOM.tabs.forEach(t => t.classList.toggle("active", t.dataset.mode === mode));

  // Show matching panel
  DOM.panels.forEach(p => p.classList.toggle("active", p.dataset.panel === mode));

  // Hide results when switching modes
  hideResults();
}

/* ══════════════════════════════════════════════════════════════
   UPLOAD MODE
══════════════════════════════════════════════════════════════ */
function initUpload() {
  // Click to browse
  DOM.uploadZone.addEventListener("click", () => DOM.fileInput.click());

  // File selected via input
  DOM.fileInput.addEventListener("change", e => {
    const file = e.target.files[0];
    if (file) handleFileSelected(file);
  });

  // Drag-and-drop
  DOM.uploadZone.addEventListener("dragover", e => {
    e.preventDefault();
    DOM.uploadZone.classList.add("dragover");
  });

  DOM.uploadZone.addEventListener("dragleave", () => {
    DOM.uploadZone.classList.remove("dragover");
  });

  DOM.uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    DOM.uploadZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelected(file);
  });
}

function handleFileSelected(file) {
  const allowed = [".wav", ".mp3", ".ogg", ".webm", ".m4a"];
  const ext = "." + file.name.split(".").pop().toLowerCase();

  if (!allowed.includes(ext)) {
    showToast(`Unsupported format: ${ext}. Please upload WAV or MP3.`);
    return;
  }

  if (file.size > 20 * 1024 * 1024) {
    showToast("File too large. Maximum size is 20 MB.");
    return;
  }

  selectedFile = file;
  DOM.fileName.textContent = `${file.name}  (${formatBytes(file.size)})`;
  DOM.fileSelected.classList.add("visible");
  const uploadPlayer = document.getElementById("upload-audio-player");
  uploadPlayer.src = URL.createObjectURL(file);
  uploadPlayer.style.display = "block";
}

/* ══════════════════════════════════════════════════════════════
   RECORD MODE
══════════════════════════════════════════════════════════════ */
function initRecord() {
  DOM.btnRecord.addEventListener("click", startRecording);
  DOM.btnStop.addEventListener("click", stopRecording);
  DOM.btnStop.disabled = true;
}

async function startRecording() {
  if (isRecording) return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    recordedBlob = null;

    // Pick best supported format
    const mimeType = getSupportedMimeType();
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

    mediaRecorder.ondataavailable = e => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      recordedBlob = blob;
      const url = URL.createObjectURL(blob);
      DOM.audioPlayer.src = url;
      DOM.audioPlayback.classList.add("visible");
      stopVizAnimation();
      stream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.start(100); // collect every 100ms
    isRecording = true;

    DOM.btnRecord.classList.add("recording");
    DOM.btnStop.disabled = false;
    DOM.recordStatus.textContent = "● Recording…";
    DOM.recordStatus.classList.add("active");
    DOM.audioPlayback.classList.remove("visible");

    startVizAnimation();

  } catch (err) {
    if (err.name === "NotAllowedError") {
      showToast("Microphone access denied. Please allow microphone permissions.");
    } else {
      showToast(`Recording error: ${err.message}`);
    }
  }
}

function stopRecording() {
  if (!isRecording || !mediaRecorder) return;

  mediaRecorder.stop();
  isRecording = false;

  DOM.btnRecord.classList.remove("recording");
  DOM.btnStop.disabled = true;
  DOM.recordStatus.textContent = "Recording saved — ready to analyse";
  DOM.recordStatus.classList.remove("active");
}

/* ── Waveform visualizer (fake bars while recording) ── */
function startVizAnimation() {
  vizInterval = setInterval(() => {
    DOM.vizBars.forEach(bar => {
      const h = isRecording
        ? Math.floor(Math.random() * 44) + 8
        : 4;
      bar.style.height = h + "px";
      bar.classList.toggle("active", isRecording);
    });
  }, 80);
}

function stopVizAnimation() {
  clearInterval(vizInterval);
  DOM.vizBars.forEach(bar => {
    bar.style.height = "4px";
    bar.classList.remove("active");
  });
}

function getSupportedMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  return types.find(t => MediaRecorder.isTypeSupported(t)) || "";
}

/* ══════════════════════════════════════════════════════════════
   TRANSCRIPT MODE
══════════════════════════════════════════════════════════════ */
function initTranscript() {
  DOM.transcriptText.addEventListener("input", () => {
    const len = DOM.transcriptText.value.length;
    DOM.charCounter.textContent = `${len} / ${MAX_CHARS}`;
    if (len >= MAX_CHARS) {
      DOM.transcriptText.value = DOM.transcriptText.value.slice(0, MAX_CHARS);
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   ANALYZE
══════════════════════════════════════════════════════════════ */
function initAnalyze() {
  DOM.btnAnalyze.addEventListener("click", runAnalysis);
}

async function runAnalysis() {
  // ── Build FormData ─────────────────────────────────────────
  const formData = new FormData();
  let hasInput = false;

  if (currentMode === "upload" && selectedFile) {
    formData.append("audio_file", selectedFile, selectedFile.name);
    hasInput = true;
  } else if (currentMode === "record" && recordedBlob) {
    // Give blob a proper filename with extension
    const ext  = recordedBlob.type.includes("ogg") ? "ogg"
               : recordedBlob.type.includes("mp4") ? "mp4"
               : "webm";
    formData.append("audio_file", recordedBlob, `recording.${ext}`);
    hasInput = true;
  } else if (currentMode === "transcript") {
    const text = DOM.transcriptText.value.trim();
    if (text) {
      formData.append("transcript", text);
      hasInput = true;
    }
  }

  if (!hasInput) {
    showToast("Please provide an audio file, a recording, or a transcript before analysing.");
    return;
  }

  // ── Set loading state ──────────────────────────────────────
  setLoading(true);
  hideResults();

  try {
    // ── Animated progress ──────────────────────────────────
    animateProgress([
      { pct: 15, label: "Uploading data…"              , delay: 0 },
      { pct: 35, label: "Extracting audio features…"   , delay: 600 },
      { pct: 60, label: "Running NLP classification…"  , delay: 1800 },
      { pct: 80, label: "Fusing risk scores…"          , delay: 3200 },
      { pct: 95, label: "Generating verdict…"          , delay: 4000 },
    ]);

    // ── API call ───────────────────────────────────────────
    const response = await fetch(API_ENDPOINT, {
      method: "POST",
      body: formData,
    });

    // Complete progress bar
    setProgress(100, "Analysis complete.");

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errData = await response.json();
        errorMsg = errData.error || errData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    const data = await response.json();
    renderResults(data);

  } catch (err) {
    showToast(err.message || "An unexpected error occurred. Please try again.");
  } finally {
    setLoading(false);
    setTimeout(() => {
      DOM.progressTrack.classList.remove("visible");
    }, 1200);
  }
}

/* ══════════════════════════════════════════════════════════════
   RESULT RENDERING
══════════════════════════════════════════════════════════════ */
function renderResults(data) {
  const { audio_risk, text_risk, final_score, verdict, recommendation, processing_ms } = data;

  // ── Verdict banner ─────────────────────────────────────────
  const verdictClass =
    verdict === "SAFE"          ? "safe"
    : verdict === "SUSPICIOUS"  ? "suspicious"
    : "critical";

  DOM.verdictBanner.className = `verdict-banner ${verdictClass}`;
  DOM.verdictTitle.textContent = verdict;
  DOM.verdictRec.textContent   = recommendation;

  // Animate score counter
  animateCounter(DOM.scoreNumber, 0, final_score, 900);

  // ── Risk meter ─────────────────────────────────────────────
  DOM.riskFill.className = `risk-fill ${verdictClass}`;
  DOM.riskPctLabel.textContent = `${final_score}%`;
  setTimeout(() => {
    DOM.riskFill.style.width = final_score + "%";
  }, 100);

  // ── Score cards ────────────────────────────────────────────
  renderScoreCard(
    DOM.audioRiskCard, DOM.audioRiskVal, DOM.audioRiskBar,
    audio_risk, "audio"
  );
  renderScoreCard(
    DOM.textRiskCard, DOM.textRiskVal, DOM.textRiskBar,
    text_risk, "text"
  );

  // ── Processing time ────────────────────────────────────────
  DOM.procTime.textContent = processing_ms != null ? `${processing_ms} ms` : "—";

  // ── Show results ───────────────────────────────────────────
  showResults();
}

function renderScoreCard(card, valEl, barEl, score, type) {
  if (score === null || score === undefined) {
    card.classList.add("null-score");
    valEl.innerHTML = `<span style="font-size:0.8rem;color:var(--text-dim)">N/A</span>`;
    barEl.style.width = "0%";
    return;
  }

  card.classList.remove("null-score");
  const rounded = Math.round(score);

  // Animate value counter
  animateCounter(valEl, 0, rounded, 1100, v => `${v}<span class="unit">%</span>`);

  setTimeout(() => {
    barEl.style.width = rounded + "%";
    // Colour the bar by risk level
    if (rounded <= 30)       barEl.style.background = "var(--green)";
    else if (rounded <= 60)  barEl.style.background = "var(--amber)";
    else                     barEl.style.background = "var(--crimson)";
  }, 150);
}

/* ══════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════ */

function setLoading(active) {
  DOM.btnAnalyze.disabled = active;
  DOM.btnAnalyze.classList.toggle("loading", active);
  DOM.btnLabel.textContent = active ? "Analysing…" : "Run Analysis";

  if (active) {
    DOM.progressTrack.classList.add("visible");
    setProgress(5, "Initialising…");
  }
}

let progressTimers = [];

function animateProgress(steps) {
  // Clear any running timers
  progressTimers.forEach(clearTimeout);
  progressTimers = [];

  steps.forEach(({ pct, label, delay }) => {
    const t = setTimeout(() => setProgress(pct, label), delay);
    progressTimers.push(t);
  });
}

function setProgress(pct, label) {
  DOM.progressFill.style.width  = pct + "%";
  DOM.progressLabel.textContent = label || "";
}

function showResults() {
  DOM.resultsSection.classList.add("visible");
  DOM.resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function hideResults() {
  DOM.resultsSection.classList.remove("visible");
}

/**
 * Animates a numeric counter from `from` to `to` over `duration` ms.
 * @param {HTMLElement} el
 * @param {number} from
 * @param {number} to
 * @param {number} duration
 * @param {Function} [formatter]  - optional fn(value) → HTML string
 */
function animateCounter(el, from, to, duration, formatter) {
  const start = performance.now();
  const fmt = formatter || (v => String(v));

  function step(now) {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased    = 1 - Math.pow(1 - progress, 3);
    const value    = Math.round(from + (to - from) * eased);
    el.innerHTML   = fmt(value);
    if (progress < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

function showToast(message) {
  DOM.toastMsg.textContent = message;
  DOM.toast.classList.add("visible");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => DOM.toast.classList.remove("visible"), 5000);
}

function formatBytes(bytes) {
  if (bytes < 1024)        return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}