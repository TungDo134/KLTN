"""
INGESTION + RETRIEVE PIPELINE
"""

# --- IMPORT ---
import os
from typing import List

import torch
from dotenv import load_dotenv

# Langchain
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
)
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

#
from pydantic import BaseModel, Field

# Embedding model
from src.core.base_embed_model import get_embedding_model, EmbeddingProvider
from src.core.base_llm_model import LLMProvider
from src.core.llm_container import get_llm, get_model_info

# --- LOAD .env ---

load_dotenv()
"""
=========== Hướng dẫn bổ sung data =========== 
- Nếu muốn thêm data, bạn chỉ cần chạy file notebook build_vector_db:
"""

# ========== Check detect GPU if CPU --> Stop ==========
if not torch.cuda.is_available():
    raise EnvironmentError(
        "Không tìm thấy GPU. Dự án này cần CUDA để cho ra hiệu suất tốt nhất."
    )

_DEVICE = "cuda"


# ============================================================
# PHASE 1: INGEST PIPELINE
# ============================================================

# --- STEP 1: FUNCTION LOAD DOCUMENT ---
def load_documents(source_data: str = os.getenv("SOURCE_DATA")):
    """Load all document in SOURCE_DATA: 'src/source_data/docs'"""
    print(f"Loading document from {source_data}")

    # check exists
    if not os.path.exists(source_data):
        raise FileNotFoundError(f"Documents directory does not exist: {source_data}")

    # load pdf + text files

    pdf_loader = DirectoryLoader(path=source_data, glob="*.pdf", loader_cls=PyPDFLoader)  # type: ignore
    txt_loader = DirectoryLoader(
        path=source_data,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )

    # documents = loader.load()
    documents = pdf_loader.load() + txt_loader.load()

    if len(documents) == 0:
        raise FileNotFoundError(
            f"No .pdf or .txt files found in {source_data}. Please add your company documents."
        )

    # check xem load được không
    print("=" * 60)
    print(f"Tổng documents: {len(documents)}")
    for doc in documents:
        print(doc.metadata["source"])

    return documents


# --- STEP 2: FUNCTION CHUNK DOC (ADVANCED LATER) ---
def split_documents(documents, chunk_size=1000, chunk_overlap=150):
    """Split documents into smaller chunks with overlap"""
    print("=" * 60)
    print("Splitting documents into chunks...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_documents(documents)

    if chunks:
        print(f"Split into {len(chunks)} chunks")
        for i, chunk in enumerate(chunks[:3]):
            print(
                f"\n[Chunk {i + 1}] {chunk.metadata['source']} | {len(chunk.page_content)} chars"
            )
            print(chunk.page_content[:100] + "...")

    return chunks


# --- STEP 3: FUNCTION CREATE/UPDATE VECTOR DB ---
def create_vector_store(chunks, persist_directory: str, embedding_model) -> Chroma:
    """
    - Embed model handle chunk to vector
    - Send all to db can time out --> Divide into parts (100 chunk/time)
    """
    print("=" * 60)
    batch_size = 100
    is_new_db = False

    # Load or create DB
    try:
        # Load
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding_model,
            collection_name="kltn_chatbot",
            collection_metadata={"hnsw:space": "cosine"},
        )
        existing_count = len(vectorstore.get()["ids"])

        if existing_count == 0:
            raise ValueError("DB rỗng, chuẩn bị tạo mới")

        print(f"📦 Load DB thành công ({existing_count} chunks đã có)")
    except Exception as e:
        # Create - Update
        print(f"📦 Tạo DB mới... ({e})")
        vectorstore = Chroma.from_documents(
            documents=chunks[:batch_size],
            collection_name="kltn_chatbot",
            embedding=embedding_model,
            persist_directory=persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )
        chunks = chunks[batch_size:]
        existing_count = 0
        is_new_db = True

    # Lọc chunk trùng dựa theo source + content
    # Lọc theo tên file != theo chunk
    if existing_count > 0:
        existing_sources = set(m["source"] for m in vectorstore.get()["metadatas"])
        chunks = [c for c in chunks if c.metadata["source"] not in existing_sources]
        print(f"⚙️  Sau lọc trùng: {len(chunks)} chunks mới cần insert")

    if not chunks:
        print("✅ Không có chunk mới, bỏ qua insert")
        return vectorstore

    # Insert theo batch với error handling
    success = batch_size if is_new_db else 0
    failed = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        try:
            vectorstore.add_documents(batch)
            success += len(batch)
            print(f"  Batch {i // batch_size + 1}: ✅ {len(batch)} chunks")
        except Exception as e:
            failed += len(batch)
            print(f"  Batch {i // batch_size + 1}: ❌ lỗi - {e}")
            continue

    print(
        f"\nHoàn tất: {success} inserted, {failed} failed | Tổng DB: {len(vectorstore.get()["ids"])}"
    )
    return vectorstore


# ============================================================
# PHASE 2: MULTI-QUERY RETRIEVER
# ============================================================

# --- Structured output schema ---
class QueryVariations(BaseModel):
    """LLM sẽ trả về đúng format này."""
    queries: List[str] = Field(
        description="Danh sách các câu hỏi biến thể để tìm kiếm tài liệu du lịch"
    )


# --- Implement multi query ---
class MultiQueryRetriever:
    """
    Custom Multi-Query Retriever cho domain du lịch Việt Nam.
    Flow:
        Original Query
            ↓
        LLM sinh N query variations (tiếng Việt, structured output)
            ↓
        Hybrid Search (Vector + BM25) với từng variation
            ↓
        Deduplicate theo page_content
            ↓
        Trả về list[Document] không trùng
    """

    # Prompt for multi query
    _PROMPT_TEMPLATE = """You are a search query expansion assistant for a Vietnamese travel knowledge base.

    Your task: Generate EXACTLY {num_variations} search query variations from the original question.

    Original question: {original_query}

    Apply each strategy EXACTLY ONCE, in order:

    Strategy A — REPHRASE
    Reword the question using different vocabulary and sentence structure.
    Same scope, same intent. No new information added.
    Example input: "What was NVIDIA's first graphics accelerator called?"
    Example output: "What is the name of NVIDIA's earliest GPU product?"

    Strategy B — ASPECT FOCUS  
    Zoom into ONE specific angle: historical context, technical specs, geography, user experience, etc.
    Pick the angle most relevant to the question.
    Example input: "What was NVIDIA's first graphics accelerator called?"
    Example output: "What was the historical significance of NVIDIA's debut graphics card launch?"

    Strategy C — SCOPE SHIFT
    Broaden OR narrow the original question.
    - Narrow: from general → specific detail
    - Broaden: from specific product → company/category level
    Example input: "What was NVIDIA's first graphics accelerator called?"
    Example output: "What graphics cards did NVIDIA release in its early years?"

    STRICT RULES:
    1. LANGUAGE: Respond in the EXACT same language as the original question.
       - English question → English answers ONLY
       - Vietnamese question → Vietnamese answers ONLY
    2. Each variation must be clearly distinct — no near-duplicates allowed
    3. Preserve the core intent of the original question
    4. Keep queries concise and optimized for semantic search
    5. Return ONLY valid JSON — no explanation, no markdown, no extra text

    Output format:
    {{
      "queries": [
        "Strategy A variation here",
        "Strategy B variation here", 
        "Strategy C variation here"
      ]
    }}"""
    def __init__(self,
                 retriever,  # EnsembleRetriever (hybrid) từ RAGStorage.get_hybrid_retriever()
                 llm,  # LLM from NVIDIA NIMs
                 num_variations: int = 3,  # số query variations
                 ):
        self.retriever = retriever
        self.num_variations = num_variations

        # Lưu model info TRƯỚC khi wrap — sau khi wrap thành RunnableSequence sẽ mất attribute
        self._model_info = get_model_info(llm)

        # Dùng structured output để đảm bảo LLM trả về đúng format
        print(f'\n- LLM cho multi query')
        self.llm_structured = llm.with_structured_output(QueryVariations)

    #  ======= Step 1: Build prompt =======
    def _build_prompt(self, original_query: str):
        return (self._PROMPT_TEMPLATE.format
                (num_variations=self.num_variations,
                 original_query=original_query))

    #  ======= Step 2: Check duplicate =======
    @staticmethod
    def _deduplicate(all_docs: List[List[Document]]) -> List[Document]:
        """Loại bỏ document trùng dựa theo 100 ký tự đầu của page_content."""
        seen = set()
        unique_docs = []
        for docs in all_docs:
            for doc in docs:
                key = doc.page_content[:100].strip()
                if key not in seen:
                    seen.add(key)
                    unique_docs.append(doc)
        return unique_docs

    #  ======= Step 3: Run chain =======
    async def ainvoke(self, query: str) -> List[Document]:
        """Hàm này sẽ gọi bên inference"""
        # 1. Tạo variations
        response: QueryVariations = await self.llm_structured.ainvoke(self._build_prompt(query))
        variations = response.queries[:self.num_variations]

        if not variations:
            print("⚠️ LLM không trả query → fallback về query gốc")
            variations = [query]

        print(f"\n🔀 Câu hỏi gốc: '{query}'")
        print(f"\n🔄 Các câu hỏi được tạo thêm (multi query) bởi [{self._model_info}]:")
        for i, v in enumerate(variations, 1):
            print(f"   {i}. {v}")

        # 2. Hybrid search từng variation
        # EnsembleRetriever xử lý Vector + BM25 bên trong — mỗi variation = 1 lần gọi
        print(f"\n🔀 Relevant Docs từng câu hỏi (Hybrid Search):")
        all_results: List[List[Document]] = []
        for i, variation in enumerate(variations, 1):
            docs = await self.retriever.ainvoke(variation)
            all_results.append(docs)
            print(f"   Query {i}: {len(docs)} relevant docs")

        # 3. Remove duplicate
        print(f"\n❌ Loại bỏ các docs mang tính trùng lặp")
        unique_docs = self._deduplicate(all_results)
        total = sum(len(r) for r in all_results)
        print(f"\n➡️ Tổng số docs sau khi Multi-Query + Hybrid : {total} docs  → {len(unique_docs)} unique docs\n")

        # 4. Trả về các relevant docs sau khi multi query + handle duplicate
        return unique_docs


# ============================================================
# PHASE 3: RETRIVAL PIPELINE
# ============================================================

class RAGStorage:
    def __init__(self, provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE):
        self.persist_directory = os.getenv("PERSIST_DIRECTORY")
        if not self.persist_directory:
            raise ValueError(f"PERSIST_DIRECTORY environment variable is not set.")

        print(f"\n- Chạy embedding model bằng: '{_DEVICE}' \n")
        # ======= Create Embedding Model =======
        self.embedding_model = get_embedding_model(provider=provider)

    # ======= FUNC 1: NẠP DỮ LIỆU (INGESTION DATA) - Run once only  =======
    def build_vector_db(self):
        """Only re-run when adding new PDFs || Texts into the folder docs/"""
        # 1. Loading the files
        documents = load_documents()

        # 2. Chunking the files
        chunks = split_documents(documents)

        # 3. Embedding and Storing in Vector DB
        vectorstore = create_vector_store(
            chunks, self.persist_directory, self.embedding_model
        )

        print(
            "\n Ingestion complete! Your documents are stored in Chroma DB and ready for RAG queries."
        )

        return vectorstore

    # ======= FUNC 2: TRUY XUẤT TÀI LIỆU =======
    def get_retriever(self):
        """Vector-only retriever — giữ lại để dùng độc lập nếu cần."""
        # Tải db từ "persist_directory"- mong muốn: "src/db/chroma_db"
        print(f"\n- Tải CSDL Chroma từ thư mục: {self.persist_directory}")

        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding_model,
            collection_name="kltn_chatbot",
        )
        # top_k
        return vectorstore.as_retriever(search_kwargs={"k": 20})

    # ======= FUNC 3: HYBRID SEARCH (VECTOR + KEY WORD) =======
    def get_hybrid_retriever(self, vector_weight: float = 0.6,
                             bm25_weight: float = 0.4) -> EnsembleRetriever:
        """
        Kết hợp Vector Search + BM25 bằng EnsembleRetriever.
        Flow:
            ChromaDB (k=20) ─┐
                              ├─ EnsembleRetriever (weighted merge) → docs
            BM25     (k=20) ─┘

        BM25 cần load toàn bộ docs từ Chroma để build index trong RAM.
        Index này được build 1 lần lúc khởi tạo, không rebuild mỗi query.

        Args:
            vector_weight: trọng số cho vector search (default 0.6)
            bm25_weight:   trọng số cho BM25 (default 0.4)
        """

        print(f"\n- Tải CSDL Chroma từ thư mục: {self.persist_directory}")
        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding_model,
            collection_name="kltn_chatbot",
        )
        # Vector retriever — k = 20 để có pool đủ lớn cho dedup sau này
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

        # BM25 chạy trên RAM ==> cần List Document => pull toàn bộ từ Chroma
        print(f"\n- Build BM25 index từ Chroma docs")
        """
        Chroma lưu trữ trên disk, trả về dict dạng:
        {
           "ids":       ["id1", "id2", ...],
           "documents": ["nội dung chunk 1", "nội dung chunk 2", ...],
           "metadatas": [{"source": "..."}, {"source": "..."}, ...]
         }"""
        chroma_data = vectorstore.get()

        # Convert sang List[Document] để BM25 hiểu
        all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(chroma_data["documents"], chroma_data["metadatas"])
        ]
        bm25_retriever = BM25Retriever.from_documents(all_docs)
        bm25_retriever.k = 20  # k=20 để tương đồng với vector retriever

        print(f"\n✅ BM25 index built: {len(all_docs)} docs")
        print(f"\n⚖️  Weights — Vector: {vector_weight} | BM25: {bm25_weight}")

        return EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[vector_weight, bm25_weight],
        )

    # ======= FUNC 4: MULTI QUERY =======
    def get_multi_query_retriever(self) -> MultiQueryRetriever:
        """Trả về MultiQueryRetriever wrapped by base retriever."""
        # base_retriever = self.get_retriever()
        hybrid_retriever = self.get_hybrid_retriever()
        llm_multi_query = get_llm(LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")))  # Chạy multi query

        return MultiQueryRetriever(
            retriever=hybrid_retriever,
            llm=llm_multi_query,
            num_variations=3,
        )
