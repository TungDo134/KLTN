"""
crawlers/tripadvisor_crawler.py
Crawler cho TripAdvisor Attractions — scrape HTML vì TripAdvisor không có public API.

Thư viện gợi ý: requests + BeautifulSoup4
URL pattern : https://www.tripadvisor.com/Attractions-g{geo_id}-Activities-{region}.html

⚠️ Lưu ý pháp lý: chỉ dùng cho mục đích học thuật / nghiên cứu.
   Kiểm tra robots.txt trước khi crawl.
"""

from crawlers.base_crawler import BaseCrawler


# Map region name → TripAdvisor geo_id
GEO_ID_MAP = {
    "dalat": "293922",
    "hanoi": "293924",
    "hcmc": "293925",
    "danang": "298082",
}


class TripAdvisorCrawler(BaseCrawler):
    def __init__(self, region: str):
        """
        Pseudo:
          super().__init__(region)
          self.geo_id   = GEO_ID_MAP[region]
          self.base_url = f"https://www.tripadvisor.com/Attractions-g{geo_id}-Activities-{region}.html"
        """
        # TODO: implement
        pass

    def crawl(self) -> list[dict]:
        # TODO: implement theo Pseudo ở BaseCrawler
        pass

    def _fetch_page(self, page: int) -> dict | None:
        # TODO: implement — trả về HTML string (không phải JSON)
        pass

    def _parse_page(self, raw: str) -> list[dict]:
        """
        Parse HTML → list[dict] theo place schema.

        Pseudo:
          soup   = BeautifulSoup(raw, "html.parser")
          cards  = soup.select("div[data-automation='attraction-list-item']")
          places = []
          for card in cards:
            place = {
              "place_id"        : _generate_place_id(card),
              "name"            : card.select_one("h3").text.strip(),
              "region"          : self.region,
              "province"        : _infer_province(self.region),
              "category"        : _parse_category(card),
              "tags"            : _parse_tags(card),
              "description"     : _parse_description(card),
              "location"        : _parse_location(card),   # lat, lon, address
              "duration_minutes": _parse_duration(card),
              "opening_hours"   : _parse_hours(card),
              "price"           : _parse_price(card),
              "rating"          : float(card.select_one("[class*='rating']").text or 0),
              "review_count"    : _parse_review_count(card),
              "popularity_score": 0.0,                     # tính sau bằng normalize rating×review
              "best_time"       : [],
              "suitable_for"    : [],
              "source"          : "tripadvisor",
              "source_url"      : _parse_url(card),
              "last_updated"    : datetime.today().strftime("%Y-%m-%d"),
            }
            places.append(place)
          return places
        """
        # TODO: implement
        pass

    # ── Helper methods ────────────────────────────────────────────────

    def _generate_place_id(self, region: str, index: int) -> str:
        """
        Pseudo:
          prefix = region.upper()[:2]
          return f"VN-{prefix}-{index:03d}"
        """
        # TODO: implement
        pass

    def _parse_location(self, card) -> dict:
        """
        Trả về {"lat": float, "lon": float, "address": str}.
        lat/lon có thể lấy từ data-lat/data-lng attribute hoặc gọi thêm Geocoding API.

        Pseudo:
          lat = float(card.get("data-lat", 0))
          lon = float(card.get("data-lng", 0))
          address = card.select_one("[class*='address']").text.strip()
          return {"lat": lat, "lon": lon, "address": address}
        """
        # TODO: implement
        pass

    def _parse_price(self, card) -> dict:
        """
        Pseudo:
          raw_price = card.select_one("[class*='price']").text
          adult     = _extract_number(raw_price)
          return {
            "adult"       : adult,
            "child"       : int(adult * 0.6),   # ước tính nếu không có
            "currency"    : "VND",
            "budget_level": _map_budget_level(adult),
          }
        """
        # TODO: implement
        pass
