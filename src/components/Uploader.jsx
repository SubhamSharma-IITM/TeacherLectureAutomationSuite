import { useState, useRef } from "react";

const ACCEPTED = ".mp3,.mp4,.wav,.ogg,.webm,.m4a";
const ACCEPTED_MIME = new Set([
  "audio/mpeg", "audio/mp4", "audio/wav", "audio/ogg",
  "audio/webm", "audio/x-wav", "video/mp4", "audio/x-m4a",
]);
const MAX_MB = 100;

export default function Uploader({ onAudioReady, disabled }) {
  const [dragging, setDragging]       = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError]             = useState("");
  const inputRef = useRef();

  const validate = (file) => {
    if (!file) return "No file selected.";
    if (file.size === 0) return "File is empty.";
    if (file.size > MAX_MB * 1024 * 1024)
      return `File too large. Max size is ${MAX_MB} MB.`;
    // FIX: validate MIME type client-side, not just extension
    if (!ACCEPTED_MIME.has(file.type))
      return `Unsupported file type (${file.type || "unknown"}). Use MP3, WAV, OGG, WEBM, or MP4.`;
    return "";
  };

  const handleFile = (file) => {
    if (!file) return;
    const err = validate(file);
    if (err) { setError(err); setSelectedFile(null); return; }
    setError("");
    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    // FIX: handle multi-file drops gracefully — take first file, warn if multiple
    const files = e.dataTransfer.files;
    if (files.length > 1) {
      setError("Please drop one file at a time.");
      return;
    }
    handleFile(files[0]);
  };

  // FIX: reset input value so re-selecting the same file triggers onChange
  const handleClick = () => {
    if (inputRef.current) {
      inputRef.current.value = "";
      inputRef.current.click();
    }
  };

  const handleSubmit = () => {
    if (!selectedFile || disabled) return;
    onAudioReady(selectedFile, selectedFile.name);
  };

  // FIX: clear file AND error on remove
  const handleRemove = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    setError("");
  };

  const sizeMB = selectedFile
    ? (selectedFile.size / (1024 * 1024)).toFixed(1)
    : null;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        aria-label="Upload audio file"
        onKeyDown={(e) => e.key === "Enter" && handleClick()}
        className={`
          border-2 border-dashed rounded-xl px-6 py-10 text-center cursor-pointer transition-all
          ${dragging
            ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30"
            : "border-stone-200 dark:border-gray-700 hover:border-orange-300 hover:bg-stone-50 dark:hover:bg-gray-800/50"
          }
          ${disabled ? "opacity-50 pointer-events-none" : ""}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
          disabled={disabled}
        />
        <div className="text-3xl mb-3">{dragging ? "📂" : "🎵"}</div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {dragging ? "Drop your audio file here" : "Click to upload or drag & drop"}
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          MP3, MP4, WAV, OGG, WEBM · Max {MAX_MB} MB
        </p>
      </div>

      {/* Selected file preview */}
      {selectedFile && !error && (
        <div className="flex items-center justify-between bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-xl px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-xl">🎵</span>
            <div>
              <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate max-w-xs">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{sizeMB} MB</p>
            </div>
          </div>
          <button
            onClick={handleRemove}
            aria-label="Remove selected file"
            className="text-gray-400 hover:text-red-500 transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <p role="alert" className="text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-lg">
          ⚠️ {error}
        </p>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!selectedFile || disabled || !!error}
        className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-colors"
      >
        {disabled ? "Transcribing..." : "Transcribe Lecture"}
      </button>
    </div>
  );
}
