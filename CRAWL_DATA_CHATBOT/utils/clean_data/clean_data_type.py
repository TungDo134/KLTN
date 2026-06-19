"""
2. CLEAN DATA TYPES
"""

from pathlib import Path
import json
import re
import unicodedata


INPUT_DIR = Path(r"D:\KLTN\Project\CRAWL_DATA_CHATBOT\utils\enrich_data_region")
OUTPUT_DIR = Path(r"D:\KLTN\Project\CRAWL_DATA_CHATBOT\utils\enrich_data_type")

VALID_TYPES = {
    "attraction",
    "historical_site",
    "religious_site",
    "museum",
    "park",
    "beach",
    "natural_site",
    "restaurant",
    "cafe",
    "shopping",
    "market",
    "spa",
    "bar",
    "entertainment",
    "accommodation",
    "transport_service",
    "tour_service",
    "other",
}

TYPE_ALIASES = {
    "pagoda": "religious_site",
    "temple": "religious_site",
    "church": "religious_site",
    "cathedral": "religious_site",
}

NAME_MATCH_SCORE = 4
CATEGORY_MATCH_SCORE = 4
COMBO_MATCH_SCORE = 4
TAG_MATCH_SCORE = 2
ADDRESS_MATCH_SCORE = 1
OLD_TYPE_SCORE = 2
MIN_TYPE_SCORE = 4

STRICT_WORD_KEYWORDS = {
    "bar",
    "bay",
    "bun",
    "bus",
    "cau",
    "cho",
    "dao",
    "doi",
    "farm",
    "game",
    "hang",
    "hill",
    "hon",
    "kem",
    "lake",
    "lang",
    "mart",
    "mien",
    "nui",
    "oc",
    "park",
    "pho",
    "shop",
    "show",
    "spa",
    "taxi",
    "tour",
    "tours",
    "train",
    "war",
    "wine",
}

TYPE_RULES = [
    (
        "spa",
        [
            "spa",
            "massage",
            "nail",
            "wellness",
            "foot massage",
            "body massage",
            "tam bun",
            "mud bath",
            "onsen",
            "jjimjilbang",
            "beauty room",
            "goi dau duong sinh",
            "tham my",
            "masage",
            "foot masage",
        ],
    ),
    (
        "restaurant",
        [
            "restaurant",
            "nha hang",
            "quan an",
            "bistro",
            "buffet",
            "seafood",
            "hai san",
            "bbq",
            "sushi",
            "ramen",
            "udon",
            "pho bo",
            "pho ga",
            "pho thin",
            "pho bat dan",
            "pho 10",
            "bun",
            "oc",
            "nhau",
            "do an",
            "cuisine",
            "hu tieu",
            "mien",
            "my van than",
            "nem cua be",
            "kitchen",
            "food man",
            "street food",
            "am thuc",
            "an uong",
            "mon an",
            "dac san",
            "bep",
            "pizza",
            "burger",
            "hotpot",
            "grill",
            "steakhouse",
            "vegan",
            "com tam",
            "banh mi",
            "deli",
        ],
    ),
    (
        "cafe",
        [
            "cafe",
            "coffee",
            "ca phe",
            "tra sua",
            "tea house",
            "bakery",
            "phe la",
            "gateaux",
            "gâteaux",
            "tous les jours",
            "kem",
            "caramen",
            "dessert",
            "banh",
            "madame huong",
            "do uong",
            "barista",
            "kafe",
            "caffe",
            "tea",
            "bean",
            "three o'clock",
            "three o’clock",
        ],
    ),
    (
        "bar",
        [
            "bar",
            "pub",
            "club",
            "lounge",
            "beer",
            "nightclub",
            "rooftop",
            "skylight",
            "ta hien",
            "bia hoi",
            "wine",
            "cigar",
            "tavern",
            "observatory",
            "cocktail",
            "shisha",
            "speakeasy",
            "acoustic",
            "skybar",
            "club99",
            "sky36",
        ],
    ),
    ("market", ["market", "cho", "night market"]),
    (
        "shopping",
        [
            "mall",
            "shopping",
            "plaza",
            "store",
            "shop",
            "sieu thi",
            "cua hang",
            "lotte mart",
            "mart",
            "tailor",
            "duong sach",
            "book street",
            "outlet",
            "fashion",
            "souvenir",
            "outdoor",
            "mini mart",
            "vintage",
            "silk",
            "handmade",
            "scent lab",
            "leather",
            "jewelry",
            "optical",
            "ao dai",
            "embroidery",
            "gift",
            "trang suc",
            "yarn",
            "candles",
            "mua sam",
            "perfume",
            "chocolate",
            "cacao",
            "swimwear",
            "floral",
            "giftshop",
            "gifts",
            "costumes",
            "accessories",
            "optic",
            "handicrafts",
            "boutique",
            "bookstore",
            "xiaomi",
            "parkson",
            "gigamall",
            "big c",
            "takashimaya",
            "saigon square",
            "sai gon square",
            "central square",
            "lam son square",
        ],
    ),
    (
        "religious_site",
        [
            "chua",
            "pagoda",
            "temple",
            "nha tho",
            "church",
            "cathedral",
            "den tho",
            "mieu",
            "linh ung",
            "lady buddha",
            "tinh xa",
            "co tu",
            "phat dai",
            "giao xu",
            "thich ca",
            "duc me",
            "monastery",
            "zen monastery",
            "shrine",
            "vihara",
            "thanh that",
            "phap vien",
            "minh dang quang",
            "tam linh",
            "ton giao",
            "mosque",
        ],
    ),
    ("museum", ["museum", "bao tang", "gallery", "trien lam", "exhibition"]),
    (
        "beach",
        [
            "beach",
            "bai bien",
            "bien",
            "bai tam",
            "bai dai",
            "bai truoc",
            "bai sau",
            "bai dua",
            "pham van dong beach",
        ],
    ),
    (
        "natural_site",
        [
            "mountain",
            "nui",
            "lake",
            "waterfall",
            "thac",
            "cave",
            "hang",
            "island",
            "river",
            "song",
            "suoi",
            "forest",
            "rung",
            "doi",
            "hill",
            "dinh ban co",
            "hon",
            "vinh",
            "bay",
            "mangrove",
            "biosphere",
            "reserve",
            "peninsula",
            "banyan tree",
            "cao nguyen",
            "lang hoa",
            "canh dong hoa",
            "sinh thai",
            "farm",
            "lavender",
            "highlands",
            "truc bach",
            "ho thuy quai",
            "ho ca",
            "thien nhien",
            "langbiang",
            "grotto",
            "cay da",
        ],
    ),
    (
        "historical_site",
        [
            "di tich",
            "historic",
            "historical",
            "heritage",
            "pho co",
            "old quarter",
            "citadel",
            "thanh co",
            "dinh",
            "lang",
            "prison",
            "war",
            "tunnels",
            "dia dao",
            "battle",
            "memorial",
            "tuong niem",
            "former",
            "embassy",
            "thap cham",
            "ponagar",
            "po nagar",
            "cu chi",
            "long tan",
            "martyrs",
            "ancient house",
            "viet phu",
            "flag tower",
            "french quarter",
            "pedagogy college",
            "old house",
            "nha xua",
            "can cu",
            "lich su",
            "diem moc lich su",
            "nha lao",
            "nha san",
            "monument",
            "statue",
            "uy ban",
        ],
    ),
    (
        "entertainment",
        [
            "sun world",
            "vinwonders",
            "karaoke",
            "cinema",
            "rap phim",
            "game",
            "theme park",
            "amusement",
            "water park",
            "show",
            "vong quay",
            "ferris wheel",
            "nha hat",
            "theater",
            "theatre",
            "mua roi",
            "xiec",
            "do theater",
            "upside down",
            "nha up nguoc",
            "escape room",
            "escape rooms",
            "aquarium",
            "thuy cung",
            "archery",
            "climb",
            "golf",
            "padel",
            "bida",
            "fitness",
            "gym",
            "arena",
            "kitesurfing",
            "giai tri",
            "khu vui choi",
            "coaster",
            "bowling",
            "pickleball",
            "water puppet",
            "immersive",
            "magic show",
        ],
    ),
    (
        "park",
        [
            "park",
            "cong vien",
            "garden",
            "vuon",
            "zoo",
            "botanical",
            "khu du lich",
            "kdl",
            "mongo land",
            "dapa hill",
            "fresh da lat",
            "pini",
            "la phong",
            "tourist area",
            "fresh dalat",
            "camping",
        ],
    ),
    (
        "tour_service",
        [
            "tour",
            "tours",
            "travel agency",
            "tourist agency",
            "tourist company",
            "klook",
            "globaltix",
            "ticket",
            "excursion",
            "trips",
            "cooking class",
            "travelogy",
            "travel group",
            "travel holiday",
            "travel company",
            "day tours",
            "walking tours",
            "food tours",
            "motorbike tours",
            "bike tours",
            "easyrider",
            "easy rider",
            "cruise",
            "cruises",
            "junks",
            "du thuyen",
            "adventures",
            "riders",
        ],
    ),
    (
        "accommodation",
        [
            "hotel",
            "resort",
            "homestay",
            "villa",
            "hostel",
            "apartment",
            "khach san",
            "khu nghi duong",
        ],
    ),
    (
        "transport_service",
        [
            "airport",
            "san bay",
            "train station",
            "railway station",
            "nha ga",
            "bus station",
            "ben xe",
            "xe buyt",
            "taxi",
            "car rental",
            "bike rental",
            "ben thuyen",
            "ben tau",
            "tau cao toc",
            "cable car",
            "cap treo",
            "marina",
            "greenlines",
            "transport",
            "transfer",
            "transfers",
            "private car",
            "limousine",
            "limo",
            "railways",
            "express",
            "bus express",
            "motorbike rental",
            "rent motor",
            "thue xe",
            "thue xe may",
        ],
    ),
    (
        "attraction",
        [
            "cau",
            "hai dang",
            "tuong",
            "tuong dai",
            "quang truong",
            "skydeck",
            "cong hoa giay",
            "check in",
            "tranh dep",
            "art studio",
            "photo studio",
            "thap tram huong",
            "cau vang",
            "cau rong",
            "bridge",
            "observatory",
            "tower",
            "landmark",
            "sculpture",
        ],
    ),
]

RAW_NAME_RULES = {
    "restaurant": [
        "phở",
        "ốc",
        "mỳ",
        "mì",
        "xôi",
        "chè",
        "ẩm thực",
        "cơm",
        "nướng",
        "lẩu",
        "chay",
    ],
    "religious_site": ["đền", "chùa", "nhà thờ", "samten hills"],
    "natural_site": [
        "đảo",
        "bãi",
        "mũi",
        "thung lũng",
        "tuyệt tình cốc",
        "mỏ đá",
        "động",
        "cây đa",
    ],
    "historical_site": [
        "nhà lưu niệm",
        "nhà lao",
        "nhà sàn",
        "ủy ban",
        "ô quan chưởng",
    ],
    "attraction": [
        "cột cờ",
        "bưu điện",
        "tháp",
        "phố đi bộ",
        "quảng trường",
        "con đường",
        "đường hầm",
        "điêu khắc",
        "phố bích họa",
        "đường bùi viện",
        "đường đồng khởi",
        "ngã sáu",
        "khu phố du lịch",
    ],
    "park": ["bà nà hills"],
    "shopping": ["tiệm may", "tiệm áo", "tiệm yến", "yến sào", "mắt kính"],
    "bar": ["bia hơi"],
    "cafe": ["trà", "cà phê"],
}

COMBO_NAME_RULES = {
    "tour_service": [
        (
            ["travel"],
            ["agency", "company", "group", "tour", "tours", "holiday", "sport"],
        ),
        (["adventure", "adventures"], ["tour", "tours", "travel", "rider", "riders"]),
        (["discovery"], ["tour", "tours", "travel"]),
        (["motorbike"], ["tour", "tours", "rider", "rental"]),
    ],
    "transport_service": [
        (["rental"], ["bike", "motorbike", "scooter", "car"]),
        (["transfer"], ["airport", "private", "car"]),
    ],
    "shopping": [
        (["center", "centre"], ["shopping", "commercial", "mall"]),
        (["tiem"], ["hoa", "ao", "kinh", "yen", "qua", "may"]),
        (["studio"], ["fashion", "gift", "floral", "handmade", "craft"]),
        (["shop"], ["gift", "souvenir", "flower", "chocolate", "perfume"]),
        (["tiem"], ["hoa", "ao", "kinh", "yen", "qua", "may"]),
        (["studio"], ["fashion", "gift", "floral", "handmade", "craft"]),
        (["shop"], ["gift", "souvenir", "flower", "chocolate", "perfume"]),
    ],
    "entertainment": [
        (["studio"], ["game", "gaming", "immersive", "yoga", "pilates"]),
        (["theatre", "theater"], ["show", "water", "do"]),
    ],
    "spa": [
        (["salon"], ["beauty", "hair", "men", "women"]),
        (["head"], ["spa"]),
    ],
}

PHASE2_RULES = [
    (
        "attraction",
        [
            "train street",
        ],
    ),
    (
        "transport_service",
        [
            "airport",
            "bus station",
            "car rental",
            "limousine",
            "motorbike rental",
            "private car",
            "railway",
            "taxi",
            "train",
            "transfer",
        ],
    ),
    (
        "tour_service",
        [
            "adventure tour",
            "bike tour",
            "cruise",
            "day tour",
            "easyrider",
            "easy rider",
            "excursion",
            "food experience",
            "food tour",
            "journey",
            "motorbike tour",
            "tour",
            "tours",
            "travel",
            "trip",
            "walking tour",
        ],
    ),
    (
        "spa",
        [
            "headspa",
            "massage",
            "retreat yoga",
            "spa",
            "wellness",
            "yoga",
        ],
    ),
    (
        "museum",
        [
            "contemporary art",
            "art gallery",
            "exhibition",
            "gallery",
            "museum",
            "vcca",
        ],
    ),
    (
        "entertainment",
        [
            "aquafield",
            "basketball",
            "cgv",
            "game",
            "golf",
            "helio center",
            "zoo",
        ],
    ),
    (
        "market",
        [
            "market",
            "night market",
        ],
    ),
    (
        "shopping",
        [
            "antique street",
            "bookstore",
            "craft",
            "fruit",
            "langfarm",
            "mall",
            "nha trang center",
            "saigon centre",
            "shopping",
            "silver house",
            "silver jewelry",
            "silver jewlery",
            "souvenir",
            "store",
            "vincom",
        ],
    ),
    (
        "cafe",
        [
            "cafe",
            "coffee",
        ],
    ),
    (
        "restaurant",
        [
            "bistro",
            "kitchen",
            "restaurant",
        ],
    ),
    (
        "bar",
        [
            "bar",
            "beer",
            "pub",
        ],
    ),
]


def normalize_text(value) -> str:
    """
    Normalize Unicode, lowercase text, and remove Vietnamese accents for rule matching.
    """
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = text.replace("\u0111", "d")
    text = text.replace("đ", "d")
    text = unicodedata.normalize("NFKC", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", text)


def keyword_matches(search_text: str, keyword: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return False

    if " " not in normalized_keyword and (
        len(normalized_keyword) <= 4 or normalized_keyword in STRICT_WORD_KEYWORDS
    ):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
        return re.search(pattern, search_text) is not None

    return normalized_keyword in search_text


def raw_keyword_matches(search_text: str, keyword: str) -> bool:
    search_text = unicodedata.normalize("NFC", str(search_text).strip().lower())
    keyword = unicodedata.normalize("NFC", str(keyword).strip().lower())
    if not keyword:
        return False

    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, search_text) is not None


def combo_matches(search_text: str, keyword_groups: tuple[list[str], ...]) -> bool:
    return all(
        any(keyword_matches(search_text, keyword) for keyword in group)
        for group in keyword_groups
    )


def detect_phase2_type(record: dict) -> str:
    name_text = normalize_text(record.get("name", ""))

    for detected_type, keywords in PHASE2_RULES:
        if any(keyword_matches(name_text, keyword) for keyword in keywords):
            return detected_type

    return "other"


def normalize_tags(tags) -> list[str]:
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []

    return [str(tag).strip() for tag in tags if str(tag).strip()]


def extract_category_text(address: str) -> str:
    if "·" not in address:
        return ""

    category = address.split("·", 1)[0].strip()
    if len(category) > 80:
        return ""

    return category


def build_search_parts(record: dict) -> tuple[str, str, str, str]:
    name = record.get("name", "")
    tags = normalize_tags(record.get("tags", []))
    address = record.get("geo", {}).get("address", "")
    category = extract_category_text(str(address))

    return (
        normalize_text(name),
        normalize_text(category),
        normalize_text(" ".join(tags)),
        normalize_text(address),
    )


def score_type(
    detected_type: str,
    keywords: list[str],
    old_type: str,
    raw_name_text: str,
    name_text: str,
    category_text: str,
    tags_text: str,
    address_text: str,
) -> int:
    score = 0

    if any(
        raw_keyword_matches(raw_name_text, keyword)
        for keyword in RAW_NAME_RULES.get(detected_type, [])
    ):
        score += NAME_MATCH_SCORE

    if any(keyword_matches(name_text, keyword) for keyword in keywords):
        score += NAME_MATCH_SCORE

    if any(
        combo_matches(name_text, keyword_groups)
        for keyword_groups in COMBO_NAME_RULES.get(detected_type, [])
    ):
        score += COMBO_MATCH_SCORE

    if any(keyword_matches(category_text, keyword) for keyword in keywords):
        score += CATEGORY_MATCH_SCORE

    if any(keyword_matches(tags_text, keyword) for keyword in keywords):
        score += TAG_MATCH_SCORE

    if any(keyword_matches(address_text, keyword) for keyword in keywords):
        score += ADDRESS_MATCH_SCORE

    if old_type == detected_type and old_type != "attraction":
        score += OLD_TYPE_SCORE

    return score


def detect_type(record: dict) -> str:
    """
    Tạo type mới cho một địa điểm.
    """
    old_type = normalize_text(record.get("type", ""))
    if old_type in TYPE_ALIASES:
        return TYPE_ALIASES[old_type]

    raw_name_text = str(record.get("name", "")).strip().lower()
    name_text, category_text, tags_text, address_text = build_search_parts(record)
    best_type = "other"
    best_score = 0

    for detected_type, keywords in TYPE_RULES:
        score = score_type(
            detected_type,
            keywords,
            old_type,
            raw_name_text,
            name_text,
            category_text,
            tags_text,
            address_text,
        )

        if score > best_score:
            best_type = detected_type
            best_score = score

    if best_score >= MIN_TYPE_SCORE:
        return best_type

    return detect_phase2_type(record)


def enrich_type_file(input_path: Path, output_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"{input_path.name} phải tồn tại trong JSON list")

    changed_count = 0
    unchanged_count = 0
    type_counter = {}

    for record in records:
        if not isinstance(record, dict):
            continue

        old_type = record.get("type")
        new_type = detect_type(record)

        if old_type != new_type:
            record["type"] = new_type
            changed_count += 1
        else:
            unchanged_count += 1

        type_counter[new_type] = type_counter.get(new_type, 0) + 1

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return {
        "filename": input_path.name,
        "total_records": len(records),
        "changed_type_count": changed_count,
        "unchanged_type_count": unchanged_count,
        "type_counter": type_counter,
        "output_path": str(output_path),
    }


def check_type_values(data_dir: Path = OUTPUT_DIR) -> dict:
    total_records = 0
    invalid_count = 0
    other_count = 0
    invalid_values = {}

    print("\n[CHECK TYPE VALUES]")

    for json_path in sorted(data_dir.glob("*.json")):
        with json_path.open("r", encoding="utf-8") as f:
            records = json.load(f)

        file_invalid_count = 0

        for record in records:
            if not isinstance(record, dict):
                continue

            place_type = record.get("type")
            total_records += 1

            if place_type == "other":
                other_count += 1

            if place_type not in VALID_TYPES:
                invalid_count += 1
                file_invalid_count += 1
                invalid_values[place_type] = invalid_values.get(place_type, 0) + 1

        print(
            f"[CHECK] {json_path.name} | "
            f"records={len(records)} | "
            f"invalid_type={file_invalid_count}"
        )

    print(
        "\n[CHECK DONE] "
        f"records={total_records} | "
        f"other={other_count} | "
        f"invalid_type={invalid_count} | "
        f"invalid_values={invalid_values}"
    )

    return {
        "total_records": total_records,
        "other": other_count,
        "invalid_type": invalid_count,
        "invalid_values": invalid_values,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_records = 0
    total_changed = 0
    total_unchanged = 0

    for input_path in sorted(INPUT_DIR.glob("*.json")):
        output_path = OUTPUT_DIR / input_path.name
        summary = enrich_type_file(input_path, output_path)

        total_files += 1
        total_records += summary["total_records"]
        total_changed += summary["changed_type_count"]
        total_unchanged += summary["unchanged_type_count"]

        print(
            f"\n[OK] {summary['filename']} | "
            f"records={summary['total_records']} | "
            f"changed={summary['changed_type_count']} | "
            f"unchanged={summary['unchanged_type_count']} | "
            f"output={summary['output_path']}"
        )

        print(f"type_counter={summary['type_counter']}")

    print(
        "\n[DONE] "
        f"files={total_files} | "
        f"records={total_records} | "
        f"type_changed={total_changed} | "
        f"type_unchanged={total_unchanged}"
    )

    check_type_values(OUTPUT_DIR)


if __name__ == "__main__":
    main()
