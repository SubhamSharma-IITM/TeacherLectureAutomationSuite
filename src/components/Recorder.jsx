import { useState, useRef } from "react";
import { useRecorder } from "../hooks/useRecorder";
import { formatTime } from "../utils/formatTime";

export default function Recorder({ onAudioReady, disabled }) {
  const { recording, duration, audioURL, startRecording, stopRecording, reset } =
    useRecorder();
  const [submitted, setSubmitted] = useState(false);

  const handleStop = async () => {
    const blob = await stopRecording();
    if (blob) {
      setSubmitted(false); // allow re-submit view
    }
  };

  const handleSubmit = async () => {
    if (!audioURL) return;
    const response = await fetch(audioURL);
    const blob = await response.blob();
    setSubmitted(true);
    onAudioReady(blob, `recording_${Date.now()}.webm`);
  };

  const handleReset = () => {
    reset();
    setSubmitted(false);
  };

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      {/* Waveform visual */}
      <div className="flex items-end gap-1 h-12">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-150 ${
              recording
                ? "bg-orange-500 animate-pulse"
                : "bg-stone-200 dark:bg-gray-700"
            }`}
            style={{
              height: recording
                ? `${20 + Math.random() * 28}px`
                : "8px",
              animationDelay: `${i * 50}ms`,
            }}
          />
        ))}
      </div>

      {/* Timer */}
      <div className="text-2xl font-mono font-bold text-gray-800 dark:text-gray-100 tabular-nums">
        {formatTime(duration)}
      </div>

      {/* Controls */}
      <div className="flex gap-3">
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
              className="px-4 py-2.5 border border-stone-200 dark:border-gray-700 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-stone-50 dark:hover:bg-gray-800 transition-colors"
            >
              Re-record
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500">
        Speak clearly · Hindi, English, or both are supported
      </p>
    </div>
  );
}
