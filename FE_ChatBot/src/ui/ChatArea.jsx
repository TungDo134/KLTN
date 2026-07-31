import { useState, useEffect, useRef } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import Message from "./Message";
import ChatInput from "./ChatInput";
import chatApi from "../services/chatApi";
import { fetchMessages } from "../services/conversationApi";
import { getStoredAuthUser } from "../services/authApi";
import extractJsonFromText from "../helper/extractJsonFromText";

function stripJsonObject(text) {
  const firstBrace = text.indexOf("{");
  if (firstBrace === -1) return text;

  let depth = 0;
  for (let i = firstBrace; i < text.length; i++) {
    const ch = text[i];
    if (ch === "{") depth++;
    if (ch === "}") depth--;

    if (depth === 0) {
      return `${text.slice(0, firstBrace)}${text.slice(i + 1)}`;
    }
  }

  return text.slice(0, firstBrace);
}

function cleanBotText(text, jsonText) {
  let cleanText = text
    .replace(/```json[\s\S]*?```/i, "")
    .replace(/^\s*json\s*$/gim, "")
    .replace(/^\s*```\s*$/gim, "")
    .trim();

  if (jsonText) cleanText = cleanText.replace(jsonText, "");

  cleanText = stripJsonObject(cleanText)
    .replace(/^\s*json\s*$/gim, "")
    .replace(/^\s*```\s*$/gim, "")
    .trim();

  return cleanText
    .replace(
      /\n*Về lịch trình,[\s\S]*?(?=\n\s*(?:Budget|Ngân sách|Chi phí)\b|$)/i,
      "\n\n",
    )
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function ChatArea() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [currentUser, setCurrentUser] = useState(() => getStoredAuthUser());
  const bottomRef = useRef(null);
  const navigate = useNavigate();
  const { conversationId: routeConversationId } = useParams();
  const { onConversationChanged } = useOutletContext() ?? {};

  const displayName = currentUser?.full_name || currentUser?.email || "User";
  console.log(displayName);

  const mapDbMessage = (message) => {
    if (message.role === "user") {
      return { text: message.content, sender: "user" };
    }

    let tripData = null;
    let jsonText = null;
    try {
      jsonText = extractJsonFromText(message.content);
      if (jsonText) tripData = JSON.parse(jsonText);
    } catch {
      tripData = null;
    }

    const cleanText = cleanBotText(message.content, jsonText);

    return {
      text: cleanText,
      sender: "bot",
      tripData,
      isBuildingUI: false,
      isStreaming: false,
    };
  };

  const handleSend = async (text) => {
    if (!text.trim()) return;

    if (!localStorage.getItem("access_token")) {
      setMessages((prev) => [
        ...prev,
        {
          text: "Vui lòng đăng nhập để bắt đầu chat.",
          sender: "bot",
          isError: true,
        },
      ]);
      return;
    }

    // Thêm message của user
    setMessages((prev) => [...prev, { text, sender: "user" }]);
    setLoading(true);

    // Chuẩn bị sẵn một message rỗng cho bot để nhận stream
    setMessages((prev) => [
      ...prev,
      { text: "", sender: "bot", isStreaming: true },
    ]);

    try {
      let nextConversationId = conversationId;

      const res = await chatApi.sendMessageStream(
        text,
        conversationId,
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
              .replace(/(^|\n)\s*json\s*\n\s*\{[\s\S]*/i, "")
              .replace(/(^|\n)\s*\{[\s\S]*/i, "")
              .trim();

            newMsgs[lastIndex] = {
              ...newMsgs[lastIndex],
              text: cleanStreamingText,
            };
            return newMsgs;
          });
        },
        (meta) => {
          if (meta.conversation_id) {
            nextConversationId = meta.conversation_id;
            setConversationId(meta.conversation_id);
          }
        },
      );

      const responseText = res?.data?.response ?? "";

      // Stream hoàn tất: Nếu LLM trả về JSON trip plan, parse để hiển thị UI
      let tripData = null;
      let jsonText = null;
      try {
        jsonText = extractJsonFromText(responseText);
        if (jsonText) tripData = JSON.parse(jsonText);
      } catch {
        tripData = null;
      }

      // Xóa hẳn khối JSON ra khỏi ngôn ngữ tự nhiên hiển thị
      const finalCleanText = cleanBotText(responseText, jsonText);

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

      if (nextConversationId && routeConversationId !== nextConversationId) {
        navigate(`/conversations/${nextConversationId}`, { replace: true });
      }

      onConversationChanged?.();
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
    if (!routeConversationId) {
      setConversationId(null);
      setMessages([]);
      return;
    }

    let ignore = false;

    const loadMessages = async () => {
      setConversationId(routeConversationId);

      try {
        const data = await fetchMessages(routeConversationId);
        if (!ignore) {
          setMessages(data.map(mapDbMessage));
        }
      } catch {
        if (!ignore) {
          setMessages([
            {
              text: "Could not load this conversation.",
              sender: "bot",
              isError: true,
            },
          ]);
        }
      }
    };

    loadMessages();

    return () => {
      ignore = true;
    };
  }, [routeConversationId]);

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
                src="/android-chrome-192x192.png"
                alt="Mellow AI logo"
                className="size-16 sm:size-20 shrink-0 object-contain"
              />
              <h1 className="text-[22px] sm:text-[32px] font-serif text-(--color-text-page-subheading) font-medium tracking-wide">
                {` ${
                  [
                    "Chủ nhật",
                    "Thứ Hai",
                    "Thứ Ba",
                    "Thứ Tư",
                    "Thứ Năm",
                    "Thứ Sáu",
                    "Thứ Bảy",
                  ][new Date().getDay()]
                } vui vẻ, ${displayName}`}
              </h1>
            </div>

            {/* Input */}
            <div className="w-full relative max-w-200">
              <ChatInput onSend={handleSend} isEmptyState={true} />
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="chat-scrollbar flex-1 overflow-y-auto px-3 sm:px-6 pt-4 sm:pt-6 pb-28">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, index) => (
                <Message key={index} {...msg} />
              ))}

              {/* Hiển thị placeholder loading khi đang chờ bot */}
              {loading && (
                <div className="mr-auto mb-6 flex items-center gap-1.5 py-3 px-2">
                  <div className="w-2 h-2 bg-(--color-text-secondary) rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-(--color-text-secondary) rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-(--color-text-secondary) rounded-full animate-bounce"></div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          <div className="px-3 sm:px-4 pb-3 sm:pb-4 bg-(--color-surface-page)">
            <div className="max-w-3xl mx-auto w-full relative">
              {/* Disable input khi đang loading */}
              <ChatInput
                onSend={handleSend}
                disabled={loading}
                isEmptyState={false}
              />
              <p className="text-center text-[12px] sm:text-[11px] text-(--color-text-subtle) mt-2 sm:mt-3">
                Mellow là trí tuệ nhân tạo (AI) và có thể mắc sai sót. Vui lòng
                kiểm tra kỹ các phản hồi.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ChatArea;
