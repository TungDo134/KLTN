import { useEffect, useState } from "react";
import { FiChevronDown } from "react-icons/fi";

export default function ModelDropdown() {
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState("Sonnet 4.6");

  // Click ra ngoài tự đóng
  useEffect(() => {
    const handleClick = () => setOpen(false);
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  //   Fake content choose model
  const models = [
    {
      name: "Sonnet 4.6",
      desc: "Most capable for ambitious work",
    },
    {
      name: "Opus 3",
      desc: "Most efficient for everyday tasks",
      upgrade: true,
    },
    {
      name: "Haiku 4.5",
      desc: "Fastest for quick answers",
    },
  ];

  return (
    <div className="relative">
      {/* btn */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="flex items-center gap-1 bg-[var(--bg-panel)] px-3 py-1 rounded-lg text-sm hover:bg-[var(--bg-hover)]"
      >
        {model}
        <FiChevronDown size={14} />
      </button>

      {/* dropdown choose model */}
      {open && (
        <div className="absolute right-0 bottom-full sm:bottom-auto sm:top-full mb-2 sm:mb-0 sm:mt-2 w-60 sm:w-72 bg-[var(--bg-panel)] border border-[var(--border-main)] rounded-xl shadow-xl p-2 z-50">
          {models.map((m) => (
            <div
              key={m.name}
              onClick={() => {
                setModel(m.name);
                setOpen(false);
              }}
              className={`p-3 rounded-lg cursor-pointer hover:bg-[var(--bg-hover)] transition
              ${model === m.name ? "border border-[var(--border-main)] bg-[var(--bg-hover)]" : ""}
              `}
            >
              <div className="flex justify-between">
                <span>{m.name}</span>

                {m.upgrade && (
                  <span className="text-sm bg-[var(--bg-main)] text-[var(--text-muted)] px-2 py-0.5 rounded-xl">
                    Upgrade
                  </span>
                )}
              </div>

              <p className="text-xs text-[var(--text-muted)] mt-1">{m.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
