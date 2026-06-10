"""
INGESTION + RETRIEVE PIPELINE
"""

# --- IMPORT ---
import os
from typing import List
from pathlib import Path
import json
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
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

#
from pydantic import BaseModel, Field, ValidationError

# Embedding model
from src.core.base_embed_model import get_embedding_model, EmbeddingProvider
from src.core.base_llm_model import LLMProvider
from src.core.llm_container import get_llm, get_model_info

from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    wait_exponential,
    retry_if_exception_type,
)

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
_TOP_K = 20


# ============================================================
#                       INGEST PIPELINE
# ============================================================


# --- Untils Function: CONVERT JSON DATA => DOCUMENT ---
def load_json_places(data_dir: str) -> list[Document]:
    """
    **Lưu ý: Chỉ hỗ trợ file dạng JSON**
    - Load files từ (folder: `D:\KLTN\Project\BE_ChatBot\src\source_data`) => `list[Document]`.

    - page_content  : text (concat từ các field ngữ nghĩa cao)
    - metadata      : các field flat support rerank (tự build) - filter - planning
    """

    documents = []
    json_files = list(Path(data_dir).glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"Không tìm thấy file json nào trong: {data_dir}")

    print(f"📂 Tìm thấy {len(json_files)} file JSON: {[f.name for f in json_files]}")

    for file in json_files:
        with open(file, "r", encoding="utf-8") as f:
            places = json.load(f)  # list[dict]

        for place in places:
            # --- 1. Build Page Content (LLM Context - RAG) ---
            tags_str = ",".join(place.get("tags", []))

            page_content = (
                f"{place['name']} là một địa điểm thuộc {place['region']}. "
                f"Loại hình: {place.get('type', 'N/A')}. "
                f"Các hoạt động nổi bật: {tags_str}. "
                f"{place.get('description', '')} "
                f"Giờ mở cửa: {place['time']['open']} - {place['time']['close']}. "
                f"Thời gian tham quan trung bình: {place.get('avg_duration_minutes', 60)} phút. "
                f"Phí vào cửa: {place.get('entrance_fee', 0):,} VNĐ. "
                f"Thời điểm lý tưởng để đến: {place.get('best_time', 'N/A')}."
            )

            # --- 2. Build Metadata (flat fields support rerank - filter - planning) ---
            metadata = {
                # Identity
                "place_id": place["id"],
                "name": place["name"],
                "region": place["region"],
                "type": place.get("type", ""),
                "tags": tags_str,  # str vì ChromaDB không nhận list
                # Geo
                "lat": place["geo"]["lat"],
                "lng": place["geo"]["lng"],
                "address": place["geo"].get("address", ""),
                # Rating
                "rating_score": place["rating"]["score"],
                "rating_count": place["rating"]["review_count"],
                "rating_is_reliable": place["rating"]["is_reliable"],
                # Time & Cost
                "open": place["time"]["open"],
                "close": place["time"]["close"],
                "avg_duration_minutes": place.get("avg_duration_minutes", 60),
                "entrance_fee": place.get("entrance_fee", 0),
                # Extra
                "best_time": place.get("best_time", ""),
                "source_url": place["metadata"].get("source_url", ""),
            }

            documents.append(Document(page_content=page_content, metadata=metadata))

    # return
    print(f"✅ Load xong: {len(documents)} địa điểm từ {len(json_files)} file")
    return documents


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
            source = chunk.metadata.get("source") or chunk.metadata.get(
                "place_id", "unknown"
            )  # fix cho json files
            print(f"\n[Chunk {i + 1}] {source} | {len(chunk.page_content)} chars")
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
        existing_sources = set(
            m.get("source") or m.get("place_id", "")
            for m in vectorstore.get()["metadatas"]
        )
        chunks = [
            c
            for c in chunks
            if (c.metadata.get("source") or c.metadata.get("place_id", ""))
            not in existing_sources
        ]
        print(f"⚙️  Sau lọc trùng: {len(chunks)} chunks mới cần insert")

    if not chunks:
        print("✅ Không có chunk mới, bỏ qua insert")
        return vectorstore

    # Insert theo batch với error handling
    success = batch_size if is_new_db else 0
    failed = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        try:
            vectorstore.add_documents(batch)
            success += len(batch)
            print(f"  Batch {i // batch_size + 1}: ✅ {len(batch)} chunks")
        except Exception as e:
            failed += len(batch)
            print(f"  Batch {i // batch_size + 1}: ❌ lỗi - {e}")
            continue

    print(
        f"\nHoàn tất: {success} inserted, {failed} failed | Tổng DB: {len(vectorstore.get()['ids'])}"
    )
    return vectorstore


# ============================================================
#                       RERANK CONFIG
# ============================================================
class RerankerConfig:
    """
    Cấu hình Reranker — chỉnh tại đây

    MODEL OPTIONS (tiếng Việt):
        BAAI/bge-reranker-v2-m3     ← recommended, multilingual, hỗ trợ tiếng Việt tốt
        BAAI/bge-reranker-base      ← nhẹ hơn, nhanh hơn, tiếng Anh chủ yếu
        BAAI/bge-reranker-large     ← nặng hơn, chính xác hơn
    """

    MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    TOP_N: int = 20  # Số docs giữ lại sau rerank — đưa vào LLM generate


# ============================================================
#                       MULTI-QUERY RETRIEVER
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
    Generate {num_variations} search query variations for a Vietnamese travel knowledge base.

    Original: {original_query}

    STRICT RULES:
    1. LANGUAGE: Respond in the EXACT SAME LANGUAGE AS THE ORIGINAL QUESTION (IMPORTANT)
       - English question → English answers ONLY
       - Vietnamese question → Vietnamese answers ONLY
    2. Each variation must be clearly distinct — no near-duplicates allowed
    3. Preserve the core intent of the original question
    4. Keep queries concise and optimized for semantic search
    5. Return ONLY VALID JSON
    6. DO NOT include explanations, no markdown, no extra text
    7. DO NOT include function call syntax like <function=...>

    Output EXACTLY:
    {{"queries": ["variation 1", "variation 2", "variation 3"]}}
"""

    def __init__(
        self,
        retriever,  # EnsembleRetriever (hybrid) từ RAGStorage.get_hybrid_retriever()
        llm,  # LLM from NVIDIA NIMs
        num_variations: int = 3,  # số query variations
    ):
        self.retriever = retriever
        self.num_variations = num_variations

        # Lưu model info TRƯỚC khi wrap — sau khi wrap thành RunnableSequence sẽ mất attribute
        self._model_info = get_model_info(llm)

        # Dùng structured output để đảm bảo LLM trả về đúng format
        self.llm_structured = llm.with_structured_output(
            QueryVariations, method="json_mode"
        )

    #  ======= Step 1: Build prompt =======
    def _build_prompt(self, original_query: str):
        return self._PROMPT_TEMPLATE.format(
            num_variations=self.num_variations, original_query=original_query
        )

    # ===================== RETRY LLM (thử lại tối đa 3 lần - 1s/once) =====================
    @retry(
        stop=stop_after_attempt(3),
        # wait_fixed(1):        1s → 1s → 1s   # retry liên tục, dễ bị rate limit
        # wait_exponential:     1s → 2s → 4s   # tăng dần, tránh hammering API
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((ValidationError, ValueError)),
        reraise=True,  # throw exception ra ngoài sau 3 lần
    )
    async def _call_llm(self, prompt: str) -> QueryVariations:
        response = await self.llm_structured.ainvoke(prompt)
        if not response.queries:
            raise ValueError("Empty queries returned")  # trigger retry
        return response

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
        """Hàm này được gọi bên orchestrator"""
        # 1. Tạo variations
        try:
            response = await self._call_llm(self._build_prompt(query))  # dùng _call_llm
            variations = response.queries[: self.num_variations]
        except Exception as e:
            print(f"⚠️ Multi-query failed - Fallback về query gốc: {e}")
            variations = [query]  # fallback về query gốc

        print(f"\n🔀 Câu hỏi gốc: '{query}'")
        print(f"\n🔄 Các câu hỏi được tạo thêm (multi query) bởi [{self._model_info}]:")
        for i, v in enumerate(variations, 1):
            print(f"   {i}. {v}")

        # 2. Hybrid search từng variation
        # EnsembleRetriever xử lý Vector + BM25 bên trong — mỗi variation = 1 lần gọi
        print("\n🔀 Relevant Docs từng câu hỏi (Hybrid Search):")
        all_results: List[List[Document]] = []
        for i, variation in enumerate(variations, 1):
            try:
                docs = await self.retriever.ainvoke(variation)
                all_results.append(docs)
                print(f"   Query {i}: {len(docs)} relevant docs")
            except Exception as e:
                print(f"⚠️ Retriever fail query {i}: {e}")

        # 3. Remove duplicate
        print("\n❌ Loại bỏ các docs mang tính trùng lặp")
        unique_docs = self._deduplicate(all_results)
        total = sum(len(r) for r in all_results)
        print(
            f"\n➡️ Tổng số docs sau khi Multi-Query + Hybrid : {total} docs  → {len(unique_docs)} unique docs\n"
        )

        # 4. Trả về các relevant docs sau khi multi query + handle duplicate
        return unique_docs


# ============================================================
#                       RETRIVAL PIPELINE
# ============================================================


class RAGStorage:
    def __init__(self, provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE):
        self.persist_directory = os.getenv("PERSIST_DIRECTORY")
        if not self.persist_directory:
            raise ValueError("PERSIST_DIRECTORY environment variable is not set.")

        print(f"\n- Chạy embedding model bằng: '{_DEVICE}' \n")
        # ======= Create Embedding Model =======
        self.embedding_model = get_embedding_model(provider=provider)

    # ======= FUNC 1: NẠP DỮ LIỆU (INGESTION DATA) - Run once only  =======
    def build_vector_db(self):
        """
        - Chỉ chạy lại (re-run) khi thêm data mới
        - Data phải lưu vào thư mục **source-data/**
        - **Lưu ý: Hàm chỉ dùng cho data type là Json**
        """
        # 1a. Loading files
        # documents = load_documents()  # PDF + Text

        # 1b. Add-on (Json data)
        json_dir = os.getenv("JSON_DATA_DIR", "src/source_data/places_data")
        json_docs = load_json_places(json_dir)
        documents = json_docs

        # 2. Chunking the files
        chunks = split_documents(documents)

        # 3. Embedding and Storing in Vector DB
        vectorstore = create_vector_store(
            chunks, self.persist_directory, self.embedding_model
        )

        print(
            "\n Ingestion hoàn thành! Tài liệu đã được lưu vào Chroma DB & sẵn sàng cho các truy vấn RAG."
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
        return vectorstore.as_retriever(search_kwargs={"k": _TOP_K})

    # ======= FUNC 3: HYBRID SEARCH (VECTOR + KEY WORD) =======
    def get_hybrid_retriever(
        self, vector_weight: float = 0.6, bm25_weight: float = 0.4
    ) -> EnsembleRetriever:
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

        Output:
        Vượt top_k là chuyện bình thường, ví dụ: top_k = 20
        Hybrid Search = Vector + BM25, mỗi cái trả về 20 docs
        → union lại → loại duplicate → ~ 35-38 unique docs.
        """

        print(f"\n- Tải CSDL Chroma từ thư mục: {self.persist_directory}")
        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding_model,
            collection_name="kltn_chatbot",
        )
        # Vector retriever — k = 20 để có pool đủ lớn cho dedup sau này
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": _TOP_K})

        # BM25 chạy trên RAM ==> cần List Document => pull toàn bộ từ Chroma
        print("\n- Build BM25 index từ Chroma docs")
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
        bm25_retriever.k = _TOP_K  # k = 20 để tương đồng với vector retriever

        print(f"\n✅ BM25 index built: {len(all_docs)} docs")
        print(f"\n[WEIGHTS] Vector: {vector_weight} | BM25: {bm25_weight}")

        """
        EnsembleRetriever Của langchain đã có RRF_score(doc) = Σ 1 / (k + rank_i)
        LangChain x weight => score = weight_vector × 1/(60+rank_vector) + weight_bm25 × 1/(60+rank_bm25)
        Vector = 0.6 (embedding dc train cho TV)
        BM25   = 0.4 ( keyword matching cho tên địa điểm, món ăn đặc sản — những thứ vector dễ miss)
        """
        return EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[vector_weight, bm25_weight],
        )

    # ======= FUNC 4a: BUILD MULTI-QUERY RETRIEVER =======
    def _build_multi_query_retriever(self) -> MultiQueryRetriever:
        """
        Khởi tạo MultiQueryRetriever:
        LLM sinh N query variations → Hybrid Search (Vector + BM25) → Dedup
        """
        hybrid_retriever = self.get_hybrid_retriever()

        print("\n- LLM cho multi query")
        llm_multi_query = get_llm(LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")))

        return MultiQueryRetriever(
            retriever=hybrid_retriever,
            llm=llm_multi_query,
            num_variations=3,
        )

    # ======= FUNC 4b: BUILD CROSS-ENCODER RERANKER =======
    @staticmethod
    def _build_cross_encoder_reranker() -> CrossEncoderReranker:
        """
        Khởi tạo BGE Reranker chạy local trên GPU.
        Nhìn (query, doc) cùng lúc → độ chính xác của docs cao hơn

        Flow:
            XX unique docs (sample: 68)(từ MultiQueryRetriever)
                ↓
            CrossEncoder tính score từng cặp (query, doc)
                ↓
            Rerank (metadatas) Sắp xếp lại theo score
                ↓
            Giữ lại top-N docs → đưa vào LLM generate

        CrossEncoder khác Embedding:
            - Embedding:    encode query và doc RIÊNG → so sánh vector
            - CrossEncoder: nhìn query + doc CÙNG LÚC → score chính xác hơn
                            nhưng chậm hơn (O(n) calls thay vì O(1))
        """
        print(
            f"\n========= Khởi tạo BGE Reranker: {RerankerConfig.MODEL_NAME} ========="
        )
        print(f"\n- Top-N sau rerank: {RerankerConfig.TOP_N}")

        _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        _DEFAULT_RERANKER_CACHE = os.path.normpath(
            os.path.join(_BASE_DIR, "..", "model", "reranker")
        )
        print(f"\n📁 Cache dir reranker model: {_DEFAULT_RERANKER_CACHE} \n")

        encoder = HuggingFaceCrossEncoder(
            model_name=RerankerConfig.MODEL_NAME,
            model_kwargs={
                "device": _DEVICE,  # chạy = gpu
                "cache_folder": _DEFAULT_RERANKER_CACHE,  # lưu model rank
            },
        )

        reranker = CrossEncoderReranker(
            model=encoder,
            top_n=RerankerConfig.TOP_N,
        )

        print("\n✅ Model Reranker sẵn sàng\n")
        return reranker

    # ======= FUNC 5: Trả về cặp (Retriever, Reranker) =======
    def get_multi_query_retriever(
        self,
    ) -> tuple[MultiQueryRetriever, CrossEncoderReranker]:
        """
        Trả về cặp (MultiQueryRetriever, CrossEncoderReranker).
        Tách ra để orchestrator.py tự quyết định khi nào rerank.
        """
        retriever = self._build_multi_query_retriever()
        reranker = self._build_cross_encoder_reranker()
        return retriever, reranker
