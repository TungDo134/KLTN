```json
{
  "id": "DL_0001",
  "name": "Khu du lịch Thác Datanla",
  "region": "Đà Lạt",
  "type": "waterfall",
  "tags": ["thiên nhiên", "tham quan", "khám phá"],
  "rating": {
    "score": 4.1,
    "review_count": 1398,
    "is_reliable": true
  },
  "geo": {
    "lat": 11.934072535120507,
    "lng": 108.45828858400883,
    "address": "...",
    "is_approximate": true
  },
  "time": {
    "open": "08:00",
    "close": "18:00",
    "is_default": true
  },
  "avg_duration_minutes": 120,
  "entrance_fee": 50000,
  "description": "Khu du lịch Thác Datanla là địa điểm lý tưởng...",
  "metadata": {
    "source_platform": "Google Maps",
    "source_url": "https://..."
  },
  "best_time": "11-03"
}
```

| Field | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `id` | string | Mã địa điểm, ví dụ `DL_0001`. |
| `name` | string | Tên địa điểm. |
| `region` | string | Khu vực, trong file này là `Đà Lạt`. |
| `type` | string | Loại địa điểm: `attraction`, `cafe`, `park`, `waterfall`, ... |
| `tags` | string[] | Nhãn hoạt động/chủ đề dùng tốt cho retrieval/filter. |
| `rating.score` | number | Điểm rating. |
| `rating.review_count` | number | Số lượt review. |
| `rating.is_reliable` | boolean | Độ tin cậy của rating. |
| `geo.lat`, `geo.lng` | number | Tọa độ. |
| `geo.address` | string/null | Địa chỉ hoặc mô tả địa chỉ. |
| `geo.is_approximate` | boolean | Tọa độ có xấp xỉ không. |
| `time.open`, `time.close` | string | Giờ mở/đóng cửa dạng `HH:mm`. |
| `time.is_default` | boolean | Giờ có phải default/generated không. |
| `avg_duration_minutes` | number | Thời lượng tham quan trung bình. |
| `entrance_fee` | number | Phí vào cửa, đơn vị VND. |
| `description` | string | Mô tả ngắn. Nhiều mô tả có dạng template. |
| `metadata.source_platform` | string | Nguồn dữ liệu: `TripAdvisor` hoặc `Google Maps`. |
| `metadata.source_url` | string | URL nguồn. |
| `best_time` | string | Thời điểm phù hợp, sample (tháng) `11-03`. |