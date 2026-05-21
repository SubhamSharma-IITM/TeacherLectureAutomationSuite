import { useState, useRef, useCallback } from "react";
import { uploadAudio, pollJob } from "../utils/api";

// How often to poll (ms) and maximum wait before giving up
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 150; // 150 × 2s = 5 minutes timeout

/**
 * useTranscription — manages the full transcription lifecycle.
 * Upload → poll → result.
 */
export function useTranscription() {
  const [jobId, setJobId]   = useState(null);
  const [status, setStatus] = useState("idle"); // idle | processing | done | error
  const [result, setResult] = useState(null);

  const pollRef     = useRef(null);
  const attemptRef  = useRef(0);  // FIX: track poll attempts to enforce timeout

  // FIX: wrap in useCallback so the function reference is stable across renders
  const startTranscription = useCallback(async (audioBlob, filename, settings) => {
    // FIX: clear any existing poll before starting a new one
    _stopPolling();

    setStatus("processing");
    setResult(null);
    setJobId(null);
    attemptRef.current = 0;

    try {
      const { job_id } = await uploadAudio(audioBlob, filename, settings);
      setJobId(job_id);
      _startPolling(job_id);
    } catch (err) {
      setStatus("error");
      // FIX: distinguish network errors from API errors
      setResult({
        error: err.response?.data?.detail ?? err.message ?? "Upload failed.",
      });
    }
  }, []);

  const _stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const _startPolling = (id) => {
    pollRef.current = setInterval(async () => {
      // FIX: enforce max poll attempts so we never poll forever
      attemptRef.current += 1;
      if (attemptRef.current > MAX_POLL_ATTEMPTS) {
        _stopPolling();
        setStatus("error");
        setResult({ error: "Transcription timed out. Please try again." });
        return;
      }

      try {
        const data = await pollJob(id);

        if (data.status === "done") {
          _stopPolling();
          // FIX: validate shape before setting — guard against malformed API response
          setResult({
            detected_language: data.detected_language ?? "unknown",
            language_mix:      data.language_mix      ?? {},
            segments:          Array.isArray(data.segments) ? data.segments : [],
            full_text:         data.full_text          ?? "",
          });
          setStatus("done");
        } else if (data.status === "error") {
          _stopPolling();
          setResult({ error: data.error ?? "Transcription failed." });
          setStatus("error");
        }
        // else still "processing" → keep polling

      } catch (err) {
        // FIX: on network error, don't give up immediately — retry up to 3 times
        if (attemptRef.current > MAX_POLL_ATTEMPTS - 3) {
          _stopPolling();
          setStatus("error");
          setResult({ error: "Network error while polling. Please check your connection." });
        }
        // else silently retry on next interval
      }
    }, POLL_INTERVAL_MS);
  };

  // FIX: wrap in useCallback for stable reference
  const reset = useCallback(() => {
    _stopPolling();
    setJobId(null);
    setStatus("idle");
    setResult(null);
    attemptRef.current = 0;
  }, []);

  return { jobId, status, result, startTranscription, reset };
}
