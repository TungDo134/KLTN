"""
crawlers/base_crawler.py
Abstract base class cho tất cả crawlers.
Cung cấp: session management, retry logic, delay, logging.
Mọi crawler cụ thể (TripAdvisor, Foursquare...) đều kế thừa class này.
"""

from abc import ABC, abstractmethod


class BaseCrawler(ABC):
    def __init__(self, region: str):
        """
        region : tên khu vực, vd: "dalat", "hanoi"
        session: requests.Session — tái sử dụng connection, gắn headers chung
        """
        # TODO:
        #   self.region  = region
        #   self.session = requests.Session()
        #   self.session.headers.update({"User-Agent": "...", "Accept-Language": "vi"})
        pass

    @abstractmethod
    def crawl(self) -> list[dict]:
        """
        Crawl toàn bộ địa điểm của region.
        Trả về list các raw dict (chưa validate).

        Pseudo:
          results = []
          for page in range(1, MAX_PAGES+1):
            raw = _fetch_page(page)
            if not raw: break
            results.extend(_parse_page(raw))
            time.sleep(REQUEST_DELAY_SEC)
          return results
        """
        pass

    @abstractmethod
    def _fetch_page(self, page: int) -> dict | None:
        """
        Gọi HTTP GET đến URL tương ứng.

        Pseudo:
          url    = _build_url(page)
          for attempt in range(MAX_RETRIES):
            try:
              resp = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
              resp.raise_for_status()
              return resp.json()   # hoặc resp.text nếu cần parse HTML
            except RequestException as e:
              log warning, time.sleep(2 ** attempt)  # exponential backoff
          return None
        """
        pass

    @abstractmethod
    def _parse_page(self, raw: dict) -> list[dict]:
        """
        Parse raw response → list[dict] theo đúng place schema.
        Mỗi subclass tự implement vì mỗi source có cấu trúc HTML/JSON khác nhau.
        """
        pass

    def _build_url(self, page: int) -> str:
        """
        Tạo URL phân trang cho region.
        Pseudo:
          BASE_URL = "https://..."
          return f"{BASE_URL}?location={self.region}&page={page}"
        """
        # TODO: implement trong subclass hoặc override
        pass

    def save_raw(self, data: list[dict], out_path: str) -> None:
        """
        Lưu kết quả crawl thô ra file JSON để debug / re-ingest mà không cần crawl lại.
        Pseudo:
          with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        """
        # TODO: implement
        pass
