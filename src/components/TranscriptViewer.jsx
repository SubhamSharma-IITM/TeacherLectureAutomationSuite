import { useState, useRef, useMemo, useCallback } from "react";
import { formatTime } from "../utils/formatTime";

const LANG_STYLES = {
  hi: {
    badge:  "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
    border: "border-l-orange-400",
    label:  "हिंदी",
  },
  en: {
    badge:  "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    border: "border-l-blue-400",
    label:  "English",
  },
  "hi+en": {
    badge:  "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
    border: "border-l-purple-400",
    label:  "Hinglish",
  },
};

const FALLBACK_STYLE = LANG_STYLES["en"];

export default function TranscriptViewer({ segments = [] }) {
  const [activeSegment, setActiveSegment] = useState(null);
  const [searchQuery, setSearchQuery]     = useState("");
  const [filterLang, setFilterLang]       = useState("all");
  const searchRef = useRef(null);

  // FIX: memoize filtered segments — avoids re-filtering on every render
  const filteredSegments = useMemo(() => {
    const q    = searchQuery.toLowerCase();
    return segments.filter((seg) => {
      const matchesSearch = !q || seg.text?.toLowerCase().includes(q);
      const matchesLang   = filterLang === "all" || seg.language === filterLang;
      return matchesSearch && matchesLang;
    });
  }, [segments, searchQuery, filterLang]);

  // FIX: memoize toggle handler — stable reference across renders
  const handleToggle = useCallback((id) => {
    setActiveSegment((prev) => (prev === id ? null : id));
  }, []);

  // FIX: clear search shortcut
  const handleSearchKeyDown = (e) => {
    if (e.key === "Escape") setSearchQuery("");
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-stone-200 dark:border-gray-800">

      {/* Toolbar */}
      <div className="p-4 border-b border-stone-100 dark:border-gray-800 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            ref={searchRef}
            type="text"
            placeholder="Search transcript..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            aria-label="Search transcript"
            className="w-full px-3 py-2 pr-8 text-sm rounded-lg border border-stone-200 dark:border-gray-700 bg-stone-50 dark:bg-gray-800 text-gray-800 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400"
          />
          {/* FIX: clear button inside search input */}
          {searchQuery && (
            <button
              onClick={() => { setSearchQuery(""); searchRef.current?.focus(); }}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <select
          value={filterLang}
          onChange={(e) => setFilterLang(e.target.value)}
          aria-label="Filter by language"
          className="px-3 py-2 text-sm rounded-lg border border-stone-200 dark:border-gray-700 bg-stone-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-orange-400"
        >
          <option value="all">All Languages</option>
          <option value="hi">Hindi only</option>
          <option value="en">English only</option>
          <option value="hi+en">Hinglish only</option>
        </select>
      </div>

      {/* Segments */}
      <div
        role="list"
        aria-label="Transcript segments"
        className="divide-y divide-stone-100 dark:divide-gray-800 max-h-[60vh] overflow-y-auto"
      >
        {filteredSegments.length === 0 && (
          <div className="p-8 text-center text-gray-400 dark:text-gray-500 text-sm">
            {searchQuery
              ? `No segments match "${searchQuery}".`
              : "No segments to display."
            }
          </div>
        )}

        {filteredSegments.map((seg) => {
          const style    = LANG_STYLES[seg.language] ?? FALLBACK_STYLE;
          const isActive = activeSegment === seg.id;

          return (
            <div
              key={seg.id}
              role="listitem"
              onClick={() => handleToggle(seg.id)}
              onKeyDown={(e) => e.key === "Enter" && handleToggle(seg.id)}
              tabIndex={0}
              aria-expanded={isActive}
              className={`
                flex gap-4 px-5 py-4 cursor-pointer transition-colors
                border-l-4 ${style.border}
                focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-400
                ${isActive
                  ? "bg-orange-50/60 dark:bg-orange-950/30"
                  : "hover:bg-stone-50 dark:hover:bg-gray-800/50"
                }
              `}
            >
              {/* Timestamp */}
              <div className="shrink-0 pt-0.5">
                <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
                  {formatTime(seg.start)}
                  {/* FIX: show end time when segment is active */}
                  {isActive && (
                    <span className="ml-1 text-gray-300 dark:text-gray-600">
                      → {formatTime(seg.end)}
                    </span>
                  )}
                </span>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 dark:text-gray-100 leading-relaxed">
                  {/* FIX: only call highlight when there's actually a query */}
                  {searchQuery ? highlight(seg.text ?? "", searchQuery) : (seg.text ?? "")}
                </p>
              </div>

              {/* Lang badge */}
              <div className="shrink-0">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.badge}`}>
                  {style.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-stone-100 dark:border-gray-800 flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
        <span>{filteredSegments.length} of {segments.length} segments</span>
        {/* FIX: show active filter so user knows why results are narrowed */}
        {filterLang !== "all" && (
          <button
            onClick={() => setFilterLang("all")}
            className="text-orange-500 hover:text-orange-600 transition-colors"
          >
            Clear filter ✕
          </button>
        )}
      </div>
    </div>
  );
}

// FIX: escape special regex characters in query to prevent crash on inputs like "hi+"
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlight(text, query) {
  if (!query || !text) return text;
  const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
  const parts = text.split(regex);
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5">
        {part}
      </mark>
    ) : part
  );
}
