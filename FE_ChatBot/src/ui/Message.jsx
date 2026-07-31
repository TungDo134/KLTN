import {
  FiCopy,
  FiThumbsUp,
  FiThumbsDown,
  FiRotateCcw,
  FiEdit2,
  FiLoader,
} from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import BotResult from "../features/result-visualize/BotResult";

function MarkdownText({ text }) {
  return (
    <ReactMarkdown
      components={{
        h3: ({ children }) => (
          <h3 className="mt-4 mb-2 text-base font-semibold">{children}</h3>
        ),
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        strong: ({ children }) => (
          <strong className="font-semibold">{children}</strong>
        ),
        blockquote: ({ children }) => (
          <blockquote className="my-3 rounded-r-lg border-l-4 border-[var(--color-action-primary)] bg-[var(--color-surface-panel)] px-4 py-3 text-[var(--color-text-primary)]">
            {children}
          </blockquote>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            className="font-medium text-[var(--color-action-primary)] underline underline-offset-2 transition-opacity hover:opacity-80"
          >
            {children}
          </a>
        ),
        ul: ({ children }) => (
          <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>
        ),
        li: ({ children }) => <li>{children}</li>,
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

function Message({ sender, text, isError, tripData, isBuildingUI }) {
  const isUser = sender === "user";
  const copyText = () => {
    if (!text) return;
    navigator.clipboard.writeText(text);
  };

  if (isBuildingUI) {
    return (
      <div className="mr-auto text-(--color-text-primary) mb-4 sm:mb-6 max-w-3xl w-full">
        <div className="flex items-center gap-3 p-3 sm:p-4 rounded-xl border border-(--color-border-default) bg-(--color-surface-panel) w-max max-w-full">
          <div className="animate-spin text-(--color-action-primary) shrink-0">
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
        <div className="bg-(--color-surface-panel) text-(--color-text-primary) px-3 sm:px-4 py-2.5 sm:py-3 rounded-2xl text-[14px] sm:text-[15px] leading-relaxed">
          {text}
        </div>
        <div className="flex items-center gap-3 mt-2 text-(--color-text-subtle) mr-2">
          {/* <span className="text-[11px]">09:29</span>
          <button className="hover:text-(--color-action-primary) transition-colors">
            <FiRotateCcw size={13} />
          </button>
          <button className="hover:text-(--color-action-primary) transition-colors">
            <FiEdit2 size={13} />
          </button>
          <button className="hover:text-(--color-action-primary) transition-colors">
            <FiCopy size={13} />
          </button> */}
        </div>
      </div>
    );
  }

  if (tripData) {
    return (
      <div className="mr-auto text-(--color-text-primary) mb-4 sm:mb-6 max-w-3xl w-full">
        {text && (
          <div className="mb-4 text-[14px] sm:text-[15px] leading-relaxed">
            <MarkdownText text={text} />
          </div>
        )}
        <BotResult tripData={tripData} />
        {/* <div className="flex items-center gap-3 mt-3 text-(--color-text-subtle)">
          <button
            onClick={copyText}
            className="hover:text-(--color-action-primary) transition-colors"
          >
            <FiCopy size={14} />
          </button>
          <button className="hover:text-(--color-action-primary) transition-colors">
            <FiRotateCcw size={14} />
          </button>
        </div> */}
      </div>
    );
  }

  // Bot message text
  return (
    <div
      className={`mr-auto mb-4 sm:mb-6 max-w-3xl w-full text-[14px] sm:text-[15px] ${isError ? "text-[var(--color-danger-text)]" : "text-[var(--color-text-primary)]"}`}
    >
      <div className="leading-relaxed">
        <MarkdownText text={text} />
      </div>
      <div className="flex items-center gap-3 mt-3 text-(--color-text-subtle)">
        <button
          onClick={copyText}
          className="hover:text-(--color-action-primary) transition-colors"
        >
          <FiCopy size={14} />
        </button>
        <button className="hover:text-(--color-action-primary) transition-colors">
          <FiThumbsUp size={14} />
        </button>
        <button className="hover:text-(--color-action-primary) transition-colors">
          <FiThumbsDown size={14} />
        </button>
        <button className="hover:text-(--color-action-primary) transition-colors">
          <FiRotateCcw size={14} />
        </button>
      </div>
    </div>
  );
}

export default Message;
