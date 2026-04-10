import { useState, useEffect, useRef } from "react";
import Message from "./Message";
import ChatInput from "./ChatInput";
import chatApi from "../services/chatApi";
import extractJsonFromText from "../helper/extractJsonFromText";

function ChatArea() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const handleSend = async (text) => {
    // Thêm message của user
    setMessages((prev) => [...prev, { text, sender: "user" }]);
    setLoading(true);

    try {
      const res = await chatApi.sendMessage(text);
      const responseText = res?.data?.response ?? "";

      // Nếu LLM trả về JSON trip plan, parse để dùng cho timeline/mindmap
      let tripData = null;
      try {
        const jsonText = extractJsonFromText(responseText);
        if (jsonText) tripData = JSON.parse(jsonText);
      } catch {
        tripData = null;
      }

      // Thêm response của bot
      setMessages((prev) => [
        ...prev,
        { text: responseText, sender: "bot", tripData },
      ]);
    } catch (err) {
      // Thêm thông báo lỗi như 1 message của bot
      setMessages((prev) => [
        ...prev,
        {
          text: err.response?.data?.detail || "Có lỗi xảy ra, thử lại nhé!",
          sender: "bot",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {isEmpty ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-6">
          <h1 className="text-2xl font-semibold text-neutral-300">
            Hỏi bất kỳ điều gì về du lịch
          </h1>
          <ChatInput onSend={handleSend} />
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto px-6 pt-6 pb-28">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, index) => (
                <Message key={index} {...msg} />
              ))}

              {/* Hiển thị loading khi đang chờ bot */}
              {loading && (
                <div className="text-neutral-400 text-sm animate-pulse">
                  Đang xử lý...
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t border-neutral-800 p-4 bg-[#212121]">
            {/* Disable input khi đang loading */}
            <ChatInput onSend={handleSend} disabled={loading} />
          </div>
        </>
      )}
    </div>
  );
}

export default ChatArea;
