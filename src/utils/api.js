// src/utils/api.js

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// FIX: shared fetch wrapper — avoids repeating error handling everywhere
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

/**
 * Upload an audio file and start a transcription job.
 * Returns { job_id, status }
 */
export async function uploadAudio(audioBlob, filename, settings) {
  const formData = new FormData();
  formData.append("file", audioBlob, filename);
  formData.append("language_hint", settings.languageHint ?? "auto");
  formData.append("script", settings.script ?? "devanagari");

  // FIX: validate blob before sending — catches empty recordings early
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error("Audio file is empty. Please try recording again.");
  }

  return apiFetch("/api/transcribe", {
    method: "POST",
    body: formData,
  });
}

/**
 * Poll for the status/result of a transcription job.
 */
export async function pollJob(jobId) {
  // FIX: guard against accidental calls with no jobId
  if (!jobId) throw new Error("No job ID provided.");
  return apiFetch(`/api/transcribe/${jobId}`);
}

/**
 * Get a direct download URL for an exported transcript.
 * format: "txt" | "pdf" | "srt"
 */
export async function getExportUrl(jobId, format = "txt") {
  // FIX: returns URL directly — FileResponse from FastAPI, open in browser
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
