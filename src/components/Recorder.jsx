import { useState, useEffect, useRef } from "react";
import { useRecorder } from "../hooks/useRecorder";
import { formatTime } from "../utils/formatTime";

const MAX_DURATION_S = 300; // FIX: 5 minute recording limit

export default function Recorder({ onAudioReady, disabled }) {
  const { recording, duration, audioURL, startRecording, stopRecording, reset } =
    useRecorder();

  const [submitted, setSubmitted]   = useState(false);
  const [error, setError]           = useState("");
  // FIX: stable waveform heights — random values in render cause flicker every re-render
  const waveHeights = useRef(
    Array.from({ length: 20 }, () => 20 + Math.floor(Math.random() * 28))
  );

  // FIX: auto-stop recording at MAX_DURATION_S
  useEffect(() => {
    if (recording && duration >= MAX_DURATION_S) {
      handleStop();
    }
  }, [recording, duration]);

  // FIX: clean up object URL on unmount to avoid memory leaks
  useEffect(() => {
    return () => {
      if (audioURL) URL.revokeObjectURL(audioURL);
    };
  }, [audioURL]);

  const handleStop = async () => {
    const blob = await stopRecording();
    if (blob) {
      setSubmitted(false);
      setError("");
    }
  };

  const handleSubmit = async () => {
    if (!audioURL || submitted) return;
    setError("");
    try {
      const response = await fetch(audioURL);
      const blob = await response.blob();

      // FIX: guard against empty recording
      if (blob.size === 0) {
        setError("Recording is empty. Please try again.");
        return;
      }

      setSubmitted(true);
      onAudioReady(blob, `recording_${Date.now()}.webm`);
    } catch {
      setError("Failed to process recording. Please try again.");
    }
  };

  const handleReset = () => {
    reset();
    setSubmitted(false);
    setError("");
  };

  return (
    <div className="flex flex-col items-center gap-6 py-4">

      {/* Waveform visual */}
      <div className="flex items-end gap-1 h-12">
        {waveHeights.current.map((h, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-150 ${
              recording
                ? "bg-orange-500 animate-pulse"
                : "bg-stone-200 dark:bg-gray-700"
            }`}
            style={{
              height: recording ? `${h}px` : "8px",
              animationDelay: `${i * 50}ms`,
            }}
          />
        ))}
      </div>

      {/* Timer + limit warning */}
      <div className="text-center">
        <div className="text-2xl font-mono font-bold text-gray-800 dark:text-gray-100 tabular-nums">
          {formatTime(duration)}
        </div>
        {/* FIX: warn user when approaching the recording limit */}
        {recording && duration >= MAX_DURATION_S - 30 && (
          <p className="text-xs text-orange-500 mt-1 animate-pulse">
            ⚠️ Recording stops at {formatTime(MAX_DURATION_S)}
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <p role="alert" className="text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-lg">
          ⚠️ {error}
        </p>
      )}

      {/* Controls */}
      <div className="flex gap-3 flex-wrap justify-center">
        {!recording && !audioURL && (
          <button
            onClick={startRecording}
            disabled={disabled}
            className="flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition-colors"
          >
            <span className="w-2 h-2 bg-white rounded-full" />
            Start Recording
          </button>
        )}

        {recording && (
          <button
            onClick={handleStop}
            className="flex items-center gap-2 px-5 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium text-sm transition-colors"
          >
            <span className="w-2 h-2 bg-white rounded-sm" />
            Stop
          </button>
        )}

        {audioURL && !recording && (
          <>
            <audio src={audioURL} controls className="h-9 rounded-lg" />
            <button
              onClick={handleSubmit}
              disabled={disabled || submitted}
              className="px-5 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition-colors"
            >
              {submitted ? "Transcribing..." : "Transcribe"}
            </button>
            <button
              onClick={handleReset}
              disabled={disabled}
              className="px-4 py-2.5 border border-stone-200 dark:border-gray-700 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-stone-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              Re-record
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500">
        Speak clearly · Hindi, English, or both are supported · Max {formatTime(MAX_DURATION_S)}
      </p>
    </div>
  );
}
