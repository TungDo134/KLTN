import { useState } from "react";
import { FiArrowUp } from "react-icons/fi";

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
        className={`relative bg-[var(--color-surface-chat-input)] rounded-2xl border border-[var(--color-surface-chat-input)] flex flex-col transition-all focus-within:border-[var(--color-surface-sidebar)] ${isEmptyState ? "min-h-[100px] sm:min-h-[120px] p-2.5 sm:p-3" : "min-h-[52px] sm:min-h-[60px] p-2"}`}
      >
        {/* Input area */}
        <input
          type="text"
          placeholder="Tôi có thể hỗ trợ bạn gì về du lịch?"
          value={input}
          disabled={disabled}
          onChange={(e) => setInput(e.target.value)}
          className={`bg-transparent outline-none text-[var(--color-text-on-chat-input)] placeholder:text-[var(--color-text-on-chat-input)] placeholder:opacity-70 w-full pr-12 leading-relaxed ${isEmptyState ? "px-2 pt-2 sm:px-3 sm:pt-3 text-[15px] sm:text-base" : "px-2 sm:px-3 py-1.5 sm:py-2 text-sm"}`}
        />

        {input.trim() && (
          <div className="absolute right-3 bottom-3">
            <button
              type="submit"
              disabled={disabled}
              aria-label="Send message"
              className="p-1.5 bg-[var(--color-text-on-chat-input)] text-[var(--color-surface-chat-input)] hover:bg-[var(--color-surface-sidebar)] disabled:opacity-50 rounded-lg transition-colors"
            >
              <FiArrowUp size={18} className="sm:w-5 sm:h-5" />
            </button>
          </div>
        )}
      </div>
    </form>
  );
}

export default ChatInput;
