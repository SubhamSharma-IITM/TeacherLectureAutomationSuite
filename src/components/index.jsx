// ── LanguageBadge ──────────────────────────────────────────────────────────────
export function LanguageBadge({ detectedLanguage, languageMix = {} }) {
  const labels = { hi: "Hindi", en: "English", "hi+en": "Hinglish" };
  const colors = {
    hi: "bg-orange-500",
    en: "bg-blue-500",
    "hi+en": "bg-purple-500",
  };

  return (
    <div className="flex items-center gap-3">
      <span
        className={`px-3 py-1 rounded-full text-white text-xs font-bold ${colors[detectedLanguage] || "bg-gray-500"}`}
      >
        {labels[detectedLanguage] || detectedLanguage?.toUpperCase()}
      </span>

      {/* Mix bar */}
      {languageMix.hindi !== undefined && (
        <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex h-2 w-24 rounded-full overflow-hidden">
            <div
              className="bg-orange-400"
              style={{ width: `${languageMix.hindi}%` }}
            />
            <div
              className="bg-purple-400"
              style={{ width: `${languageMix.mixed}%` }}
            />
            <div
              className="bg-blue-400"
              style={{ width: `${languageMix.english}%` }}
            />
          </div>
          <span>
            HI {languageMix.hindi}% · EN {languageMix.english}%
          </span>
        </div>
      )}
    </div>
  );
}

// ── ExportPanel ────────────────────────────────────────────────────────────────
export function ExportPanel({ jobId }) {
  const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const download = (format) => {
    window.open(`${API_BASE}/api/export/${jobId}?format=${format}`, "_blank");
  };

  return (
    <div className="flex gap-1.5">
      {["txt", "srt", "pdf"].map((fmt) => (
        <button
          key={fmt}
          onClick={() => download(fmt)}
          className="px-3 py-1.5 text-xs rounded-lg bg-stone-100 dark:bg-gray-800 hover:bg-stone-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium uppercase tracking-wide transition-colors"
        >
          {fmt}
        </button>
      ))}
    </div>
  );
}

// ── SettingsPanel ──────────────────────────────────────────────────────────────
import { useState } from "react";

export function SettingsPanel({ settings, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-9 h-9 rounded-lg border border-stone-200 dark:border-gray-700 flex items-center justify-center hover:bg-stone-100 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-300"
        title="Settings"
      >
        ⚙️
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-11 z-20 w-64 bg-white dark:bg-gray-900 rounded-xl border border-stone-200 dark:border-gray-700 shadow-xl p-4 space-y-4">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              Transcription Settings
            </h3>

            {/* Language hint */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Language Hint
              </label>
              <div className="mt-1.5 flex gap-1.5">
                {["auto", "hi", "en"].map((l) => (
                  <button
                    key={l}
                    onClick={() => onChange({ ...settings, languageHint: l })}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors font-medium ${
                      settings.languageHint === l
                        ? "bg-orange-500 border-orange-500 text-white"
                        : "border-stone-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-stone-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    {l === "auto" ? "Auto" : l === "hi" ? "हिंदी" : "English"}
                  </button>
                ))}
              </div>
            </div>

            {/* Script */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Hindi Script
              </label>
              <div className="mt-1.5 flex gap-1.5">
                {["devanagari", "roman"].map((s) => (
                  <button
                    key={s}
                    onClick={() => onChange({ ...settings, script: s })}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors font-medium ${
                      settings.script === s
                        ? "bg-orange-500 border-orange-500 text-white"
                        : "border-stone-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-stone-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    {s === "devanagari" ? "देवनागरी" : "Roman"}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default LanguageBadge;
