import { useState } from "react";
import { generateAssignment } from "../utils/api";

const QUESTION_TYPE_OPTIONS = [
  { value: "mcq",          label: "Multiple Choice",  icon: "🔘", description: "4 options, one correct" },
  { value: "short_answer", label: "Short Answer",     icon: "✏️",  description: "Open-ended questions" },
  { value: "true_false",   label: "True / False",     icon: "☑️",  description: "Statement judgment" },
];

const DIFFICULTY_OPTIONS = [
  { value: "easy",   label: "Easy",   color: "text-green-600  dark:text-green-400",  bg: "bg-green-50  dark:bg-green-950/30  border-green-200  dark:border-green-800"  },
  { value: "medium", label: "Medium", color: "text-orange-600 dark:text-orange-400", bg: "bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800" },
  { value: "hard",   label: "Hard",   color: "text-red-600    dark:text-red-400",    bg: "bg-red-50    dark:bg-red-950/30    border-red-200    dark:border-red-800"    },
];

export default function AssignmentPanel({ jobId }) {
  const [open, setOpen]               = useState(false);
  const [loading, setLoading]         = useState(false);
  const [assignment, setAssignment]   = useState(null);
  const [error, setError]             = useState("");

  // Config state
  const [selectedTypes, setSelectedTypes] = useState(["mcq", "short_answer"]);
  const [difficulty, setDifficulty]       = useState("medium");
  const [numQuestions, setNumQuestions]   = useState(10);

  const toggleType = (type) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.length > 1 ? prev.filter((t) => t !== type) : prev  // keep at least one
        : [...prev, type]
    );
  };

  const handleGenerate = async () => {
    if (!jobId || loading) return;
    setError("");
    setLoading(true);
    setAssignment(null);
    try {
      const result = await generateAssignment(jobId, {
        questionTypes: selectedTypes,
        difficulty,
        numQuestions,
      });
      setAssignment(result);
    } catch (err) {
      setError(err.message ?? "Failed to generate assignment.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportTxt = () => {
    if (!assignment) return;
    const lines = [
      assignment.title,
      `Difficulty: ${assignment.metadata?.difficulty ?? difficulty}`,
      `Total Questions: ${assignment.questions?.length ?? 0}`,
      "",
      ...assignment.questions.map((q, i) => {
        const lines = [`Q${i + 1}. [${q.type.toUpperCase()}] ${q.question}`];
        if (q.type === "mcq" && q.options) {
          Object.entries(q.options).forEach(([k, v]) => lines.push(`  ${k}. ${v}`));
          lines.push(`Answer: ${q.correct_answer}`);
          if (q.explanation) lines.push(`Explanation: ${q.explanation}`);
        } else if (q.type === "short_answer") {
          lines.push(`Model Answer: ${q.model_answer}`);
        } else if (q.type === "true_false") {
          lines.push(`Answer: ${q.correct_answer ? "True" : "False"}`);
          if (q.explanation) lines.push(`Explanation: ${q.explanation}`);
        }
        return lines.join("\n");
      }),
    ];
    const blob = new Blob([lines.join("\n\n")], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `assignment_${jobId.slice(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!jobId) return null;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-stone-200 dark:border-gray-800 overflow-hidden">

      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-stone-50 dark:hover:bg-gray-800/50 transition-colors"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-purple-100 dark:bg-purple-950 rounded-lg flex items-center justify-center text-purple-600 dark:text-purple-400 text-sm">
            📝
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              Generate Practice Assignment
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              AI-powered questions from this lecture
            </p>
          </div>
        </div>
        <span className={`text-gray-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>

      {/* Config panel */}
      {open && !assignment && (
        <div className="px-5 pb-5 space-y-5 border-t border-stone-100 dark:border-gray-800 pt-4">

          {/* Question types */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Question Types
            </label>
            <div className="grid grid-cols-3 gap-2">
              {QUESTION_TYPE_OPTIONS.map((opt) => {
                const active = selectedTypes.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    onClick={() => toggleType(opt.value)}
                    className={`flex flex-col items-center gap-1 px-3 py-3 rounded-xl border text-center transition-colors
                      ${active
                        ? "border-purple-400 bg-purple-50 dark:bg-purple-950/30"
                        : "border-stone-200 dark:border-gray-700 hover:bg-stone-50 dark:hover:bg-gray-800"
                      }`}
                  >
                    <span className="text-lg">{opt.icon}</span>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-200 leading-tight">
                      {opt.label}
                    </p>
                    {active && <span className="text-purple-500 text-xs">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Difficulty */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Difficulty
            </label>
            <div className="grid grid-cols-3 gap-2">
              {DIFFICULTY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setDifficulty(opt.value)}
                  className={`px-3 py-2 rounded-xl border text-sm font-medium transition-colors
                    ${difficulty === opt.value ? `${opt.bg} ${opt.color}` : "border-stone-200 dark:border-gray-700 text-gray-500 hover:bg-stone-50 dark:hover:bg-gray-800"}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Number of questions */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Number of Questions: <span className="text-purple-600 dark:text-purple-400">{numQuestions}</span>
            </label>
            <input
              type="range"
              min={5}
              max={30}
              step={5}
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>5</span><span>10</span><span>15</span><span>20</span><span>25</span><span>30</span>
            </div>
          </div>

          {error && (
            <p role="alert" className="text-xs text-red-500 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-lg">
              ⚠️ {error}
            </p>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Generating with Claude...
              </>
            ) : (
              "✨ Generate Assignment"
            )}
          </button>
        </div>
      )}

      {/* Assignment result */}
      {assignment && (
        <div className="border-t border-stone-100 dark:border-gray-800">

          {/* Assignment header */}
          <div className="px-5 py-4 bg-purple-50 dark:bg-purple-950/20 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-gray-800 dark:text-gray-100">
                {assignment.title}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {assignment.questions?.length} questions · {assignment.metadata?.difficulty}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleExportTxt}
                className="px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                ⬇ Export TXT
              </button>
              <button
                onClick={() => setAssignment(null)}
                className="px-3 py-1.5 text-xs border border-stone-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-stone-50 dark:hover:bg-gray-800 transition-colors"
              >
                Regenerate
              </button>
            </div>
          </div>

          {/* Questions */}
          <div className="divide-y divide-stone-100 dark:divide-gray-800 max-h-[70vh] overflow-y-auto">
            {assignment.questions?.map((q) => (
              <QuestionCard key={q.id} question={q} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Question card ──────────────────────────────────────────────────────────────

function QuestionCard({ question: q }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="px-5 py-4 space-y-3">
      {/* Question */}
      <div className="flex gap-3">
        <span className="shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400 rounded-full text-xs font-bold flex items-center justify-center">
          {q.id}
        </span>
        <p className="text-sm text-gray-800 dark:text-gray-100 leading-relaxed">
          {q.question}
        </p>
      </div>

      {/* MCQ options */}
      {q.type === "mcq" && q.options && (
        <div className="ml-9 grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {Object.entries(q.options).map(([key, val]) => (
            <div
              key={key}
              className={`flex gap-2 px-3 py-2 rounded-lg text-xs border transition-colors
                ${revealed && key === q.correct_answer
                  ? "bg-green-50 dark:bg-green-950/30 border-green-300 dark:border-green-700 text-green-700 dark:text-green-300 font-medium"
                  : "bg-stone-50 dark:bg-gray-800 border-stone-200 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                }`}
            >
              <span className="font-bold shrink-0">{key}.</span>
              <span>{val}</span>
            </div>
          ))}
        </div>
      )}

      {/* True/False */}
      {q.type === "true_false" && revealed && (
        <div className="ml-9">
          <span className={`text-xs font-semibold px-2 py-1 rounded-lg ${
            q.correct_answer
              ? "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300"
              : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
          }`}>
            Answer: {q.correct_answer ? "True ✓" : "False ✗"}
          </span>
        </div>
      )}

      {/* Short answer model answer */}
      {q.type === "short_answer" && revealed && (
        <div className="ml-9 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2">
          <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1">Model Answer:</p>
          <p className="text-xs text-gray-700 dark:text-gray-300">{q.model_answer}</p>
        </div>
      )}

      {/* Explanation */}
      {revealed && q.explanation && (
        <div className="ml-9 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
          <p className="text-xs text-amber-700 dark:text-amber-300">💡 {q.explanation}</p>
        </div>
      )}

      {/* Reveal toggle */}
      <div className="ml-9">
        <button
          onClick={() => setRevealed((r) => !r)}
          className="text-xs text-purple-500 hover:text-purple-600 transition-colors"
        >
          {revealed ? "Hide answer ▲" : "Show answer ▼"}
        </button>
      </div>
    </div>
  );
}
