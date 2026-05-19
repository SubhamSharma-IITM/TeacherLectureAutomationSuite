import { useState, useRef } from "react";

const ACCEPTED = ".mp3,.mp4,.wav,.ogg,.webm,.m4a";
const MAX_MB = 100;

export default function Uploader({ onAudioReady, disabled }) {
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef();

  const validate = (file) => {
    if (!file) return "No file selected.";
    if (file.size > MAX_MB * 1024 * 1024)
      return `File too large. Max size is ${MAX_MB} MB.`;
    return "";
  };

  const handleFile = (file) => {
    const err = validate(file);
    if (err) { setError(err); return; }
    setError("");
    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const handleSubmit = () => {
    if (!selectedFile) return;
    onAudioReady(selectedFile, selectedFile.name);
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
        onClick={() => inputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl px-6 py-10 text-center cursor-pointer transition-all
          ${dragging
            ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30"
            : "border-stone-200 dark:border-gray-700 hover:border-orange-300 hover:bg-stone-50 dark:hover:bg-gray-800/50"
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
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
            onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
            className="text-gray-400 hover:text-red-500 transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-lg">
          ⚠️ {error}
        </p>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!selectedFile || disabled || !!error}
        className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-colors"
      >
        Transcribe Lecture
      </button>
    </div>
  );
}
