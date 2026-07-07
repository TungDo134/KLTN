from functools import partial
import asyncio
import time

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.messages import HumanMessage

from src.core.base_embed_model import get_embedding_model
from src.core.base_llm_model import LLMProvider
from src.core.llm_container import get_llm

load_dotenv()

import os
import torch
import chromadb
from langchain_ollama import OllamaEmbeddings


"""
Test xem nó run bằng cpu hay gpu
"""
# print(torch.cuda.is_available())  # True ✅
# print(torch.cuda.get_device_name(0))  # NVIDIA GeForce RTX 3050 ✅
# print(torch.__version__)  # 2.x.x+cu124 ✅


"""
Test xem get dc value env khong? 
"""
# json_dir = os.getenv("JSON_DATA_DIR")
# print(json_dir)


"""
- Check exist db and have data?.
- Check matching embedding model?
"""
#
#
# def check_vector_db(
#         persist_dir: str,
#         collection_name: str,
#         embedding_model_name: str):
#     print("=" * 50)
#     print("VECTOR DB HEALTH CHECK")
#     print("=" * 50)
#
#     # 1. Kết nối DB
#     client = chromadb.PersistentClient(path=persist_dir)
#
#     # 2. Kiểm tra collection tồn tại không
#     collections = [c.name for c in client.list_collections()]
#     print(f"\nCollections có trong DB: {collections}")
#
#     if collection_name not in collections:
#         print(f"❌ Collection '{collection_name}' không tồn tại!")
#         return
#
#     col = client.get_collection(collection_name)
#
#     # 3. Kiểm tra số lượng documents
#     count = col.count()
#     print(f"Total documents: {count}")
#     if count == 0:
#         print("❌ DB trống — cần chạy lại build_vector_db!")
#         return
#
#     # 4. Kiểm tra dimension
#     sample = col.peek(limit=1)
#     db_dim = len(sample["embeddings"][0])
#     print(f"\nDB vector dimension: {db_dim}")
#
#     # 5. Kiểm tra model dimension
#     model = OllamaEmbeddings(model=embedding_model_name)
#     test_vec = model.embed_query("kiểm tra")
#     model_dim = len(test_vec)
#     print(f"Model vector dimension: {model_dim}")
#
#     # 6. So sánh
#     if db_dim == model_dim:
#         print(f"\n✅ Match! Cả 2 đều {db_dim} chiều")
#     else:
#         print(f"\n❌ Mismatch! DB={db_dim} vs Model={model_dim}")
#         print("→ Xóa DB cũ và chạy lại build_vector_db!")
#
#     # 7. Preview 3 documents đầu
#     print("\n--- Preview 3 documents ---")
#     preview = col.peek(limit=3)
#     for i, doc in enumerate(preview["documents"], 1):
#         print(f"Doc {i}: {doc[:80]}...")
#
#
# # Chạy kiểm tra
# check_vector_db(
#     persist_dir=os.getenv("PERSIST_DIRECTORY"),
#     collection_name="kltn_chatbot",
#     embedding_model_name="bge-m3"
# )


"""
- Test hàm load file pdf + text  
"""
# def _test_func(source_data=os.getenv("SOURCE_DATA")):
#     pdf_loader = DirectoryLoader(path=source_data, glob="*.pdf", loader_cls=PyPDFLoader)
#     txt_loader = DirectoryLoader(path=source_data, glob="*.txt", loader_cls=TextLoader,
#                                  loader_kwargs={"encoding": "utf-8"})
#
#     # documents = loader.load()
#     documents = pdf_loader.load() + txt_loader.load()
#     print(f"Tổng documents: {len(documents)}")
#     for doc in documents:
#         print(doc.metadata['source'])
#
#
# if __name__ == '__main__':
#     _test_func()


"""
- Test LLM
"""


async def _quick_nvidia_model_test():
    """
    Test nhanh NVIDIA LLM, không chạy RAG/orchestrator.

    Mục tiêu:
      1. Kiểm tra non-stream `ainvoke`.
      2. Kiểm tra stream `astream`.
      3. Không set timeout; in thời gian chờ để biết model trả chậm hay không trả.
    """
    provider = LLMProvider.NVIDIA
    prompt = "Tra loi ngan gon bang tieng Viet: 2 + 2 bang may?"

    print("=" * 60)
    print("NVIDIA LLM QUICK HEALTH CHECK")
    print("=" * 60)
    print(f"Provider: {provider}")
    print("Timeout : disabled")

    llm = get_llm(provider=provider, temperature=0.1, max_tokens=128)
    messages = [HumanMessage(content=prompt)]

    print("\n[1] Testing ainvoke...")
    started_at = time.perf_counter()
    done = asyncio.Event()
    progress_task = asyncio.create_task(
        _print_elapsed_until_done("ainvoke", started_at, done)
    )
    try:
        response = await llm.ainvoke(messages)
        elapsed = time.perf_counter() - started_at
        print(f"OK ainvoke in {elapsed:.2f}s")
        print("Response:", getattr(response, "content", response))
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"FAILED ainvoke after {elapsed:.2f}s")
        print(f"Error: {type(exc).__name__}: {repr(exc)}")
        return
    finally:
        done.set()
        await progress_task

    print("\n[2] Testing astream...")
    started_at = time.perf_counter()
    chunks = []
    first_token_at = None
    done = asyncio.Event()
    progress_task = asyncio.create_task(
        _print_elapsed_until_done("astream", started_at, done)
    )

    try:
        async for chunk in llm.astream(messages):
            token = getattr(chunk, "content", "")
            if token:
                if first_token_at is None:
                    first_token_at = time.perf_counter() - started_at
                    print(f"First stream token after {first_token_at:.2f}s")
                chunks.append(token)
        elapsed = time.perf_counter() - started_at
        print(f"OK astream in {elapsed:.2f}s")
        print("Stream response:", "".join(chunks))
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"FAILED astream after {elapsed:.2f}s")
        print(f"Error: {type(exc).__name__}: {repr(exc)}")
    finally:
        done.set()
        await progress_task


async def _print_elapsed_until_done(label: str, started_at: float, done: asyncio.Event):
    while not done.is_set():
        await asyncio.sleep(10)
        if not done.is_set():
            elapsed = time.perf_counter() - started_at
            print(f"[{label}] still waiting... {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(_quick_nvidia_model_test())


# def _llm_test(provider: LLMProvider):
#     llm = get_llm(provider=provider)
#
#     # Nhập input vào terminal để test
#     user_input = input("You: ")
#
#     if not user_input.strip():
#         print("⚠️ Input is empty.")
#         return
#
#     response = llm.invoke([HumanMessage(content=user_input)])
#     print(f"[{provider}]: {response.content}")


# from langchain_chroma import Chroma
#
#
# # ... khởi tạo embedding model
# def metadata_db():
#     vectorstore = Chroma(persist_directory=os.getenv("PERSIST_DIRECTORY"),
#                          embedding_function=get_embedding_model(),
#                          collection_name="kltn_chatbot",
#                          collection_metadata={"hnsw:space": "cosine"})
#     sample = vectorstore.get(limit=2)
#     print(sample["metadatas"])
#     print(sample["documents"][0][:200])


# Synthetic Questions:
# 1. "What was NVIDIA's first graphics accelerator called?"
# 2. "Which company did NVIDIA acquire to enter the mobile processor market?"
# 3. "What was Microsoft's first hardware product release?"
# 4. "How much did Microsoft pay to acquire GitHub?"
# 5. "In what year did Tesla begin production of the Roadster?"
# 6. "Who succeeded Ze'ev Drori as CEO in October 2008?"
# 7. "What was the name of the autonomous spaceport drone ship that achieved the first successful sea landing?"
# 8. "What was the original name of Microsoft before it became Microsoft?"
