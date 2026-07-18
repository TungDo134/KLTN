import { useState } from "react";
import { FiArrowUp, FiPlus } from "react-icons/fi";
import { HiOutlineMicrophone } from "react-icons/hi";

import ModelDropdown from "../features/navigation/ModelDropdown";
// Import or keep PlusMenu, but we might just use a simple button if we want exact Claude look.
// Claude uses a + icon button on the left.
import PlusMenu from "../features/navigation/PlusMenu";

function ChatInput({ onSend, disabled, isEmptyState }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full w-full mx-auto">
      {/* Container - if isEmptyState it could be taller, but let's keep it uniform for now */}
      <div
        className={`bg-[var(--bg-panel)] rounded-2xl border border-[var(--border-main)] flex flex-col transition-all focus-within:border-[var(--text-muted)] ${isEmptyState ? "min-h-[100px] sm:min-h-[120px] p-2.5 sm:p-3" : "min-h-[52px] sm:min-h-[60px] p-2"}`}
      >
        {/* Input area */}
        <input
          type="text"
          placeholder="How can I help you today?"
          value={input}
          disabled={disabled}
          onChange={(e) => setInput(e.target.value)}
          className={`flex-1 bg-transparent outline-none text-[var(--text-main)] w-full resize-none ${isEmptyState ? "pt-1.5 sm:pt-2 px-1.5 sm:px-2 text-[15px] sm:text-base" : "px-2 sm:px-3 py-1.5 sm:py-2 text-sm"}`}
        />

        {/* Bottom actions within the input box */}
        <div className="flex items-center justify-between mt-auto pt-1.5 sm:pt-2">
          <div className="flex items-center">
            {/* The + button for attachments */}
            <button
              type="button"
              className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
            >
              <FiPlus size={18} className="sm:w-5 sm:h-5" />
            </button>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            <ModelDropdown />
            {input.trim() ? (
              <button
                type="submit"
                disabled={disabled}
                aria-label="Send message"
                className="p-1.5 bg-[var(--text-main)] text-[var(--bg-panel)] hover:opacity-80 disabled:opacity-50 rounded-lg transition-opacity"
              >
                <FiArrowUp size={18} className="sm:w-5 sm:h-5" />
              </button>
            ) : (
              <button
                type="button"
                className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                <HiOutlineMicrophone size={18} className="sm:w-5 sm:h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}

export default ChatInput;
