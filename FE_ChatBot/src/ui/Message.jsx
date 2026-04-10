import BotResult from "../features/result-visualize/BotResult";

function Message({ sender, text, isError, tripData }) {
  const isUser = sender === "user";

  if (isUser) {
    return (
      <div className="ml-auto bg-[#2a2a2a] text-white p-3 rounded-xl max-w-lg">
        {text}
      </div>
    );
  }

  if (tripData) {
    return (
      <div className="mr-auto bg-[#1f1f1f] text-white rounded-xl max-w-3xl">
        <BotResult tripData={tripData} />
      </div>
    );
  }

  // Bot message: show the text returned from API
  // (BotResult is for future structured visualization; keep it separate from chat bubbles.)
  return (
    <div
      className={[
        "mr-auto p-3 rounded-xl max-w-lg whitespace-pre-wrap",
        isError ? "bg-red-950/40 text-red-200" : "bg-[#1f1f1f] text-white",
      ].join(" ")}
    >
      {text}
    </div>
  );
}

export default Message;
