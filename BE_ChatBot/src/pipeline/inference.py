"""
History-Aware RAG Inference Pipeline
FLOW:
  User question
      ↓
  [1] Rewrite question thành standalone (nếu có history)
      ↓
  [2] Multi-Query Retrieval
        ↓ LLM sinh N variations
        ↓ Search ChromaDB với từng variation
        ↓ Deduplicate → List[Document]
      ↓
  [3] Build prompt = system + chat_history + context + question
      ↓
  [4] LLM generate answer
      ↓
  [5] Lưu (user_question, answer) vào history
      ↓
  Return answer ✅
"""
import os
from collections import defaultdict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.core.llm_container import get_llm, get_system_prompt, get_model_info
# Import các module
from .rag_pipline import RAGStorage
from ..core.base_llm_model import LLMProvider

# Limit turns tránh vượt quá context window LLM
_MAX_HISTORY_TURNS = 10  # 1 turn = 1 HumanMessage + 1 AIMessage


class RAGInference:
    def __init__(self):
        print("\n⚙️ Đang khởi tạo RAG Inference Pipeline")

        # ========= COMPONENTS =========
        print(f'\n- LLM cho response user (core)')
        self.llm = get_llm()  # LLM chạy chain (core)

        print(f'\n- LLM cho rewrite question (hisory chat)')
        self.llm_rewrite = get_llm(LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")), temperature=0.2)  # LLM rewrite

        self.retriever = RAGStorage().get_multi_query_retriever()  # multi query instead of base RAG
        self.system_prompt = get_system_prompt()  # System prompt

        # ------------------------------------------------------------------ #
        # Chat history store: { session_id → [HumanMessage, AIMessage, ...] }
        # Dùng defaultdict(list) => không cần khởi tạo thủ công từng session.
        # ------------------------------------------------------------------ #
        self._history: dict[str, list] = defaultdict(list)

        # ------------------------------------------------------------------ #
        # Save model info - Just in case "WRAP" something else later.
        # Example: method ".with_structured_output" in rag_pipeline
        # ------------------------------------------------------------------ #
        self.model_info_core = get_model_info(self.llm)
        self.model_info_rewrite = get_model_info(self.llm_rewrite)

    def _get_history(self, session_id: str) -> list:
        """Trả về lịch sử hội thoại dựa vào session_id (cắt bớt nếu quá dài)."""
        history = self._history[session_id]
        # Giữ lại _MAX_HISTORY_TURNS turns gần nhất (mỗi turn = 2 message)
        max_messages = _MAX_HISTORY_TURNS * 2
        return history[-max_messages:] if len(history) > max_messages else history

    # Viết lại câu hỏi dựa trên history
    async def _rewrite_question(self, question: str, history: list) -> str:
        """
        Nếu có history, dùng LLM rewrite câu hỏi thành standalone
        để ChromaDB search chính xác hơn (không phụ thuộc ngữ cảnh trước).

        Ví dụ:
          - History: "Tôi muốn đi Đà Lạt 2 ngày"
          - Question: "Còn chỗ nào ăn ngon không?"
          → Rewrite: "Các quán ăn ngon tại Đà Lạt?"
        """
        if not history:
            return question  # Không có history -> giữ nguyên

        messages = (
                [SystemMessage(content=(
                    "Given the chat history below, rewrite the new question to be "
                    "completely standalone and searchable without needing the history. "
                    "Return ONLY the rewritten question, nothing else."
                ))]
                + history
                + [HumanMessage(content=f"New question: {question}")]
        )

        # result = await self.llm.ainvoke(messages)
        result = await self.llm_rewrite.ainvoke(messages)
        rewritten = result.content.strip()

        print(f"\n🔄 Viết lại câu hỏi (history chat) bởi [{self.model_info_rewrite}]:")
        print(f"   {rewritten}")
        return rewritten

    # Query Chroma => response context: String
    async def _retrieve_context(self, search_question: str) -> str:
        """Truy vấn ChromaDB, trả về context dạng string."""
        docs = await self.retriever.ainvoke(search_question)
        print(f"========= Tìm thấy {len(docs)} tài liệu liên quan sau khi Multi-Query =========")

        for i, doc in enumerate(docs, 1):
            # Lấy tối đa 2 dòng đầu, bỏ dòng rỗng
            lines = [l.strip() for l in doc.page_content.split('\n') if l.strip()][:2]
            # Gộp thành 1 dòng
            preview = ' '.join(lines)
            print(f"\n 📄 Doc {i}: {preview}...")

        context = "\n\n".join(doc.page_content for doc in docs)
        return context

    # Ghép prompt lại
    def _build_messages(self, history: list, context: str, question: str) -> list:
        """
        Ghép prompt hoàn chỉnh:
          SystemMessage (system_prompt + hướng dẫn + context)
          + history (HumanMessage + AIMessage xen kẽ)
          + HumanMessage (câu hỏi hiện tại)
        """
        system_content = f"""{self.system_prompt}

    Hãy trả lời câu hỏi của người dùng CHỈ dựa trên ngữ cảnh dưới đây.
    Nếu không tìm thấy thông tin, hãy nói: "Tôi không thể trả lời do không tìm thấy thông tin này trong dữ liệu của mình."

    Ngữ cảnh:
    {context}"""

        return (
                [SystemMessage(content=system_content)]
                + history
                + [HumanMessage(content=question)]
        )

    def _save_turn(self, session_id: str, question: str, answer: str) -> None:
        """Lưu lượt hội thoại vào history."""
        self._history[session_id].append(HumanMessage(content=question))
        self._history[session_id].append(AIMessage(content=answer))

    # ============================================================ #
    # PUBLIC API
    # ============================================================ #

    # ========= Hàm Async để gọi API =========
    async def predict_async(
            self,
            question: str,
            session_id: str = "default",
    ) -> str:
        """
        Main entry point — gọi từ FastAPI

        Args:
            question:   Câu hỏi của user.
            session_id: ID phiên chat (mỗi user/tab nên có ID riêng).
                        Mặc định "default" cho Gradio single-user.

        Returns:
            Câu trả lời dạng string.
        """
        history = self._get_history(session_id)

        # [1] Rewrite nếu có history
        search_question = await self._rewrite_question(question, history)

        # [2] Retrieve từ ChromaDB
        context = await self._retrieve_context(search_question)

        # [3] Build messages (system + history + question)
        messages = self._build_messages(history, context, question)

        # [4] LLM generate
        result = await self.llm.ainvoke(messages)
        answer = result.content
        print(f"\n [{get_model_info(self.llm)}]: {answer}")

        # [5] Lưu vào history
        self._save_turn(session_id, question, answer)

        return answer

    # Xóa lịch sử - API
    def clear_history(self, session_id: str = "default") -> None:
        """Xóa lịch sử của một session (dùng cho nút 'New Chat')."""
        self._history.pop(session_id, None)
        print(f"🗑️  History cleared for session: {session_id}")

    #
    def get_history_length(self, session_id: str = "default") -> int:
        """Trả về số lượt hội thoại (turns) của session."""
        return len(self._history[session_id]) // 2

# TODO: ======================================= NEW INFERENCE (IMPLEMENT LATER) =======================================
# """
# pipeline/inference.py  (UPDATED)
# Entry point cho FastAPI — thay RAGInference đơn giản bằng TripOrchestrator.
#
# BEFORE (old):  query → ChromaDB → LLM → text
# AFTER  (new):  query → QueryAnalyzer → RAG → Reranker → Recommend → Planning → LLM → text + JSON
# """
# from src.pipeline.llm import LLM
# from src.pipeline.rag_pipline import RAGStorage
# from src.pipeline.orchestrator import TripOrchestrator
#
#
# class RAGInference:
#     """
#     Backward-compatible wrapper giữ nguyên interface predict_async(question) → str
#     nhưng bên trong chạy full pipeline qua TripOrchestrator.
#     """
#
#     def __init__(self):
#         print("⚙️ Đang khởi tạo Full Trip Planning Pipeline...")
#
#         llm = LLM().get_llm()
#         retriever = RAGStorage().get_retriever()
#
#         # Thay thế chain đơn giản bằng Orchestrator
#         self.orchestrator = TripOrchestrator(llm=llm, retriever=retriever)
#
#     async def predict_async(self, question: str) -> str:
#         """
#         Pseudo:
#           result = await orchestrator.run(question)
#
#           # result = {"text": "...", "trip_plan": {...}}
#           # FastAPI / Gradio hiện tại chỉ trả text,
#           # FE sẽ parse trip_plan từ JSON embedded trong text nếu cần.
#
#           return result["text"]
#
#         NOTE: Khi FE sẵn sàng nhận JSON riêng biệt, đổi endpoint /chat
#               để trả về ChatResponse(response=text, plan=trip_plan).
#         """
#         # TODO: implement
#         pass
