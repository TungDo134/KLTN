"""
ingest/json_to_chromadb.py
Đọc file JSON đã validate → build text + metadata → upsert vào ChromaDB.

Dùng upsert (không phải insert) để:
  - Tránh duplicate nếu chạy lại
  - Tự động update nếu place đã có mà dữ liệu thay đổi
  - Key duy nhất là place_id
"""

from ingest.text_builder import TextBuilder


class JSONToChromaDB:
    def __init__(self):
        """
        Pseudo:
          self.text_builder = TextBuilder()
          self.embedding    = get_embedding_model()     # tái dùng từ BE_ChatBot/core/base_embed_model.py
          self.vectorstore  = Chroma(
            persist_directory = CHROMA_PERSIST_DIR,
            embedding_function= self.embedding,
            collection_name   = CHROMA_COLLECTION,
          )
        """
        # TODO: implement
        pass

    def ingest_file(self, json_path: str) -> dict:
        """
        Ingest một file JSON (list of place dicts).
        Trả về summary {"inserted": int, "updated": int, "failed": int}.

        Pseudo:
          with open(json_path, encoding="utf-8") as f:
            places = json.load(f)

          documents, metadatas, ids = [], [], []
          for place in places:
            text     = text_builder.build(place)
            metadata = text_builder.build_metadata(place)
            documents.append(text)
            metadatas.append(metadata)
            ids.append(place["place_id"])

          # Upsert theo batch
          vectorstore._collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
          )
          return {"inserted": len(places), "updated": 0, "failed": 0}
        """
        # TODO: implement
        pass

    def ingest_directory(self, dir_path: str) -> dict:
        """
        Ingest toàn bộ file .json trong một thư mục.

        Pseudo:
          total = {"inserted": 0, "updated": 0, "failed": 0}
          for json_file in Path(dir_path).glob("*.json"):
            summary = ingest_file(json_file)
            total   = _merge_summary(total, summary)
            print(f"✅ {json_file.name}: {summary}")
          return total
        """
        # TODO: implement
        pass
