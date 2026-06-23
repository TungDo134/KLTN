/*
- Session tạm (save history cho từng tab chat)
- Lưu trong sessionStorage - key = 'conversationSessionId'
- BE nhận và truyền qua: schemas/chat.py => routers/chat.py => inference.py 
*/

const CONVERSATION_SESSION_ID_KEY = "conversationSessionId";

const createConversationSessionId = () => {
  if (crypto?.randomUUID) {
    return crypto.randomUUID();
  }

  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

export const getConversationSessionId = () => {
  const existingConversationSessionId = sessionStorage.getItem(
    CONVERSATION_SESSION_ID_KEY,
  );

  if (existingConversationSessionId) {
    return existingConversationSessionId;
  }

  const conversationSessionId = createConversationSessionId();
  sessionStorage.setItem(CONVERSATION_SESSION_ID_KEY, conversationSessionId);
  return conversationSessionId;
};

export const resetConversationSessionId = () => {
  const conversationSessionId = createConversationSessionId();
  sessionStorage.setItem(CONVERSATION_SESSION_ID_KEY, conversationSessionId);
  return conversationSessionId;
};
