import re
import unicodedata


def normalize_region(region: str) -> str:
    """Chuan hoa de lookup REGION_TO_ZONE"""
    value = (region or "").strip().lower()
    value = re.sub(r"^(tp\.?|thanh pho|thành phố|tinh|tỉnh)\s+", "", value)
    value = " ".join(value.split())
    return REGION_ALIASES.get(value, value)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


# Match ten ve cac location chung
REGION_ALIASES: dict[str, str] = {
    "hcm": "hồ chí minh",
    "tp hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "sài gòn": "hồ chí minh",
    "saigon": "hồ chí minh",
    "da nang": "đà nẵng",
    "da lat": "đà lạt",
    "ha noi": "hà nội",
    "ha long": "hạ long",
    "nha trang": "nha trang",
    "vung tau": "vũng tàu",
    "phu quoc": "phú quốc",
    "can tho": "cần thơ",
    "hoi an": "hội an",
    "hue": "huế",
    "sapa": "sa pa",
}

# Mapping cac dia diem ve 1 khu vuc
REGION_TO_ZONE: dict[str, str] = {
    # ===== BAC BO =====
    "hà nội": "bac_bo",
    "sa pa": "bac_bo",
    "hạ long": "bac_bo",
    "ninh bình": "bac_bo",
    "hải phòng": "bac_bo",
    "tràng an": "bac_bo",
    "mai châu": "bac_bo",
    "tam đảo": "bac_bo",
    "mộc châu": "bac_bo",
    "cát bà": "bac_bo",
    # ===== TRUNG BO =====
    "huế": "trung_bo",
    "đà nẵng": "trung_bo",
    "hội an": "trung_bo",
    "quy nhơn": "trung_bo",
    "phong nha": "trung_bo",
    # ===== TAY NGUYEN =====
    "đà lạt": "tay_nguyen",
    "buôn ma thuột": "tay_nguyen",
    "kon tum": "tay_nguyen",
    "pleiku": "tay_nguyen",
    "bảo lộc": "tay_nguyen",
    # ===== NAM BO =====
    "hồ chí minh": "nam_bo",
    "vũng tàu": "nam_bo",
    "phú quốc": "nam_bo",
    "cần thơ": "nam_bo",
    "mũi né": "nam_bo",
    "nha trang": "nam_bo",
    "phan thiết": "nam_bo",
    "côn đảo": "nam_bo",
    "long an": "nam_bo",
}

# Moi zone chua list season blocks
CLIMATE_ZONES: dict[str, list[dict]] = {
    "bac_bo": [
        {
            "months": [12, 1, 2],
            "label": "Đông",
            "temp_range": "10-18°C",
            "rain": "ít mưa, hanh khô",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Lạnh, khô ráo, phù hợp tham quan. Vùng núi như Sa Pa có thể rất lạnh.",
            "suggestions": [
                "mang áo ấm dày",
                "cẩn thận sương mù khi di chuyển buổi sáng",
            ],
        },
        {
            "months": [3, 4],
            "label": "Xuân",
            "temp_range": "18-25°C",
            "rain": "mưa phùn, ẩm",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Thời tiết dễ chịu, có thể ẩm nhẹ.",
            "suggestions": ["mang áo khoác mỏng", "chuẩn bị áo mưa nhẹ"],
        },
        {
            "months": [5, 6, 7, 8],
            "label": "Hè",
            "temp_range": "28-38°C",
            "rain": "mưa rào, có thể có giông",
            "risk_level": "medium",
            "should_go": "go_with_caution",
            "notes": "Nóng, mưa bất chợt vào chiều. Tháng 7-8 có thể chịu ảnh hưởng bão.",
            "suggestions": [
                "ưu tiên hoạt động buổi sáng",
                "mang kem chống nắng",
                "theo dõi dự báo bão",
            ],
        },
        {
            "months": [9, 10, 11],
            "label": "Thu",
            "temp_range": "22-30°C",
            "rain": "giảm dần",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Mát, dễ chịu, là thời điểm đẹp để du lịch miền Bắc.",
            "suggestions": [],
        },
    ],
    "trung_bo": [
        {
            "months": [1, 2, 3, 4],
            "label": "Xuân",
            "temp_range": "20-28°C",
            "rain": "ít mưa",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Thời tiết đẹp, nắng ấm, phù hợp biển và tham quan phố cổ.",
            "suggestions": [],
        },
        {
            "months": [5, 6, 7, 8],
            "label": "Hè",
            "temp_range": "30-38°C",
            "rain": "ít mưa, nắng gắt",
            "risk_level": "medium",
            "should_go": "go_with_caution",
            "notes": "Biển đẹp nhưng nắng nóng mạnh, cần chống nắng kỹ.",
            "suggestions": [
                "tránh nắng 11h-14h",
                "mang kem chống nắng SPF50+",
                "uống nhiều nước",
            ],
        },
        {
            "months": [9, 10, 11],
            "label": "Mưa bão",
            "temp_range": "22-28°C",
            "rain": "mưa lớn, bão, lũ",
            "risk_level": "high",
            "should_go": "not_recommended",
            "notes": "Mùa mưa bão chính ở miền Trung, có thể ảnh hưởng lịch trình.",
            "suggestions": [
                "theo dõi cảnh báo bão",
                "hạn chế lịch trình biển",
                "ưu tiên phương án linh hoạt",
            ],
        },
        {
            "months": [12],
            "label": "Chuyển mùa",
            "temp_range": "18-25°C",
            "rain": "mưa giảm dần",
            "risk_level": "medium",
            "should_go": "go_with_caution",
            "notes": "Thời tiết mát hơn, vẫn có thể có mưa.",
            "suggestions": ["mang áo khoác nhẹ", "chuẩn bị áo mưa"],
        },
    ],
    "tay_nguyen": [
        {
            "months": [11, 12, 1, 2, 3, 4],
            "label": "Mùa khô",
            "temp_range": "15-26°C",
            "rain": "ít mưa",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Mát, khô ráo, rất phù hợp tham quan, săn mây và chụp ảnh.",
            "suggestions": ["mang áo ấm cho buổi tối", "giữ ẩm da vì trời khô"],
        },
        {
            "months": [5, 6, 7, 8, 9, 10],
            "label": "Mùa mưa",
            "temp_range": "18-27°C",
            "rain": "mưa nhiều vào chiều",
            "risk_level": "medium",
            "should_go": "go_with_caution",
            "notes": "Vẫn đi được nhưng nên tránh lịch trình ngoài trời vào chiều muộn.",
            "suggestions": [
                "ưu tiên hoạt động buổi sáng",
                "mang áo mưa",
                "cẩn thận đường đèo trơn",
            ],
        },
    ],
    "nam_bo": [
        {
            "months": [12, 1, 2, 3, 4],
            "label": "Mùa khô",
            "temp_range": "25-34°C",
            "rain": "ít mưa",
            "risk_level": "low",
            "should_go": "recommended",
            "notes": "Thời điểm đẹp nhất để đi biển, đảo và city tour.",
            "suggestions": ["mang kem chống nắng", "uống đủ nước"],
        },
        {
            "months": [5, 6, 7, 8, 9, 10, 11],
            "label": "Mùa mưa",
            "temp_range": "24-32°C",
            "rain": "mưa rào ngắn, thường vào chiều",
            "risk_level": "medium",
            "should_go": "go_with_caution",
            "notes": "Mưa thường đến nhanh và tạnh nhanh, vẫn có thể du lịch nếu lịch trình linh hoạt.",
            "suggestions": [
                "mang áo mưa hoặc ô",
                "ưu tiên điểm trong nhà vào buổi chiều",
            ],
        },
    ],
}


def get_climate_block(region: str, month: int) -> dict | None:
    """
    - Lay dung block khi hau theo dia diem + thang
    - Dung khi khong goi dc API hoac thoi gian di > range du bao (16days)
    """
    normalized = normalize_region(region)
    zone = REGION_TO_ZONE.get(normalized)
    if not zone:
        return None

    for block in CLIMATE_ZONES.get(zone, []):
        if month in block["months"]:
            return block

    return None


def build_best_time_overview(zone: str) -> str:
    """
    - Tao summary tong quan cho 1 zone
    - Output ví dụ cho `trung_bo`:
       • Đẹp nhất — Xuân (tháng 1-4): 20-28°C, ít mưa
       • Cần cân nhắc — Hè (tháng 5-8): 30-38°C, nắng gắt
       • Tránh — Mưa bão (tháng 9-11): mưa lớn, bão, lũ
       • Khá tốt — Đông (tháng 12): 18-24°C, mưa giảm dần"
    """
    blocks = CLIMATE_ZONES.get(zone)
    if not blocks:
        return "Không có dữ liệu khí hậu cho vùng này."

    lines = []
    for block in blocks:
        months = ", ".join(str(month) for month in block["months"])
        lines.append(
            f"- {block['label']} (tháng {months}): "
            f"{block['temp_range']}, {block['rain']}. "
            f"{block['notes']}"
        )

    return "\n".join(lines)
