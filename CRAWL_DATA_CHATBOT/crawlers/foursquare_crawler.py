"""
crawlers/foursquare_crawler.py
Crawler dùng Foursquare Places API (có free tier, trả về JSON chuẩn).
Tốt hơn scraping HTML — ổn định hơn, có tọa độ chính xác.

Docs   : https://docs.foursquare.com/developer/reference/place-search
API Key: đặt FSQ_API_KEY trong .env
"""

from crawlers.base_crawler import BaseCrawler


# Map region → tọa độ trung tâm để dùng làm ll param
REGION_COORDS = {
    "dalat": (11.9404, 108.4583),
    "hanoi": (21.0285, 105.8542),
    "hcmc": (10.8231, 106.6297),
    "danang": (16.0544, 108.2022),
}

FSQ_SEARCH_URL = "https://api.foursquare.com/v3/places/search"


class FoursquareCrawler(BaseCrawler):
    def __init__(self, region: str):
        """
        Pseudo:
          super().__init__(region)
          self.api_key = os.getenv("FSQ_API_KEY")
          self.coords  = REGION_COORDS[region]
          self.session.headers.update({
            "Authorization": self.api_key,
            "Accept"       : "application/json",
          })
        """
        # TODO: implement
        pass

    def crawl(self) -> list[dict]:
        """
        Foursquare dùng cursor-based pagination (cursor thay vì page number).

        Pseudo:
          results = []
          cursor  = None
          while True:
            raw    = _fetch_page(cursor)
            if not raw: break
            parsed = _parse_page(raw)
            results.extend(parsed)
            cursor = raw.get("context", {}).get("next_cursor")
            if not cursor: break
            time.sleep(REQUEST_DELAY_SEC)
          return results
        """
        # TODO: implement
        pass

    def _fetch_page(self, cursor: str | None = None) -> dict | None:
        """
        Pseudo:
          params = {
            "ll"    : f"{self.coords[0]},{self.coords[1]}",
            "radius": 20000,   # 20km
            "limit" : 50,
            "categories": "16000",  # Travel & Transportation category
          }
          if cursor: params["cursor"] = cursor
          resp = session.get(FSQ_SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT_SEC)
          return resp.json()
        """
        # TODO: implement
        pass

    def _parse_page(self, raw: dict) -> list[dict]:
        """
        Pseudo:
          places = []
          for item in raw.get("results", []):
            geo = item["geocodes"]["main"]
            place = {
              "place_id"        : f"VN-FSQ-{item['fsq_id']}",
              "name"            : item["name"],
              "region"          : self.region,
              "province"        : _infer_province(self.region),
              "category"        : item["categories"][0]["name"] if item["categories"] else "khác",
              "tags"            : [c["name"] for c in item.get("categories", [])],
              "description"     : "",   # Foursquare free tier không trả description
              "location"        : {
                "lat"    : geo["latitude"],
                "lon"    : geo["longitude"],
                "address": item.get("location", {}).get("formatted_address", ""),
              },
              "duration_minutes": 60,   # default, không có trong API
              "opening_hours"   : _parse_hours(item.get("hours", {})),
              "price"           : {"adult": 0, "child": 0, "currency": "VND", "budget_level": "free"},
              "rating"          : item.get("rating", 0) / 2,  # Foursquare scale 0-10 → 0-5
              "review_count"    : item.get("stats", {}).get("total_ratings", 0),
              "popularity_score": 0.0,
              "best_time"       : [],
              "suitable_for"    : [],
              "source"          : "foursquare",
              "source_url"      : f"https://foursquare.com/v/{item['fsq_id']}",
              "last_updated"    : datetime.today().strftime("%Y-%m-%d"),
            }
            places.append(place)
          return places
        """
        # TODO: implement
        pass
