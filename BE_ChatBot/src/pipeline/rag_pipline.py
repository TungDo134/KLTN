"""
INGESTION + RETRIEVE PIPELINE
"""

# --- IMPORT ---
import os
from functools import partial

import torch
from dotenv import load_dotenv

# Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain_chroma import Chroma

# Embedding model
from src.core.base_embed_model import get_embedding_model, EmbeddingProvider

# --- LOAD .env ---
load_dotenv()

"""
=========== Hướng dẫn bổ sung data =========== 
- Nếu muốn thêm data, bạn chỉ cần chạy file notebook build_vector_db:
"""

# --- Auto-detect GPU ---
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Get global var from .env (UNUSED)
model_name = os.getenv("MODEL_NAME")
cache_folder = os.getenv("CACHE_FOLDER")

"""# --- Create Embedding Model ---
# HuggingFaceEmbeddings
# def _build_embedding_model() -> HuggingFaceEmbeddings:
#     return HuggingFaceEmbeddings(
#         model_name="AITeamVN/Vietnamese_Embedding",
#         model_kwargs={"device": _DEVICE},
#         encode_kwargs={"normalize_embeddings": True},
#         cache_folder="src/model/embeddings",
#     )


# OllamaEmbeddings
# def _build_embedding_model() -> OllamaEmbeddings:
#     return OllamaEmbeddings(model='bge-m3')"""


# --- STEP 1: FUNCTION LOAD DOCUMENT ---
def load_documents(source_data: str = os.getenv("SOURCE_DATA")):
    """Load all document in SOURCE_DATA: 'src/source_data/docs' """
    print(f"Loading document from {source_data}")

    # check exists
    if not os.path.exists(source_data):
        raise FileNotFoundError(f"Documents directory does not exist: {source_data}")

    # load pdf + text files

    pdf_loader = DirectoryLoader(path=source_data, glob="*.pdf", loader_cls=PyPDFLoader)  # type: ignore
    txt_loader = DirectoryLoader(path=source_data, glob="*.txt",
                                 loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})

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
        print(doc.metadata['source'])

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
            print(f"\n[Chunk {i + 1}] {chunk.metadata['source']} | {len(chunk.page_content)} chars")
            print(chunk.page_content[:100] + "...")

    return chunks


# --- CREATE VECTOR DB (CHROMA) ---
"""def create_vector_store_v1(chunks, persist_directory: str, embedding_model) -> Chroma:
 
    print("-" * 60)
    print("Creating embeddings and storing in ChromaDB...")

    # Lần đầu tiên: DB chưa tồn tại → tạo mới bằng from_documents
    # Các lần sau: DB đã có → load lên rồi add vào
    db_exists = os.path.exists(persist_directory) and os.listdir(persist_directory)

    print("-" * 60)

    batch_size = 100
    if not db_exists:
        print("📦 DB chưa tồn tại, tạo mới...")
        first_batch = chunks[:batch_size]
        vectorstore = Chroma.from_documents(
            documents=first_batch,
            collection_name="kltn_chatbot",
            embedding=embedding_model,
            persist_directory=persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )
        remaining = chunks[batch_size:]
    else:
        print("📦 DB đã tồn tại, load lên và bổ sung...")
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding_model,
            collection_name="kltn_chatbot",
        )
        remaining = chunks

    # Add các batch còn lại
    for i in range(0, len(remaining), batch_size):
        batch = remaining[i: i + batch_size]
        print(f"Inserting batch ({len(batch)} chunks)...")
        vectorstore.add_documents(batch)

    print(f"Total inserted: {vectorstore._collection.count()} chunks")
    return vectorstore
"""


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
        existing_count = vectorstore._collection.count()

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
            m["source"] for m in vectorstore.get()["metadatas"]
        )
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

    print(f"\nHoàn tất: {success} inserted, {failed} failed | Tổng DB: {vectorstore._collection.count()}")
    return vectorstore


class RAGStorage:
    def __init__(self, provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE):
        self.persist_directory = os.getenv("PERSIST_DIRECTORY")
        if not self.persist_directory:
            raise ValueError(f"PERSIST_DIRECTORY environment variable is not set.")

        print(f"Loading embedding model on device using: '{_DEVICE}'...")
        # --- Create Embedding Model ---
        self.embedding_model = get_embedding_model(provider=provider)

    # --- HÀM 1: NẠP DỮ LIỆU (INGESTION DATA) - Run once only  ---
    def build_vector_db(self):
        """Only re-run when adding new PDFs || Texts into the docs/ folder."""
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

    # --- HÀM 2: TRUY XUẤT TÀI LIỆU (API) ---
    def get_retriever(self):
        # Load database in "persist_directory"
        print("=" * 60)
        print(f"Loading Chroma database from {self.persist_directory}...")

        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding_model,
            collection_name="kltn_chatbot",
        )
        # top_k
        return vectorstore.as_retriever(search_kwargs={"k": 5})
