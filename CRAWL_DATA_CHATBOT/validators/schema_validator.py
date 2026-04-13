"""
validators/schema_validator.py
Validate mỗi place dict trước khi ingest vào ChromaDB.
Dùng jsonschema library để check theo place_schema.json.

Mục đích:
  - Phát hiện thiếu field bắt buộc (lat, lon, tags...)
  - Phát hiện sai kiểu dữ liệu
  - Phát hiện giá trị ngoài range (rating > 5, budget_level không hợp lệ)
  - Tách riêng valid / invalid để log ra file, không crash toàn bộ pipeline
"""

import json


class SchemaValidator:
    def __init__(self, schema_path: str = "validators/place_schema.json"):
        """
        Pseudo:
          with open(schema_path, encoding="utf-8") as f:
            self.schema = json.load(f)
        """
        # TODO: implement
        pass

    def validate_all(self, places: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Validate toàn bộ list.
        Trả về (valid_places, invalid_places).

        Pseudo:
          valid, invalid = [], []
          for place in places:
            errors = validate_one(place)
            if errors:
              invalid.append({"place": place, "errors": errors})
            else:
              valid.append(place)
          return valid, invalid
        """
        # TODO: implement
        pass

    def validate_one(self, place: dict) -> list[str]:
        """
        Validate một place, trả về list error messages (rỗng = hợp lệ).

        Pseudo:
          errors = []
          try:
            jsonschema.validate(instance=place, schema=self.schema)
          except jsonschema.ValidationError as e:
            errors.append(e.message)

          # Custom checks ngoài jsonschema
          if not (-90 <= place["location"]["lat"] <= 90):
            errors.append("lat out of range")
          if not (-180 <= place["location"]["lon"] <= 180):
            errors.append("lon out of range")
          if not (0 <= place.get("rating", 0) <= 5):
            errors.append("rating must be between 0 and 5")

          return errors
        """
        # TODO: implement
        pass

    def log_invalid(self, invalid_places: list[dict], log_path: str) -> None:
        """
        Ghi các invalid places ra file để review thủ công.
        Pseudo:
          with open(log_path, "w", encoding="utf-8") as f:
            json.dump(invalid_places, f, ensure_ascii=False, indent=2)
          print(f"⚠️ {len(invalid_places)} invalid places logged to {log_path}")
        """
        # TODO: implement
        pass
