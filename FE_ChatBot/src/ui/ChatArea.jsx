import { useState, useEffect, useRef } from "react";
import Message from "./Message";
import ChatInput from "./ChatInput";
import chatApi from "../services/chatApi";
import { getConversationSessionId } from "../services/conversationSession";
import extractJsonFromText from "../helper/extractJsonFromText";

function ChatArea() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const conversationSessionIdRef = useRef(getConversationSessionId());

  const handleSend = async (text) => {
    if (!text.trim()) return;

    // Thêm message của user
    setMessages((prev) => [...prev, { text, sender: "user" }]);
    setLoading(true);

    // Chuẩn bị sẵn một message rỗng cho bot để nhận stream
    setMessages((prev) => [
      ...prev,
      { text: "", sender: "bot", isStreaming: true },
    ]);

    try {
      const res = await chatApi.sendMessageStream(
        text,
        conversationSessionIdRef.current,
        (chunk, fullTextSoFar) => {
          // Tắt loading khi nhận ký tự đầu tiên
          setLoading(false);
          // Cập nhật text liên tục cho tin nhắn bot cuối cùng
          setMessages((prev) => {
            const newMsgs = [...prev];
            const lastIndex = newMsgs.length - 1;

            // Loại bỏ khối ```json... để chỉ stream ngôn ngữ tự nhiên
            const cleanStreamingText = fullTextSoFar
              .replace(/```json[\s\S]*/i, "")
              .trim();

            newMsgs[lastIndex] = {
              ...newMsgs[lastIndex],
              text: cleanStreamingText,
            };
            return newMsgs;
          });
        },
      );

      const responseText = res?.data?.response ?? "";

      // Stream hoàn tất: Nếu LLM trả về JSON trip plan, parse để hiển thị UI
      let tripData = null;
      try {
        const jsonText = extractJsonFromText(responseText);
        if (jsonText) tripData = JSON.parse(jsonText);
      } catch {
        tripData = null;
      }

      // Xóa hẳn khối JSON ra khỏi ngôn ngữ tự nhiên hiển thị
      const finalCleanText = responseText
        .replace(/```json[\s\S]*?```/i, "")
        .trim();

      if (tripData) {
        // Đặt trạng thái đang tạo giao diện (chưa có tripData)
        setMessages((prev) => {
          const newMsgs = [...prev];
          const lastIndex = newMsgs.length - 1;
          newMsgs[lastIndex] = {
            ...newMsgs[lastIndex],
            text: finalCleanText,
            isBuildingUI: true,
            isStreaming: false,
          };
          return newMsgs;
        });

        // Tạm khóa thao tác (loading = true) và dừng 1.5s để show thông báo tạo giao diện
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }

      // Cập nhật lại lần cuối cùng, thêm tripData để Message component chuyển sang UI
      setMessages((prev) => {
        const newMsgs = [...prev];
        const lastIndex = newMsgs.length - 1;

        newMsgs[lastIndex] = {
          ...newMsgs[lastIndex],
          text: finalCleanText,
          tripData,
          isBuildingUI: false,
          isStreaming: false,
        };
        return newMsgs;
      });
    } catch (err) {
      // Cập nhật tin nhắn lỗi
      setMessages((prev) => {
        const newMsgs = [...prev];
        const lastIndex = newMsgs.length - 1;
        newMsgs[lastIndex] = {
          text: err.response?.data?.detail || "Có lỗi xảy ra, thử lại nhé!",
          sender: "bot",
          isError: true,
          isStreaming: false,
        };
        return newMsgs;
      });
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
        <div className="flex flex-1 flex-col items-center justify-center px-3 sm:p-4 h-full">
          <div className="w-full max-w-3xl flex flex-col items-center justify-center mt-[-5vh] sm:mt-[-10vh]">
            {/* Greeting */}
            <div className="flex items-center gap-2 sm:gap-3 mb-6 sm:mb-8">
              <img
                src="/favicon.ico"
                alt="Logo"
                className="w-[40px] h-[33px] sm:w-[60px] sm:h-[50px]"
              />
              <h1 className="text-[22px] sm:text-[32px] font-serif text-(--text-main) font-medium tracking-wide">
                {`Happy ${
                  [
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                  ][new Date().getDay()]
                }, Tung Do`}
              </h1>
            </div>

            {/* Input */}
            <div className="w-full relative max-w-[800px]">
              <ChatInput onSend={handleSend} isEmptyState={true} />
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap justify-center gap-2 sm:gap-3 mt-4 sm:mt-5 w-full max-w-[800px]">
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border-main)] bg-transparent hover:bg-[var(--bg-hover)] text-[12px] sm:text-[13px] text-[var(--text-muted)] transition-colors">
                <span className="text-gray-400">{"</>"}</span> Code
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border-main)] bg-transparent hover:bg-[var(--bg-hover)] text-[12px] sm:text-[13px] text-[var(--text-muted)] transition-colors">
                <span className="text-gray-400">🎓</span> Learn
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border-main)] bg-transparent hover:bg-[var(--bg-hover)] text-[12px] sm:text-[13px] text-[var(--text-muted)] transition-colors">
                <span className="text-gray-400">🖊️</span> Write
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border-main)] bg-transparent hover:bg-[var(--bg-hover)] text-[12px] sm:text-[13px] text-[var(--text-muted)] transition-colors">
                <span className="text-gray-400">☕</span> Relax
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto px-3 sm:px-6 pt-4 sm:pt-6 pb-28">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, index) => (
                <Message key={index} {...msg} />
              ))}

              {/* Hiển thị placeholder loading khi đang chờ bot */}
              {loading && (
                <div className="mr-auto mb-6 flex items-center gap-1.5 py-3 px-2">
                  <div className="w-2 h-2 bg-(--text-muted) rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-(--text-muted) rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-(--text-muted) rounded-full animate-bounce"></div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          <div className="px-3 sm:px-4 pb-3 sm:pb-4 bg-(--bg-main)">
            <div className="max-w-3xl mx-auto w-full relative">
              {/* Disable input khi đang loading */}
              <ChatInput
                onSend={handleSend}
                disabled={loading}
                isEmptyState={false}
              />
              <p className="text-center text-[10px] sm:text-[11px] text-(--text-dark) mt-2 sm:mt-3">
                Mellow is AI and can make mistakes. Please double-check
                responses.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ChatArea;
