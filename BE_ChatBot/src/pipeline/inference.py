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
