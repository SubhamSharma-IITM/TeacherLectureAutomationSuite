// src/utils/api.js
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Upload an audio file and start a transcription job.
 */
export async function uploadAudio(audioBlob, filename, settings) {
  const formData = new FormData();
  formData.append("file", audioBlob, filename);
  formData.append("language_hint", settings.languageHint || "auto");
  formData.append("script", settings.script || "devanagari");

  const res = await fetch(`${API_BASE}/api/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }

  return res.json(); // { job_id, status }
}

/**
 * Poll for the status/result of a transcription job.
 */
export async function pollJob(jobId) {
  const res = await fetch(`${API_BASE}/api/transcribe/${jobId}`);
  if (!res.ok) throw new Error(`Poll failed (${res.status})`);
  return res.json();
}
