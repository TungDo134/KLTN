"""
ingest/text_builder.py
Convert một place dict → chuỗi văn bản (document text) để embed vào ChromaDB.

Tại sao cần bước này?
  ChromaDB lưu embedding của TEXT, không phải JSON.
  Cần build một đoạn text tự nhiên đại diện cho địa điểm
  để embedding model hiểu ngữ nghĩa khi user hỏi.

Ví dụ output:
  "Thác Datanla là địa điểm thiên nhiên tại Đà Lạt, Lâm Đồng.
   Tags: thác nước, dã ngoại, gia đình.
   Thác Datanla nằm cách trung tâm Đà Lạt 7km...
   Thời gian tham quan: 120 phút. Đánh giá: 4.3/5 (1250 đánh giá).
   Phù hợp cho: gia đình, cặp đôi. Thời điểm lý tưởng: sáng sớm, chiều mát."
"""


class TextBuilder:
    def build(self, place: dict) -> str:
        """
        Entry point — tạo document text từ place dict.

        Pseudo:
          parts = [
            _build_header(place),       # tên + category + region
            _build_tags_line(place),     # tags
            _build_description(place),   # description gốc
            _build_details(place),       # duration, rating, review_count
            _build_suitability(place),   # suitable_for, best_time
            _build_price_info(place),    # budget_level + giá vé
          ]
          return "\n".join(filter(None, parts))
        """
        # TODO: implement
        pass

    def build_metadata(self, place: dict) -> dict:
        """
        Tạo metadata dict để lưu kèm vào ChromaDB document.
        Metadata này được dùng bởi _docs_to_places() trong Orchestrator.

        Pseudo:
          return {
            "place_id"        : place["place_id"],
            "name"            : place["name"],
            "region"          : place["region"],
            "category"        : place["category"],
            "tags"            : ",".join(place.get("tags", [])),
            "lat"             : place["location"]["lat"],
            "lon"             : place["location"]["lon"],
            "address"         : place["location"].get("address", ""),
            "duration"        : place.get("duration_minutes", 60),
            "rating"          : place.get("rating", 0.0),
            "budget_level"    : place.get("price", {}).get("budget_level", "low"),
            "source_url"      : place.get("source_url", ""),
          }
        """
        # TODO: implement
        pass

    # ── Private helpers ───────────────────────────────────────────────

    def _build_header(self, place: dict) -> str:
        # Pseudo: return f"{name} là địa điểm {category} tại {region}, {province}."
        pass

    def _build_tags_line(self, place: dict) -> str:
        # Pseudo: return f"Tags: {', '.join(tags)}."
        pass

    def _build_details(self, place: dict) -> str:
        # Pseudo: return f"Thời gian tham quan: {duration} phút. Đánh giá: {rating}/5 ({review_count} đánh giá)."
        pass

    def _build_suitability(self, place: dict) -> str:
        # Pseudo: return f"Phù hợp cho: {suitable_for}. Thời điểm lý tưởng: {best_time}."
        pass

    def _build_price_info(self, place: dict) -> str:
        # Pseudo: return f"Mức giá: {budget_level}. Vé vào: {adult}đ (người lớn), {child}đ (trẻ em)."
        pass
