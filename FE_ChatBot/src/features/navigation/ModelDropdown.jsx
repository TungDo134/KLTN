import { useEffect, useState } from "react";
import { FiChevronDown } from "react-icons/fi";

export default function ModelDropdown() {
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState("ChatGPT");

  // Click ra ngoài tự đóng
  useEffect(() => {
    const handleClick = () => setOpen(false);
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  //   Fake content choose model
  const models = [
    {
      name: "ChatGPT Plus",
      desc: "Most capable for ambitious work",
      upgrade: true,
    },
    {
      name: "ChatGPT Go",
      desc: "Most efficient for everyday tasks",
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
        className="flex items-center gap-1 bg-neutral-900 px-3 py-1 rounded-lg text-sm hover:bg-neutral-800"
      >
        {model}
        <FiChevronDown size={14} />
      </button>

      {/* dropdown choose model */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-[#2a2a2a] border border-neutral-700 rounded-xl shadow-xl p-2">
          {models.map((m) => (
            <div
              key={m.name}
              onClick={() => {
                setModel(m.name);
                setOpen(false);
              }}
              className={`p-3 rounded-lg cursor-pointer hover:bg-neutral-800 transition
              ${model === m.name ? "border border-blue-500" : ""}
              `}
            >
              <div className="flex justify-between">
                <span>{m.name}</span>

                {m.upgrade && (
                  <span className="text-sm bg-[#212121] px-2 py-0.5 rounded-xl">
                    Upgrade
                  </span>
                )}
              </div>

              <p className="text-xs text-neutral-400 mt-1">{m.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
