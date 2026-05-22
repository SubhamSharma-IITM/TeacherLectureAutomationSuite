import { useState } from "react";

const PROVIDER_OPTIONS = [
  {
    value:       "whisper",
    label:       "OpenAI Whisper",
    description: "Best for files under 25 MB",
    icon:        "🎙️",
  },
  {
    value:       "grok",
    label:       "Grok (xAI)",
    description: "Best for long videos up to 90 MB",
    icon:        "⚡",
  },
];

const LANGUAGE_OPTIONS = [
  { value: "auto", label: "Auto-detect",  description: "Let AI decide" },
  { value: "hi",   label: "Hindi",        description: "Force Hindi detection" },
  { value: "en",   label: "English",      description: "Force English detection" },
];

const SCRIPT_OPTIONS = [
  { value: "devanagari", label: "Devanagari", description: "Hindi in native script (हिंदी)" },
  { value: "roman",      label: "Roman",      description: "Hindi transliterated (Hindi)" },
];

export default function SettingsPanel({ settings, onChange }) {
  const [open, setOpen] = useState(false);

  const handleChange = (key, value) => {
    onChange({ ...settings, [key]: value });
  };

  const nonDefault =
    (settings.languageHint !== "auto"       ? 1 : 0) +
    (settings.script       !== "devanagari" ? 1 : 0) +
    (settings.provider     !== "whisper"    ? 1 : 0);

  return (
    <div className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        className="relative flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-stone-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-stone-50 dark:hover:bg-gray-800 transition-colors"
      >
        ⚙️ Settings
        {nonDefault > 0 && (
          <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-orange-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {nonDefault}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />

          <div className="absolute right-0 mt-2 w-72 z-20 bg-white dark:bg-gray-900 border border-stone-200 dark:border-gray-700 rounded-2xl shadow-xl overflow-hidden">

            {/* Header */}
            <div className="px-4 py-3 border-b border-stone-100 dark:border-gray-800 flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Transcription Settings
              </p>
              {nonDefault > 0 && (
                <button
                  onClick={() => onChange({ languageHint: "auto", script: "devanagari", provider: "whisper" })}
                  className="text-xs text-orange-500 hover:text-orange-600 transition-colors"
                >
                  Reset
                </button>
              )}
            </div>

            <div className="p-4 space-y-5">

              {/* Provider */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
                  Transcription Provider
                </label>
                <div className="space-y-1.5">
                  {PROVIDER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleChange("provider", opt.value)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl border text-left transition-colors
                        ${settings.provider === opt.value
                          ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30"
                          : "border-stone-200 dark:border-gray-700 hover:bg-stone-50 dark:hover:bg-gray-800"
                        }`}
                    >
                      <div className="flex items-center gap-2">
                        <span>{opt.icon}</span>
                        <div>
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
                            {opt.label}
                          </p>
                          <p className="text-xs text-gray-400 dark:text-gray-500">
                            {opt.description}
                          </p>
                        </div>
                      </div>
                      {settings.provider === opt.value && (
                        <span className="text-orange-500 text-sm shrink-0">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language hint */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
                  Language Hint
                </label>
                <div className="space-y-1.5">
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleChange("languageHint", opt.value)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl border text-left transition-colors
                        ${settings.languageHint === opt.value
                          ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30"
                          : "border-stone-200 dark:border-gray-700 hover:bg-stone-50 dark:hover:bg-gray-800"
                        }`}
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
                          {opt.label}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          {opt.description}
                        </p>
                      </div>
                      {settings.languageHint === opt.value && (
                        <span className="text-orange-500 text-sm shrink-0">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Script */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
                  Hindi Script
                </label>
                <div className="space-y-1.5">
                  {SCRIPT_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleChange("script", opt.value)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl border text-left transition-colors
                        ${settings.script === opt.value
                          ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30"
                          : "border-stone-200 dark:border-gray-700 hover:bg-stone-50 dark:hover:bg-gray-800"
                        }`}
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
                          {opt.label}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          {opt.description}
                        </p>
                      </div>
                      {settings.script === opt.value && (
                        <span className="text-orange-500 text-sm shrink-0">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </>
      )}
    </div>
  );
}
