import { useMemo } from "react";

/**
 * LanguageBadge — Displays the macro breakdown of the lecture's language mix.
 * Expects languageMix = { hindi: number, english: number, mixed: number, primary: string }
 */
export default function LanguageBadge({ languageMix = {} }) {
  const { hindi = 0, english = 0, mixed = 0, primary = "en" } = languageMix;

  // Compute a structured breakdown array for easier rendering
  const metrics = useMemo(() => {
    return [
      {
        label: "Hindi",
        pct: Math.max(0, Math.min(100, Math.round(hindi))),
        color: "bg-orange-500",
        text: "text-orange-600 dark:text-orange-400",
        bg: "bg-orange-50 dark:bg-orange-950/30",
      },
      {
        label: "English",
        pct: Math.max(0, Math.min(100, Math.round(english))),
        color: "bg-blue-500",
        text: "text-blue-600 dark:text-blue-400",
        bg: "bg-blue-50 dark:bg-blue-950/30",
      },
      {
        label: "Mixed (Hinglish)",
        pct: Math.max(0, Math.min(100, Math.round(mixed))),
        color: "bg-purple-500",
        text: "text-purple-600 dark:text-purple-400",
        bg: "bg-purple-50 dark:bg-purple-950/30",
      },
    ];
  }, [hindi, english, mixed]);

  const primaryLabel = primary === "hi" ? "Hindi dominant" : "English dominant";

  return (
    <div className="bg-white dark:bg-gray-900 border border-stone-200 dark:border-gray-800 rounded-2xl p-5 shadow-sm space-y-4">
      {/* Header Summary */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
            Language Composition
          </h3>
          <p className="text-sm font-bold text-gray-800 dark:text-gray-100 mt-0.5">
            {primaryLabel}
          </p>
        </div>
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
            primary === "hi"
              ? "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300"
              : "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
          }`}
        >
          {primary === "hi" ? "🇮🇳 HI" : "🇬🇧 EN"}
        </span>
      </div>

      {/* Stacked Progress Bar */}
      <div 
        className="w-full h-3 bg-stone-100 dark:bg-gray-800 rounded-full flex overflow-hidden"
        role="img"
        aria-label={`Language mix progress: Hindi ${hindi}%, English ${english}%, Hinglish ${mixed}%`}
      >
        {metrics.map(
          (m) =>
            m.pct > 0 && (
              <div
                key={m.label}
                style={{ width: `${m.pct}%` }}
                className={`${m.color} h-full transition-all duration-500 ease-out`}
              />
            )
        )}
      </div>

      {/* Individual Legend Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div
            key={m.label}
            className={`flex items-center justify-between p-2.5 rounded-xl border border-stone-100 dark:border-gray-800/60 ${m.bg}`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className={`w-2 h-2 rounded-full shrink-0 ${m.color}`} />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-300 truncate">
                {m.label}
              </span>
            </div>
            <span className={`text-xs font-bold tabular-nums ${m.text}`}>
              {m.pct}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
