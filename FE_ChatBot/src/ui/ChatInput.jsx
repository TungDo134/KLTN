import { useState } from "react";
import { FiArrowUp, FiSliders } from "react-icons/fi";

function ChatInput({
  onSend,
  disabled,
  isEmptyState,
  weightSettings,
  onWeightSettingsChange,
}) {
  const [input, setInput] = useState("");
  const [showWeightSettings, setShowWeightSettings] = useState(false);

  const vectorWeight = weightSettings.retrievalVector;
  const bm25Weight = 100 - vectorWeight;
  const contentWeight = weightSettings.recommendationContent;
  const locationWeight = 100 - contentWeight;

  const updateWeight = (field, value) => {
    onWeightSettingsChange({
      ...weightSettings,
      [field]: Number(value),
    });
  };

  const resetWeights = () => {
    onWeightSettingsChange({
      retrievalVector: 60,
      recommendationContent: 60,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full mx-auto">
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

      <button
        type="button"
        disabled={disabled}
        onClick={() => setShowWeightSettings((current) => !current)}
        className="mt-2 flex items-center gap-1.5 text-[16px] text-(--color-text-secondary) hover:text-[var(--color-action-primary)] disabled:opacity-50 transition-colors"
      >
        <FiSliders size={14} />
        Tùy chỉnh cách tìm và gợi ý
      </button>

      {showWeightSettings && (
        <div className="mt-2 rounded-xl border border-(--color-border-default) bg-[var(--color-surface-panel)] p-3 text-[var(--color-text-primary)] shadow-sm">
          <div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Cách tìm thông tin</p>
                <p className="text-[14px] text-(--color-text-secondary)">
                  {vectorWeight}% theo ý nghĩa câu hỏi · {bm25Weight}% theo từ
                  khóa
                </p>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={vectorWeight}
              disabled={disabled}
              onChange={(event) =>
                updateWeight("retrievalVector", event.target.value)
              }
              aria-label="Mức ưu tiên ý nghĩa câu hỏi"
              className="mt-2 w-full accent-[var(--color-action-primary)]"
            />
            <div className="flex justify-between text-[11px] text-[var(--color-text-subtle)]">
              <span>Ưu tiên từ khóa</span>
              <span>Ưu tiên ý nghĩa</span>
            </div>
          </div>

          <div className="mt-4 border-t border-[var(--color-border-default)] pt-3">
            <p className="text-sm font-medium">Cách chọn địa điểm</p>
            <p className="text-[14px] text-[var(--color-text-secondary)]">
              {contentWeight}% theo mức độ phù hợp · {locationWeight}% theo mức
              độ gần nhau
            </p>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={contentWeight}
              disabled={disabled}
              onChange={(event) =>
                updateWeight("recommendationContent", event.target.value)
              }
              aria-label="Mức ưu tiên sự phù hợp với nhu cầu"
              className="mt-2 w-full accent-[var(--color-action-primary)]"
            />
            <div className="flex justify-between text-[11px] text-[var(--color-text-subtle)]">
              <span>Ưu tiên gần nhau</span>
              <span>Ưu tiên phù hợp</span>
            </div>
          </div>

          <button
            type="button"
            disabled={disabled}
            onClick={resetWeights}
            className="mt-4 text-[14px] font-medium text-[var(--color-action-primary)] hover:underline disabled:opacity-50"
          >
            Đặt lại mức mặc định 60/40
          </button>
        </div>
      )}
    </form>
  );
}

export default ChatInput;
