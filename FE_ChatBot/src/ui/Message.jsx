import {
  FiCopy,
  FiThumbsUp,
  FiThumbsDown,
  FiRotateCcw,
  FiEdit2,
  FiLoader,
} from "react-icons/fi";
import BotResult from "../features/result-visualize/BotResult";

function Message({ sender, text, isError, tripData, isBuildingUI }) {
  const isUser = sender === "user";

  if (isBuildingUI) {
    return (
      <div className="mr-auto text-(--text-main) mb-4 sm:mb-6 max-w-3xl w-full">
        <div className="flex items-center gap-3 p-3 sm:p-4 rounded-xl border border-(--border-main) bg-(--bg-panel) w-max max-w-full">
          <div className="animate-spin text-(--accent-color) shrink-0">
            <FiLoader size={18} />
          </div>
          <span className="text-sm font-medium truncate">
            Đang tạo phản hồi hoàn chỉnh...
          </span>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="ml-auto max-w-[85%] sm:max-w-[70%] flex flex-col items-end mb-4 sm:mb-6">
        <div className="bg-(--bg-panel) text-(--text-main) px-3 sm:px-4 py-2.5 sm:py-3 rounded-2xl text-[14px] sm:text-[15px] leading-relaxed">
          {text}
        </div>
        <div className="flex items-center gap-3 mt-2 text-gray-500 mr-2">
          <span className="text-[11px]">09:29</span>
          <button className="hover:text-gray-300 transition-colors">
            <FiRotateCcw size={13} />
          </button>
          <button className="hover:text-gray-300 transition-colors">
            <FiEdit2 size={13} />
          </button>
          <button className="hover:text-gray-300 transition-colors">
            <FiCopy size={13} />
          </button>
        </div>
      </div>
    );
  }

  if (tripData) {
    return (
      <div className="mr-auto text-(--text-main) mb-4 sm:mb-6 max-w-3xl w-full">
        <BotResult tripData={tripData} />
        <div className="flex items-center gap-3 mt-3 text-gray-500">
          <button className="hover:text-gray-300 transition-colors">
            <FiCopy size={14} />
          </button>
          <button className="hover:text-gray-300 transition-colors">
            <FiThumbsUp size={14} />
          </button>
          <button className="hover:text-gray-300 transition-colors">
            <FiThumbsDown size={14} />
          </button>
          <button className="hover:text-gray-300 transition-colors">
            <FiRotateCcw size={14} />
          </button>
        </div>
      </div>
    );
  }

  // Bot message text
  return (
    <div
      className={`mr-auto mb-4 sm:mb-6 max-w-3xl w-full text-[14px] sm:text-[15px] ${isError ? "text-red-400" : "text-[var(--text-main)]"}`}
    >
      <div className="whitespace-pre-wrap leading-relaxed">{text}</div>
      <div className="flex items-center gap-3 mt-3 text-gray-500">
        <button className="hover:text-gray-300 transition-colors">
          <FiCopy size={14} />
        </button>
        <button className="hover:text-gray-300 transition-colors">
          <FiThumbsUp size={14} />
        </button>
        <button className="hover:text-gray-300 transition-colors">
          <FiThumbsDown size={14} />
        </button>
        <button className="hover:text-gray-300 transition-colors">
          <FiRotateCcw size={14} />
        </button>
      </div>
    </div>
  );
}

export default Message;
