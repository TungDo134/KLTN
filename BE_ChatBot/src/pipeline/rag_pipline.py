"""
INGESTION + RETRIEVE PIPELINE
"""

# --- IMPORT ---
import os
import torch
from dotenv import load_dotenv

# Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
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


# --- Create Embedding Model ---


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
#     return OllamaEmbeddings(model='bge-m3')


# --- FUNCTION LOAD DOCUMENT ---
def load_documents(source_data: str = os.getenv("SOURCE_DATA")):
    print(f"Loading document from {source_data}")

    # check exists
    if not os.path.exists(source_data):
        raise FileNotFoundError(f"Documents directory does not exist: {source_data}")

    # load files
    loader = DirectoryLoader(path=source_data, glob="*.pdf", loader_cls=PyPDFLoader)

    documents = loader.load()

    if len(documents) == 0:
        raise FileNotFoundError(
            f"No .pdf files found in {source_data}. Please add your company documents."
        )

    for i, doc in enumerate(documents[:2]):  # Show first 2 documents
        print(f"\nDocument {i + 1}:")
        print(f"  Source: {doc.metadata['source']}")
        print(f"  Content length: {len(doc.page_content)} characters")
        print(f"  Content preview: {doc.page_content[:100]}...")
        print(f"  metadata: {doc.metadata}")

    return documents


# --- FUNCTION CHUNK DOC (ADVANCED LATER) ---
def split_documents(documents, chunk_size=1000, chunk_overlap=150):
    """Split documents into smaller chunks with overlap"""
    print("=" * 60)
    print("Splitting documents into chunks...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_documents(documents)

    if chunks:
        for i, chunk in enumerate(chunks[:5]):
            print(f"\n--- Chunk {i + 1} ---")
            print(f"Source: {chunk.metadata['source']}")
            print(f"Length: {len(chunk.page_content)} characters")
            print(f"Content:")
            print(chunk.page_content)
            print("-" * 50)

        if len(chunks) > 5:
            print(f"\n... and {len(chunks) - 5} more chunks")

    return chunks


# --- CREATE VECTOR DB (CHROMA) ---
def create_vector_store(
        chunks, persist_directory: str, embedding_model
) -> Chroma:
    print("Creating embeddings and storing in ChromaDB...")

    batch_size = 100

    # Lần đầu tiên: DB chưa tồn tại → tạo mới bằng from_documents
    # Các lần sau: DB đã có → load lên rồi add vào
    db_exists = os.path.exists(persist_directory) and os.listdir(persist_directory)

    if not db_exists:
        print("📦 DB chưa tồn tại, tạo mới...")
        first_batch = chunks[:batch_size]
        vectorstore = Chroma.from_documents(
            documents=first_batch,
            collection_name="kltn_chatbot",
            embedding=embedding_model,  # ← đổi 'embedding' thành 'embedding_function'
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
        print(f"  Inserting batch ({len(batch)} chunks)...")
        vectorstore.add_documents(batch)

    print(f"Total inserted: {vectorstore._collection.count()} chunks")
    return vectorstore


class RAGStorage:
    def __init__(self, provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE):
        self.persist_directory = os.getenv("PERSIST_DIRECTORY")
        if not self.persist_directory:
            raise ValueError(f"PERSIST_DIRECTORY environment variable is not set.")

        print(f"Loading embedding model on device using: '{_DEVICE}'...")
        # self.embedding_model = _build_embedding_model()
        self.embedding_model = get_embedding_model(provider=provider)

    # --- HÀM 1: NẠP DỮ LIỆU (INGESTION DATA) - Run once only  ---
    def build_vector_db(self):
        """Only rerun when adding new PDFs into the docs/ folder."""
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


def test_embedding():
    get_embedding_model(provider=EmbeddingProvider.HUGGINGFACE)
    print("=" * 50)


test_embedding()
