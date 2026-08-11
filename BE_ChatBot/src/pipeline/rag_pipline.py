"""
INGESTION + RETRIEVE PIPELINE
"""

# --- IMPORT ---
import json
import os
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Langchain
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

#
from pydantic import BaseModel, Field, ValidationError

# Embedding model
from src.core.base_embed_model import (
    EmbeddingProvider,
    get_embedding_model,
    resolve_embedding_config,
)
from src.core.base_llm_model import LLMProvider
from src.core.llm_container import get_llm, get_model_info
from src.pipeline.document_reranker import DocumentReranker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

# --- LOAD .env ---

load_dotenv()
"""
=========== Hướng dẫn bổ sung data =========== 
- Nếu muốn thêm data, bạn chỉ cần chạy file notebook build_vector_db:
"""

_TOP_K = 20
_COLLECTION_NAME = "kltn_chatbot"
_GOOGLE_BATCH_SIZE = 100
_GOOGLE_BATCH_DELAY_SECONDS = 65
_GOOGLE_MAX_RATE_LIMIT_RETRIES = 3


class EmbeddingDatabaseMismatchError(ValueError):
    """Nem loi khi ChromaDB duoc tao boi embedding khac."""


def _embedding_collection_metadata(
    provider: EmbeddingProvider,
    model_name: str,
) -> dict:
    return {
        "hnsw:space": "cosine",
        "embedding_provider": provider.value,
        "embedding_model": model_name,
    }


def _validate_embedding_database(
    vectorstore: Chroma,
    provider: EmbeddingProvider,
    model_name: str,
    persist_directory: str,
    require_documents: bool = False,
) -> int:
    existing_count = len(vectorstore.get()["ids"])
    if require_documents and existing_count == 0:
        raise ValueError(
            f"ChromaDB is empty at {persist_directory}. Run the build notebook first."
        )
    if existing_count == 0:
        return 0

    metadata = vectorstore._collection.metadata or {}
    stored_provider = metadata.get("embedding_provider")
    stored_model = metadata.get("embedding_model")
    if stored_provider != provider.value or stored_model != model_name:
        raise EmbeddingDatabaseMismatchError(
            "ChromaDB embedding configuration does not match .env. "
            f"DB uses provider={stored_provider or 'missing'}, "
            f"model={stored_model or 'missing'}; .env uses "
            f"provider={provider.value}, model={model_name}. "
            f"Stop the backend, delete {persist_directory} manually, then rebuild "
            "with utils/build_rag_vector_db.ipynb."
        )
    return existing_count


# ============================================================
#                       INGEST DATA
# ============================================================


# --- (IGNORE - DO NOT USED) FUNCTION LOAD DOCUMENT ---
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


# --- STEP 1: FUNCTION CONVERT JSON DATA => DOCUMENT ---
def load_json_places(data_dir: str) -> list[Document]:
    """
    **Lưu ý: Chỉ hỗ trợ file dạng JSON**
    - Load files từ `D:/KLTN/Project/BE_ChatBot/src/source_data/places_data` => `list[Document]`.

    - page_content  : text `concat từ các field ngữ nghĩa cao`
    - metadata      : các field flat support **RERANK** `tự build` - filter - planning
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


# --- STEP 2: FUNCTION CHUNK DOC ---
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
def create_vector_store(
    chunks,
    persist_directory: str,
    embedding_model,
    provider: EmbeddingProvider,
    model_name: str,
) -> Chroma:
    """
    - Embed model handle chunk to vector
    - Send all to db can time out --> Divide into parts (100 chunk/time)
    """
    print("=" * 60)
    batch_size = 100
    is_new_db = False
    collection_metadata = _embedding_collection_metadata(provider, model_name)

    # Load or create DB
    try:
        # Load
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding_model,
            collection_name=_COLLECTION_NAME,
            collection_metadata=collection_metadata,
        )
        existing_count = _validate_embedding_database(
            vectorstore,
            provider,
            model_name,
            persist_directory,
        )

        if existing_count == 0:
            raise ValueError("DB rỗng, chuẩn bị tạo mới")

        print(f"📦 Load DB thành công ({existing_count} chunks đã có)")
    except EmbeddingDatabaseMismatchError:
        raise
    except Exception as e:
        # Create - Update
        print(f"📦 Tạo DB mới... ({e})")
        vectorstore = Chroma.from_documents(
            documents=chunks[:batch_size],
            collection_name=_COLLECTION_NAME,
            embedding=embedding_model,
            persist_directory=persist_directory,
            collection_metadata=collection_metadata,
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


# --- STEP 3: Use Gemini Embedding ---
def create_vector_store_google(
    chunks,
    persist_directory: str,
    embedding_model,
    provider: EmbeddingProvider,
    model_name: str,
) -> Chroma:
    """Create/update ChromaDB with Google free-tier throttling and retry."""
    if provider != EmbeddingProvider.GOOGLE:
        raise ValueError(
            "create_vector_store_google() requires EMBEDDING_PROVIDER=google."
        )
    if not chunks:
        raise ValueError("No chunks found to embed.")

    collection_metadata = _embedding_collection_metadata(provider, model_name)
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_model,
        collection_name=_COLLECTION_NAME,
        collection_metadata=collection_metadata,
    )
    existing_count = _validate_embedding_database(
        vectorstore,
        provider,
        model_name,
        persist_directory,
    )

    if existing_count > 0:
        existing_sources = set(
            metadata.get("source") or metadata.get("place_id", "")
            for metadata in vectorstore.get()["metadatas"]
        )
        chunks = [
            chunk
            for chunk in chunks
            if (chunk.metadata.get("source") or chunk.metadata.get("place_id", ""))
            not in existing_sources
        ]
        print(f"Google ingestion: {len(chunks)} new chunks after duplicate filtering")

    if not chunks:
        print("No new chunks. Google ingestion skipped.")
        return vectorstore

    inserted_batches = 0
    for start in range(0, len(chunks), _GOOGLE_BATCH_SIZE):
        batch = chunks[start : start + _GOOGLE_BATCH_SIZE]
        batch_number = start // _GOOGLE_BATCH_SIZE + 1

        if inserted_batches > 0:
            print(
                f"Waiting {_GOOGLE_BATCH_DELAY_SECONDS}s before batch "
                f"{batch_number} to respect the Google free-tier rate limit..."
            )
            time.sleep(_GOOGLE_BATCH_DELAY_SECONDS)

        rate_limit_retries = 0
        while True:
            try:
                vectorstore.add_documents(batch)
                inserted_batches += 1
                print(f"Google batch {batch_number}: OK ({len(batch)} chunks)")
                break
            except Exception as exc:
                error_message = str(exc)
                is_rate_limit_error = (
                    "429" in error_message or "RESOURCE_EXHAUSTED" in error_message
                )
                if not is_rate_limit_error:
                    raise RuntimeError(
                        f"Google batch {batch_number} failed: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc

                rate_limit_retries += 1
                if rate_limit_retries > _GOOGLE_MAX_RATE_LIMIT_RETRIES:
                    raise RuntimeError(
                        f"Google batch {batch_number} is still rate limited after "
                        f"{_GOOGLE_MAX_RATE_LIMIT_RETRIES} retries: {exc}"
                    ) from exc

                print(
                    f"Google batch {batch_number}: rate limited (429). Waiting "
                    f"{_GOOGLE_BATCH_DELAY_SECONDS}s before retry "
                    f"{rate_limit_retries}/{_GOOGLE_MAX_RATE_LIMIT_RETRIES}..."
                )
                time.sleep(_GOOGLE_BATCH_DELAY_SECONDS)

    total_count = len(vectorstore.get()["ids"])
    print(f"Google ingestion complete. Total DB chunks: {total_count}")
    return vectorstore


# ============================================================
#                       RERANK CONFIG
# ============================================================
class RerankerConfig:
    """
    Cau hinh buoc rerank tai lieu truoc khi convert sang Place.
    Doi provider bang .env va restart BE de ap dung.
    """

    PROVIDER: str = os.getenv("RERANKER_PROVIDER", "huggingface").strip().lower()
    TOP_N: int = int(os.getenv("RERANKER_TOP_N", "20"))

    _MODEL_NAME = os.getenv("RERANKER_MODEL_NAME")
    MODEL_NAME: str = (
        _MODEL_NAME.strip()
        if _MODEL_NAME and _MODEL_NAME.strip()
        else ("rerank-v3.5" if PROVIDER == "cohere" else "BAAI/bge-reranker-v2-m3")
    )

    COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY") or None


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

        # 2. HYBRID SEARCH từng VARIATION
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

        # 4. Trả về các RELEVANTS DOCS sau khi multi query + duplicate
        return unique_docs


# ============================================================
#                       RETRIVAL PIPELINE
# ============================================================


class RAGStorage:
    def __init__(
        self,
        provider: EmbeddingProvider | str | None = None,
        model_name: str | None = None,
    ):
        self.persist_directory = os.getenv("PERSIST_DIRECTORY")
        if not self.persist_directory:
            raise ValueError("PERSIST_DIRECTORY environment variable is not set.")

        self.embedding_provider, self.embedding_model_name = resolve_embedding_config(
            provider,
            model_name,
        )
        self.collection_metadata = _embedding_collection_metadata(
            self.embedding_provider,
            self.embedding_model_name,
        )
        self.embedding_model = get_embedding_model(
            provider=self.embedding_provider,
            model_name=self.embedding_model_name,
        )

    # ======= FUNC 1: NẠP DỮ LIỆU (INGESTION DATA) - Run once only  =======
    def build_vector_db(self):
        """
        - Chỉ chạy lại (re-run) khi thêm data mới
        - Data phải lưu vào thư mục **source-data/**
        - **Lưu ý: Hàm chỉ dùng cho data type là Json**
        """
        if self.embedding_provider == EmbeddingProvider.GOOGLE:
            raise ValueError(
                "Google embedding must use build_vector_db_google(). "
                "Update the comment/uncomment selection in "
                "utils/build_rag_vector_db.ipynb."
            )

        # 1-old. Loading files
        # documents = load_documents()  # PDF + Text

        # [1]. Load JSON files => Document (LangChain Object)
        json_dir = os.getenv("JSON_DATA_DIR", "src/source_data/places_data")
        json_docs = load_json_places(json_dir)
        documents = json_docs

        # [2]. Files Chunking
        chunks = split_documents(documents)

        # [3]. Embedding and Storing in Vector DB
        vectorstore = create_vector_store(
            chunks,
            self.persist_directory,
            self.embedding_model,
            self.embedding_provider,
            self.embedding_model_name,
        )

        print(
            "\n Ingestion hoàn thành! Tài liệu đã được lưu vào Chroma DB & sẵn sàng cho các truy vấn RAG."
        )

        return vectorstore

    def build_vector_db_google(self):
        """Build ChromaDB through the separate Google throttled ingestion path."""
        if self.embedding_provider != EmbeddingProvider.GOOGLE:
            raise ValueError(
                "build_vector_db_google() requires EMBEDDING_PROVIDER=google. "
                "Use build_vector_db() for HuggingFace or Ollama."
            )

        json_dir = os.getenv("JSON_DATA_DIR", "src/source_data/places_data")
        documents = load_json_places(json_dir)
        chunks = split_documents(documents)
        vectorstore = create_vector_store_google(
            chunks,
            self.persist_directory,
            self.embedding_model,
            self.embedding_provider,
            self.embedding_model_name,
        )
        print(
            "\nGoogle embedding ingestion completed. ChromaDB is ready for RAG retrieval."
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
            collection_name=_COLLECTION_NAME,
            collection_metadata=self.collection_metadata,
        )
        _validate_embedding_database(
            vectorstore,
            self.embedding_provider,
            self.embedding_model_name,
            self.persist_directory,
            require_documents=True,
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
            collection_name=_COLLECTION_NAME,
            collection_metadata=self.collection_metadata,
        )
        _validate_embedding_database(
            vectorstore,
            self.embedding_provider,
            self.embedding_model_name,
            self.persist_directory,
            require_documents=True,
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
        llm_multi_query = get_llm(
            LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")),
            model_name=os.getenv("REWRITE_LLM_MODEL") or None,
        )

        return MultiQueryRetriever(
            retriever=hybrid_retriever,
            llm=llm_multi_query,
            num_variations=3,
        )

    # ======= FUNC 4b: BUILD DOCUMENT RERANKER =======
    @staticmethod
    def _build_document_reranker() -> DocumentReranker:
        """
        Khoi tao document reranker bang interface chung.
        Provider huggingface chay local, provider cohere goi API.
        """
        print(
            f"\n🚀 Initializing Document Reranker [{RerankerConfig.PROVIDER} - {RerankerConfig.MODEL_NAME}] "
            f"\n🔧 Provider{RerankerConfig.PROVIDER}"
            f"\n🔧 Model{RerankerConfig.MODEL_NAME}"
        )
        print(f"\n- Top-N sau rerank: {RerankerConfig.TOP_N}")

        _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        _DEFAULT_RERANKER_CACHE = os.path.normpath(
            os.path.join(_BASE_DIR, "..", "model", "reranker")
        )

        if RerankerConfig.PROVIDER == "huggingface":
            print(f"\nCache dir reranker model: {_DEFAULT_RERANKER_CACHE} \n")

        reranker = DocumentReranker(
            provider=RerankerConfig.PROVIDER,
            model_name=RerankerConfig.MODEL_NAME,
            top_n=RerankerConfig.TOP_N,
            api_key=RerankerConfig.COHERE_API_KEY,
            cache_dir=_DEFAULT_RERANKER_CACHE,
        )

        print("\nModel Reranker san sang\n")
        return reranker

    # ======= FUNC 5: Trả về cặp (Retriever, Reranker) =======
    def get_multi_query_retriever(
        self,
    ) -> tuple[MultiQueryRetriever, DocumentReranker]:
        """
        Tra ve cap retriever va document reranker cho orchestrator.
        Orchestrator se tu quyet dinh luc goi rerank sau khi retrieve xong.
        """
        retriever = self._build_multi_query_retriever()
        reranker = self._build_document_reranker()
        return retriever, reranker
