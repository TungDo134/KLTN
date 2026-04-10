import { useState } from "react";

import { FiPlus } from "react-icons/fi";

import ModelDropdown from "../features/navigation/ModelDropdown";
import PlusMenu from "../features/navigation/PlusMenu";

function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-3xl mx-auto">
      <div className="bg-[#2f2f2f] rounded-3xl px-4 py-4 flex items-center gap-3 border border-neutral-700">
        <PlusMenu />

        <input
          type="text"
          placeholder="Hôm nay bạn muốn đi đâu nào ?"
          value={input}
          disabled={disabled} // ✅ Disable input khi loading
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 bg-transparent outline-none text-sm"
        />

        {/* choose model */}
        <ModelDropdown />
      </div>
    </form>
  );
}

export default ChatInput;
