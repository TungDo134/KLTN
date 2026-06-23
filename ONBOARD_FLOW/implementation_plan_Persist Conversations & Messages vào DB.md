# Persist Conversations & Messages vào DB

> **Ứng dụng**: Mellow AI — Vietnam Travel ChatBot
> **Mục tiêu**: Lưu conversations + messages vào PostgreSQL, gắn với user. Load lại history khi quay lại.

> [!IMPORTANT]
> **Bắt buộc login mới chat được.** User chưa đăng nhập → BE trả 401 → FE chặn ở UI.

---

## Hiện trạng

| Component | Hiện tại | Vấn đề |
|-----------|----------|--------|
| FE `conversationSession.js` | Tạo UUID random, lưu `sessionStorage` | ID không gắn DB, mất khi đóng tab |
| FE `chatApi.js` | Gửi `conversationSessionId` trong body | BE nhận nhưng chỉ dùng làm key in-memory |
| BE `inference.py` | `_history[session_id]` = `defaultdict(list)` | Mất khi restart BE |
| DB `conversations`, `messages` | Bảng có sẵn, chưa có code ghi | Trống |

---

## Chia Phase mới (đã fix findings)

| Phase | Mục tiêu | Success Criteria |
|:-----:|----------|-----------------|
| **1** | Persist + round-trip conversation_id | Multi-turn chat → DB có nhiều messages cùng `conversation_id` |
| **2** | Hydrate RAG history từ DB + load messages | Restart BE → tiếp tục chat → LLM vẫn biết ngữ cảnh trước |
| **3** | Sidebar UX: list, select, new chat, delete | User thấy danh sách conversations, click vào load lại, xóa được |

> [!NOTE]
> **Điểm khác biệt chính vs plan cũ**: Phase 1 bao gồm cả FE (SSE meta + lưu conversation_id). Không có phase "BE only" vì success criteria là multi-turn → cần FE gửi lại conversation_id.

---

# Phase 1: Persist + Round-trip conversation_id

> **Scope**: BE tạo conversation trong DB, gửi `conversation_id` qua SSE meta event, FE lưu và gửi lại. Verify: nhiều messages cùng conversation trong DB.

## BE — Repository Layer

### [NEW] conversation_repository.py
📁 `src/repositories/conversation_repository.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from src.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_for_user(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        """Tìm conversation theo ID + verify ownership."""
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,       # ← ownership check
                Conversation.deleted_at.is_(None),
            )
            .first()
        )

    def create(self, user_id: str, title: str | None = None) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def touch_updated_at(self, conversation: Conversation) -> None:
        """Cập nhật updated_at — để Sidebar sort đúng."""
        conversation.updated_at = func.now()
        self.db.flush()
```

> [!WARNING]
> **[P0 — Ownership]**: Dùng `get_by_id_for_user(conversation_id, user_id)` thay vì `get_by_id(conversation_id)`. Nếu user A gửi conversation_id của user B → trả `None` → tạo conversation mới (không append vào conversation người khác).

### [NEW] message_repository.py
📁 `src/repositories/message_repository.py`

```python
from sqlalchemy.orm import Session
from src.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, conversation_id: str, role: str, content: str) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(message)
        self.db.flush()
        self.db.refresh(message)
        return message
```

---

## BE — Service Layer

### [NEW] conversation_service.py
📁 `src/services/conversation_service.py`

```python
from sqlalchemy.orm import Session
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    def get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str,
    ) -> Conversation:
        """Tìm conversation (verify ownership). Không tìm thấy → tạo mới."""
        if conversation_id:
            conv = self.conversation_repo.get_by_id_for_user(conversation_id, user_id)
            if conv:
                return conv
        # Tạo mới
        conv = self.conversation_repo.create(user_id=user_id)
        self.db.commit()
        return conv

    def save_turn(
        self,
        conversation_id: str,
        user_message: str,
        bot_response: str,
    ) -> None:
        """Lưu 1 lượt hội thoại + cập nhật updated_at."""
        self.message_repo.create(conversation_id, role="user", content=user_message)
        self.message_repo.create(conversation_id, role="assistant", content=bot_response)

        # [P1] Cập nhật updated_at để Sidebar sort đúng
        conv = self.conversation_repo.get_by_id_for_user(conversation_id, user_id="*")
        # Workaround: get conversation trực tiếp vì đây là internal call
        conv_direct = self.db.query(Conversation).get(conversation_id)
        if conv_direct:
            self.conversation_repo.touch_updated_at(conv_direct)

        self.db.commit()
```

> [!NOTE]
> **[P1 — updated_at]**: `touch_updated_at()` gọi mỗi khi save turn. Model `Conversation.updated_at` chỉ có `server_default`, không có `onupdate` → phải set thủ công.

---

## BE — Schema

### [MODIFY] schemas/chat.py
📁 `src/schemas/chat.py`

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    conversationSessionId: str = "default"    # giữ backward compat (sẽ xóa Phase 2)
    conversation_id: str | None = None        # DB ID — FE gửi sau lần chat đầu

class ChatResponse(BaseModel):
    response: str
```

> [!NOTE]
> **[P1 — ChatResponse]**: Không thêm `conversation_id` vào `ChatResponse` vì endpoint `/chat/stream` trả `StreamingResponse`, không dùng schema. Conversation ID truyền qua SSE `event: meta`.

---

## BE — Router

### [MODIFY] routers/chat.py
📁 `src/api/routers/chat.py`

```python
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.api.deps_chat import get_inference_service
from src.db.session import get_db
from src.models.user import User
from src.pipeline.inference import RAGInference
from src.schemas.chat import ChatRequest, ChatResponse
from src.services.conversation_service import ConversationService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    engine: RAGInference = Depends(get_inference_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conversation = conv_service.get_or_create_conversation(
        request.conversation_id, current_user.id,
    )
    response_text = await engine.predict_async(request.prompt, conversation.id)
    conv_service.save_turn(conversation.id, request.prompt, response_text)
    return ChatResponse(response=response_text)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    engine: RAGInference = Depends(get_inference_service),
    current_user: User = Depends(get_current_user),    # bắt buộc login
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conversation = conv_service.get_or_create_conversation(
        request.conversation_id, current_user.id,
    )

    async def event_generator():
        # [P1] Gửi conversation_id qua SSE named event TRƯỚC content
        meta = json.dumps({"conversation_id": conversation.id}, ensure_ascii=False)
        yield f"event: meta\ndata: {meta}\n\n"

        # Stream content
        full_response = ""
        async for token in engine.predict_stream(request.prompt, conversation.id):
            full_response += token
            yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"

        # Lưu messages vào DB sau khi stream xong
        conv_service.save_turn(conversation.id, request.prompt, full_response)

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## FE — Sửa SSE parser + lưu conversation_id

### [MODIFY] chatApi.js
📁 `src/services/chatApi.js`

> [!WARNING]
> **[P2 — SSE parser]**: `readStream` hiện chỉ parse `data:`. Cần thêm parse `event:` để route `meta` event sang `onMeta` callback, còn token vẫn giữ format cũ.

```js
const BASE_URL = import.meta.env.VITE_FASTAPI_URL;

if (!BASE_URL) {
  throw new Error("VITE_FASTAPI_URL not found");
}

/**
 * Đọc SSE stream, phân biệt event types:
 * - event: meta → gọi onMeta({ conversation_id })
 * - data: <token> → gọi onProgress(token, fullText)
 * - data: [DONE]  → kết thúc
 */
const readStream = async (response, onProgress, onMeta) => {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const lines = event.split("\n");

      // Kiểm tra có event type không (VD: "event: meta")
      const eventTypeLine = lines.find((l) => l.startsWith("event: "));
      const eventType = eventTypeLine ? eventTypeLine.slice(7).trim() : null;

      // Lấy data lines
      const dataLines = lines
        .filter((l) => l.startsWith("data: "))
        .map((l) => l.slice(6));
      const data = dataLines.join("\n");

      if (!data) continue;
      if (data === "[DONE]") return fullText;

      if (eventType === "meta") {
        // SSE meta event → parse JSON → gọi onMeta
        const metaObj = JSON.parse(data);
        onMeta?.(metaObj);
      } else {
        // Token content → parse JSON → gọi onProgress
        const token = JSON.parse(data);
        fullText += token;
        onProgress(token, fullText);
      }
    }
  }

  return fullText;
};

const chatApi = {
  /**
   * @param {string} prompt
   * @param {string|null} conversationId - DB conversation ID (null = tạo mới)
   * @param {function} onProgress - (chunk, fullText) => void
   * @param {function} onMeta - ({ conversation_id }) => void
   */
  sendMessageStream: async (prompt, conversationId, onProgress, onMeta) => {
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify({
        prompt,
        conversation_id: conversationId || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw { response: { data: error } };
    }

    const responseText = await readStream(response, onProgress, onMeta);
    return { data: { response: responseText } };
  },
};

export default chatApi;
```

### [MODIFY] ChatArea.jsx
📁 `src/ui/ChatArea.jsx`

Thay `conversationSessionIdRef` bằng `conversationId` state từ DB:

```jsx
function ChatArea() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);   // ← DB ID
  const bottomRef = useRef(null);

  const handleSend = async (text) => {
    // ... (giữ nguyên phần thêm user message + bot placeholder)

    try {
      const res = await chatApi.sendMessageStream(
        text,
        conversationId,              // ← gửi DB ID (null lần đầu)
        (chunk, fullTextSoFar) => {
          // ... onProgress giữ nguyên
        },
        (meta) => {
          // Nhận conversation_id từ BE (chỉ lần đầu)
          if (meta.conversation_id) {
            setConversationId(meta.conversation_id);
          }
        },
      );
      // ... phần xử lý response giữ nguyên
    }
  };
}
```

### [DELETE] conversationSession.js

Không cần nữa — FE nhận `conversation_id` từ BE, không tự tạo UUID.

---

## Verification — Phase 1

```
1. Login → gửi message đầu tiên
   → verify: DB có 1 conversation + 2 messages (user + assistant)
   → verify: FE nhận conversation_id qua SSE meta event

2. Gửi message thứ 2 (FE gửi conversation_id kèm request)
   → verify: DB có thêm 2 messages CÙNG conversation_id
   → verify: LLM response có context từ message trước (in-memory history)

3. Thử gửi conversation_id của user khác
   → verify: BE tạo conversation MỚI (không append vào conversation người khác)

4. Chat khi chưa login
   → verify: BE trả 401 Unauthorized
```

---

# Phase 2: Hydrate RAG history từ DB + Load messages

> **Scope**: Khi tiếp tục conversation (sau restart BE), load messages từ DB để LLM vẫn biết ngữ cảnh trước. Thêm API get messages.

## Vấn đề cần giải quyết

> [!WARNING]
> **[P1 — RAG history gap]**: `RAGInference._history` là in-memory dict. Sau restart BE → dict trống → `_rewrite_question()` không có history → LLM mất ngữ cảnh. FE hiển thị messages từ DB nhưng LLM "quên" hết.

## BE — Hydrate history

### [MODIFY] inference.py
📁 `src/pipeline/inference.py`

Thêm method hydrate history từ DB messages:

```python
from langchain_core.messages import HumanMessage, AIMessage

def hydrate_history(self, session_id: str, messages: list[dict]) -> None:
    """Load messages từ DB vào in-memory history.
    
    Args:
        session_id: conversation_id từ DB
        messages: list of {role, content} từ DB, sorted by created_at asc
    """
    if session_id in self._history and self._history[session_id]:
        return  # Đã có history → không cần load lại

    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    self._history[session_id] = history
```

### [MODIFY] routers/chat.py

Trước khi stream, hydrate history nếu conversation đã tồn tại:

```python
@router.post("/chat/stream")
async def chat_stream(...):
    # ... get_or_create_conversation ...

    # Hydrate RAG history từ DB (nếu conversation đã có messages)
    if request.conversation_id:
        msg_repo = MessageRepository(db)
        db_messages = msg_repo.get_by_conversation_id(conversation.id)
        engine.hydrate_history(
            conversation.id,
            [{"role": m.role, "content": m.content} for m in db_messages],
        )

    # ... event_generator ...
```

---

## BE — API get messages

### [MODIFY] message_repository.py

Thêm method:

```python
def get_by_conversation_id(self, conversation_id: str) -> list[Message]:
    return (
        self.db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
```

### [NEW] schemas — thêm response models

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Auto-generate title

Trong `ConversationService.save_turn()`, tự tạo title từ message đầu tiên:

```python
def save_turn(self, conversation_id, user_message, bot_response):
    self.message_repo.create(conversation_id, "user", user_message)
    self.message_repo.create(conversation_id, "assistant", bot_response)

    conv = self.db.query(Conversation).get(conversation_id)
    if conv:
        self.conversation_repo.touch_updated_at(conv)
        if not conv.title:
            conv.title = user_message[:100]
            self.db.flush()

    self.db.commit()
```

---

## Verification — Phase 2

```
1. Chat vài turn → restart BE → gửi message tiếp (FE gửi conversation_id)
   → verify: LLM response vẫn có context (VD: "Bạn hỏi về Đà Lạt lúc trước...")
   → verify: _history[conversation_id] được hydrate từ DB

2. Check DB: conversation có title = message đầu tiên (cắt 100 ký tự)
3. Check DB: conversation.updated_at thay đổi sau mỗi turn
```

---

# Phase 3: Sidebar UX

> **Scope**: List conversations, select/switch, new chat, soft delete.

## BE — API conversations

### [NEW] routers/conversation.py
📁 `src/api/routers/conversation.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.user import User
from src.schemas.chat import ConversationSummary, MessageResponse
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    return conv_service.get_conversations_by_user(current_user.id)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    # Verify ownership
    conv = conv_service.conversation_repo.get_by_id_for_user(
        conversation_id, current_user.id
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv_service.message_repo.get_by_conversation_id(conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conv_service.delete_conversation(conversation_id, current_user.id)
```

### [MODIFY] conversation_repository.py

Thêm methods cho Phase 3:

```python
def get_by_user_id(self, user_id: str) -> list[Conversation]:
    return (
        self.db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )

def soft_delete(self, conversation: Conversation) -> None:
    conversation.deleted_at = func.now()
    self.db.flush()
```

### [MODIFY] conversation_service.py

Thêm methods:

```python
def get_conversations_by_user(self, user_id: str) -> list[Conversation]:
    return self.conversation_repo.get_by_user_id(user_id)

def delete_conversation(self, conversation_id: str, user_id: str) -> None:
    conv = self.conversation_repo.get_by_id_for_user(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    self.conversation_repo.soft_delete(conv)
    self.db.commit()
```

### [MODIFY] schemas/chat.py

Thêm:

```python
from datetime import datetime
from pydantic import ConfigDict

class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### [MODIFY] main.py

```python
from .api.routers import conversation
app.include_router(conversation.router)
```

---

## FE — Sidebar + Routing

### [NEW] services/conversationApi.js

```js
import axiosClient from "../api/axiosClient";

export const fetchConversations = async () => {
  const res = await axiosClient.get("/conversations");
  return res.data;
};

export const fetchMessages = async (conversationId) => {
  const res = await axiosClient.get(`/conversations/${conversationId}/messages`);
  return res.data;
};

export const deleteConversation = async (conversationId) => {
  await axiosClient.delete(`/conversations/${conversationId}`);
};
```

### [MODIFY] Sidebar.jsx

Thay mảng `chats` hardcode bằng data từ API. Thêm nút xóa.

### [MODIFY] ChatArea.jsx

Nhận `conversationId` từ route params, load messages khi select conversation.

### [MODIFY] App.jsx

```jsx
<Route path="home" element={<ChatArea />} />
<Route path="c/:conversationId" element={<ChatArea />} />
```

---

## Verification — Phase 3

```
1. Login → Sidebar hiển thị danh sách conversations (từ DB, mới nhất trước)
2. Click conversation → ChatArea load lại messages
3. Tiếp tục chat → messages append, updated_at thay đổi → conversation nhảy lên đầu Sidebar
4. Click "New Chat" → ChatArea reset, conversationId = null
5. Gửi message → tạo conversation mới → xuất hiện trên Sidebar
6. Click nút xóa → conversation biến mất khỏi Sidebar
7. Kiểm tra DB: deleted_at được set, conversation không hiện lại
```

---

## Tổng kết files

### Files mới

| File | Phase | Mô tả |
|------|:-----:|-------|
| `repositories/conversation_repository.py` | 1 | CRUD conversation + ownership check |
| `repositories/message_repository.py` | 1 | CRUD message |
| `services/conversation_service.py` | 1 | get_or_create + save_turn + delete |
| `api/routers/conversation.py` | 3 | API list/get/delete conversations |
| `FE services/conversationApi.js` | 3 | FE gọi API conversations |

### Files sửa

| File | Phase | Thay đổi |
|------|:-----:|----------|
| `schemas/chat.py` | 1, 2, 3 | `conversation_id` field + response schemas |
| `api/routers/chat.py` | 1, 2 | Conversation service + SSE meta + hydrate + bắt buộc login |
| `pipeline/inference.py` | 2 | Thêm `hydrate_history()` |
| `main.py` | 3 | Register conversation router |
| `FE chatApi.js` | 1 | Parse SSE `event: meta`, gửi/nhận `conversation_id` |
| `FE ChatArea.jsx` | 1, 3 | `conversationId` state + load history |
| `FE Sidebar.jsx` | 3 | List conversations từ DB + nút xóa |
| `FE App.jsx` | 3 | Route `/c/:conversationId` |

### Files xóa

| File | Phase | Lý do |
|------|:-----:|-------|
| `FE conversationSession.js` | 1 | FE nhận ID từ BE, không tự tạo UUID |
