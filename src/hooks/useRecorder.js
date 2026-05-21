import { useState, useRef, useEffect, useCallback } from "react";

// Preferred MIME types in priority order
const MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function getSupportedMimeType() {
  return MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

/**
 * useRecorder — MediaRecorder hook for capturing mic audio.
 * Returns recording state, duration, audioURL, and controls.
 */
export function useRecorder() {
  const [recording, setRecording]   = useState(false);
  const [duration, setDuration]     = useState(0);
  const [audioURL, setAudioURL]     = useState(null);
  const [error, setError]           = useState(""); // FIX: surface errors as state, not alert()

  const mediaRecorderRef  = useRef(null);
  const chunksRef         = useRef([]);
  const timerRef          = useRef(null);
  const blobResolverRef   = useRef(null);
  const streamRef         = useRef(null); // FIX: track stream separately for reliable cleanup

  const startRecording = useCallback(async () => {
    setError("");

    // FIX: check MediaRecorder API availability (not supported in some browsers/contexts)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,   // FIX: echo and noise reduction for lecture recording
          noiseSuppression: true,
          sampleRate: 16000,        // Whisper's preferred sample rate
        },
      });
      streamRef.current = stream;

      const mimeType = getSupportedMimeType();
      const mediaRecorder = new MediaRecorder(stream, {
        ...(mimeType && { mimeType }), // FIX: only set mimeType if one is supported
      });

      chunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        // FIX: use detected mimeType for the blob, not hardcoded "audio/webm"
        const blob = new Blob(chunksRef.current, {
          type: mimeType || "audio/webm",
        });
        const url = URL.createObjectURL(blob);
        setAudioURL(url);

        if (blobResolverRef.current) {
          blobResolverRef.current(blob);
          blobResolverRef.current = null;
        }

        // FIX: stop tracks via streamRef, not the closure variable
        streamRef.current?.getTracks().forEach((t) => t.stop());
      };

      // FIX: handle unexpected recorder errors
      mediaRecorder.onerror = (e) => {
        setError(`Recording error: ${e.error?.message ?? "unknown error"}`);
        _cleanup();
      };

      mediaRecorder.start(250);
      setRecording(true);
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);

    } catch (err) {
      // FIX: distinguish permission denial from other errors
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setError("Microphone access denied. Please allow microphone permissions and try again.");
      } else if (err.name === "NotFoundError") {
        setError("No microphone found. Please connect a microphone and try again.");
      } else {
        setError(`Could not start recording: ${err.message}`);
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    return new Promise((resolve) => {
      blobResolverRef.current = resolve;
      if (mediaRecorderRef.current && recording) {
        mediaRecorderRef.current.stop();
        setRecording(false);
        clearInterval(timerRef.current);
      } else {
        resolve(null);
      }
    });
  }, [recording]);

  const reset = useCallback(() => {
    _cleanup();
    setAudioURL((prev) => {
      if (prev) URL.revokeObjectURL(prev); // FIX: revoke inside setter to get latest value
      return null;
    });
    setDuration(0);
    setRecording(false);
    setError("");
    chunksRef.current = [];
  }, []);

  const _cleanup = () => {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      // FIX: use ref value at cleanup time, not stale closure
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return { recording, duration, audioURL, error, startRecording, stopRecording, reset };
}
