import { useState } from "react";
import Recorder from "./components/Recorder";
import Uploader from "./components/Uploader";
import TranscriptViewer from "./components/TranscriptViewer";
import LanguageBadge from "./components/LanguageBadge";
import ExportPanel from "./components/ExportPanel";
import SettingsPanel from "./components/SettingsPanel";
import { useTranscription } from "./hooks/useTranscription";

export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [settings, setSettings] = useState({
    languageHint: "auto",
    script: "devanagari",
  });
  const [activeTab, setActiveTab] = useState("upload"); // "upload" | "record"

  const { jobId, status, result, startTranscription, reset } =
    useTranscription();

  const handleAudioReady = (audioBlob, filename) => {
    startTranscription(audioBlob, filename, settings);
  };

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="min-h-screen bg-stone-50 dark:bg-gray-950 transition-colors duration-300">
        {/* Header */}
        <header className="border-b border-stone-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-orange-500 rounded-xl flex items-center justify-center text-white text-lg">
              🎙️
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
                Lecture Transcriber
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Hindi · English · Hinglish
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <SettingsPanel settings={settings} onChange={setSettings} />
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="w-9 h-9 rounded-lg border border-stone-200 dark:border-gray-700 flex items-center justify-center hover:bg-stone-100 dark:hover:bg-gray-800 transition-colors"
              title="Toggle dark mode"
            >
              {darkMode ? "☀️" : "🌙"}
            </button>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          {/* Input Section */}
          {!result && (
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-stone-200 dark:border-gray-800 overflow-hidden">
              {/* Tab switcher */}
              <div className="flex border-b border-stone-200 dark:border-gray-800">
                {["upload", "record"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 py-3 text-sm font-medium capitalize transition-colors
                      ${activeTab === tab
                        ? "bg-orange-50 dark:bg-orange-950 text-orange-600 dark:text-orange-400 border-b-2 border-orange-500"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                      }`}
                  >
                    {tab === "upload" ? "📁 Upload File" : "🎙️ Record Live"}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {activeTab === "upload" ? (
                  <Uploader onAudioReady={handleAudioReady} disabled={status === "processing"} />
                ) : (
                  <Recorder onAudioReady={handleAudioReady} disabled={status === "processing"} />
                )}
              </div>
            </div>
          )}

          {/* Processing State */}
          {status === "processing" && (
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-stone-200 dark:border-gray-800 p-8 text-center">
              <div className="w-14 h-14 mx-auto mb-4 relative">
                <div className="w-14 h-14 rounded-full border-4 border-orange-100 dark:border-orange-950" />
                <div className="w-14 h-14 rounded-full border-4 border-orange-500 border-t-transparent animate-spin absolute inset-0" />
              </div>
              <p className="font-semibold text-gray-800 dark:text-gray-100">Transcribing...</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Detecting language and transcribing your lecture
              </p>
            </div>
          )}

          {/* Result */}
          {result && status === "done" && (
            <div className="space-y-4">
              {/* Language Info Bar */}
              <div className="flex items-center justify-between bg-white dark:bg-gray-900 rounded-2xl border border-stone-200 dark:border-gray-800 px-5 py-3">
                <LanguageBadge
                  detectedLanguage={result.detected_language}
                  languageMix={result.language_mix}
                />
                <div className="flex gap-2">
                  <ExportPanel jobId={jobId} />
                  <button
                    onClick={reset}
                    className="px-3 py-1.5 text-xs rounded-lg border border-stone-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-stone-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    New Transcript
                  </button>
                </div>
              </div>

              {/* Transcript */}
              <TranscriptViewer segments={result.segments} />
            </div>
          )}

          {/* Error */}
          {status === "error" && (
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-2xl p-6 text-center">
              <p className="text-red-700 dark:text-red-300 font-medium">
                ⚠️ Transcription failed
              </p>
              <p className="text-red-500 dark:text-red-400 text-sm mt-1">
                {result?.error || "An unknown error occurred."}
              </p>
              <button
                onClick={reset}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
