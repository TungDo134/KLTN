from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Import các module
from .llm import LLM
from .rag_pipline import RAGStorage

"""
Integration complete RAG Pipeline
FLOW: User question → Retriever → Prompt (context + question) → LLM → Answer
"""


class RAGInference:
    def __init__(self):
        print("⚙️ Đang khởi tạo RAG Inference Pipeline...")

        # 1. Khởi tạo các Component
        self.llm = LLM().get_llm()
        self.retriever = RAGStorage().get_retriever()

        # 2. Xây dựng Prompt Template
        template = """Bạn là trợ lý du lịch ảo thông minh ở VIỆT NAM. 
        Hãy trả lời câu hỏi của người dùng CHỈ dựa trên ngữ cảnh được cung cấp dưới đây.
        Nếu không thể trả lời, hãy nói "Tôi không thể trả lời do không tìm thấy thông tin này trong dữ liệu của mình".

        Ngữ cảnh:
        {context}

        Câu hỏi: {question}
        Trả lời:"""

        self.prompt = ChatPromptTemplate.from_template(template)

        # 3. Lắp ráp dây chuyền (LCEL)
        # Khi user hỏi -> Đưa câu hỏi cho Retriever tìm Document
        # -> Bỏ Document vào {context} -> Nạp vào Prompt -> Gọi LLM -> Trả ra Text
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    # 4. Hàm thực thi Async để API gọi
    async def predict_async(self, question: str) -> str:
        # ainvoke giúp server không bị treo khi chờ LLM
        response = await self.chain.ainvoke(question)
        return response


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
