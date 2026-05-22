// src/utils/api.js

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Shared fetch wrapper ───────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

// ── Transcription ──────────────────────────────────────────────────────────────

/**
 * Upload an audio file and start a transcription job.
 * provider: "whisper" (default) | "grok" (for long videos)
 */
export async function uploadAudio(audioBlob, filename, settings) {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error("Audio file is empty. Please try recording again.");
  }

  const formData = new FormData();
  formData.append("file",          audioBlob, filename);
  formData.append("language_hint", settings.languageHint ?? "auto");
  formData.append("script",        settings.script        ?? "devanagari");
  formData.append("provider",      settings.provider      ?? "whisper");

  return apiFetch("/api/transcribe", {
    method: "POST",
    body:   formData,
  });
}

/**
 * Poll for the status/result of a transcription job.
 */
export async function pollJob(jobId) {
  if (!jobId) throw new Error("No job ID provided.");
  return apiFetch(`/api/transcribe/${jobId}`);
}

/**
 * Get a direct download URL for an exported transcript.
 * format: "txt" | "pdf" | "srt"
 */
export async function getExportUrl(jobId, format = "txt") {
  if (!["txt", "pdf", "srt"].includes(format)) {
    throw new Error(`Invalid format: ${format}`);
  }
  return `${API_BASE}/api/export/${jobId}?format=${format}`;
}

/**
 * Delete a job and clean up server-side files.
 */
export async function deleteJob(jobId) {
  if (!jobId) throw new Error("No job ID provided.");
  return apiFetch(`/api/transcribe/${jobId}`, { method: "DELETE" });
}

// ── Assignment ─────────────────────────────────────────────────────────────────

/**
 * Generate a practice assignment from a completed transcript.
 * questionTypes: ["mcq", "short_answer", "true_false"]
 * difficulty:    "easy" | "medium" | "hard"
 * numQuestions:  1–50
 */
export async function generateAssignment(jobId, { questionTypes, difficulty, numQuestions }) {
  if (!jobId) throw new Error("No job ID provided.");

  const formData = new FormData();
  questionTypes.forEach((t) => formData.append("question_types", t));
  formData.append("difficulty",     difficulty);
  formData.append("num_questions",  numQuestions);

  return apiFetch(`/api/assignment/${jobId}`, {
    method: "POST",
    body:   formData,
  });
}
