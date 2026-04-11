from dotenv import load_dotenv

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


