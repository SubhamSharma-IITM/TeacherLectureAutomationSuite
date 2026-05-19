import { useState, useRef } from "react";
import { uploadAudio, pollJob } from "../utils/api";

/**
 * useTranscription — manages the full transcription lifecycle.
 * Upload → poll → result.
 */
export function useTranscription() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | processing | done | error
  const [result, setResult] = useState(null);
  const pollRef = useRef(null);

  const startTranscription = async (audioBlob, filename, settings) => {
    setStatus("processing");
    setResult(null);

    try {
      const { job_id } = await uploadAudio(audioBlob, filename, settings);
      setJobId(job_id);
      _startPolling(job_id);
    } catch (err) {
      setStatus("error");
      setResult({ error: err.message });
    }
  };

  const _startPolling = (id) => {
    // Poll every 2 seconds
    pollRef.current = setInterval(async () => {
      try {
        const data = await pollJob(id);

        if (data.status === "done") {
          clearInterval(pollRef.current);
          setResult(data);
          setStatus("done");
        } else if (data.status === "error") {
          clearInterval(pollRef.current);
          setResult({ error: data.error || "Transcription failed." });
          setStatus("error");
        }
        // else still "processing" → keep polling
      } catch (err) {
        clearInterval(pollRef.current);
        setStatus("error");
        setResult({ error: "Network error while polling." });
      }
    }, 2000);
  };

  const reset = () => {
    clearInterval(pollRef.current);
    setJobId(null);
    setStatus("idle");
    setResult(null);
  };

  return { jobId, status, result, startTranscription, reset };
}
