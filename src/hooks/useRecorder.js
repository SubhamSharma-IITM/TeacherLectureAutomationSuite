import { useState, useRef, useEffect } from "react";

/**
 * useRecorder — MediaRecorder hook for capturing mic audio.
 * Returns recording state, duration, audioURL, and controls.
 */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioURL, setAudioURL] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const blobResolverRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      chunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioURL(url);
        // Resolve promise returned from stopRecording()
        if (blobResolverRef.current) {
          blobResolverRef.current(blob);
          blobResolverRef.current = null;
        }
        // Stop all tracks
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start(250); // collect chunks every 250ms
      setRecording(true);
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (err) {
      console.error("Microphone access denied:", err);
      alert("Could not access microphone. Please allow microphone permissions.");
    }
  };

  const stopRecording = () => {
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
  };

  const reset = () => {
    if (audioURL) URL.revokeObjectURL(audioURL);
    setAudioURL(null);
    setDuration(0);
    setRecording(false);
    chunksRef.current = [];
    clearInterval(timerRef.current);
  };

  // Cleanup on unmount
  useEffect(() => () => {
    clearInterval(timerRef.current);
    if (audioURL) URL.revokeObjectURL(audioURL);
  }, []);

  return { recording, duration, audioURL, startRecording, stopRecording, reset };
}
