import { FiList } from "react-icons/fi";
import { LuGitBranch } from "react-icons/lu";
import { MdTimeline } from "react-icons/md";

function ResultSwitcher({ view, setView, language = "vi" }) {
  const base =
    "flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition";

  const active =
    "bg-[var(--color-action-primary)] text-[var(--color-text-on-primary)]";
  const inactive =
    "text-[var(--color-text-secondary)] hover:text-[var(--color-action-primary)] hover:bg-[var(--color-surface-hover)]";
  const labels =
    language === "en"
      ? { text: "Text", timeline: "Timeline", mindmap: "Mindmap" }
      : { text: "Văn bản", timeline: "Dòng thời gian", mindmap: "Sơ đồ" };

  return (
    <div className="flex gap-2 mb-3">
      <button
        onClick={() => setView("text")}
        className={`${base} ${view === "text" ? active : inactive}`}
      >
        <FiList size={16} />
        {labels.text}
      </button>

      <button
        onClick={() => setView("timeline")}
        className={`${base} ${view === "timeline" ? active : inactive}`}
      >
        <MdTimeline size={16} />
        {labels.timeline}
      </button>

      <button
        onClick={() => setView("mindmap")}
        className={`${base} ${view === "mindmap" ? active : inactive}`}
      >
        <LuGitBranch size={16} />
        {labels.mindmap}
      </button>
    </div>
  );
}

export default ResultSwitcher;
