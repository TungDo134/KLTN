import { FiList } from "react-icons/fi";
import { LuGitBranch } from "react-icons/lu";
import { MdTimeline } from "react-icons/md";

function ResultSwitcher({ view, setView }) {
  const base =
    "flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition";

  const active = "bg-neutral-700 text-white";
  const inactive = "text-neutral-400 hover:text-white hover:bg-neutral-800";

  return (
    <div className="flex gap-2 mb-3">
      <button
        onClick={() => setView("text")}
        className={`${base} ${view === "text" ? active : inactive}`}
      >
        <FiList size={16} />
        Text
      </button>

      <button
        onClick={() => setView("timeline")}
        className={`${base} ${view === "timeline" ? active : inactive}`}
      >
        <MdTimeline size={16} />
        Timeline
      </button>

      <button
        onClick={() => setView("mindmap")}
        className={`${base} ${view === "mindmap" ? active : inactive}`}
      >
        <LuGitBranch size={16} />
        Mindmap
      </button>
    </div>
  );
}

export default ResultSwitcher;
