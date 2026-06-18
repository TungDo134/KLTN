from pathlib import Path
import json
import re
import unicodedata


INPUT_DIR = Path(r"D:\KLTN\Project\BE_ChatBot\src\utils\enrich_data_type")
OUTPUT_DIR = Path(r"D:\KLTN\Project\BE_ChatBot\src\utils\enrich_data_tag")

TYPE_BASE_TAGS = {
    "attraction": ["khám phá", "tham quan", "check-in"],
    "historical_site": ["lịch sử", "văn hóa", "tham quan"],
    "religious_site": ["tâm linh", "văn hóa", "tham quan"],
    "museum": ["văn hóa", "lịch sử", "trong nhà"],
    "park": ["ngoài trời", "gia đình", "trẻ em"],
    "beach": ["biển", "thiên nhiên", "ngoài trời", "check-in"],
    "natural_site": ["thiên nhiên", "ngoài trời", "check-in"],
    "restaurant": ["ẩm thực", "địa phương"],
    "cafe": ["cafe", "thư giãn", "check-in"],
    "shopping": ["mua sắm", "trong nhà"],
    "market": ["chợ", "mua sắm", "địa phương"],
    "spa": ["spa", "thư giãn", "nghỉ dưỡng"],
    "bar": ["nightlife", "giải trí"],
    "entertainment": ["giải trí", "gia đình"],
    "accommodation": ["nghỉ dưỡng", "thư giãn"],
    "transport_service": ["di chuyển", "dịch vụ"],
    "tour_service": ["tour", "trải nghiệm", "địa phương"],
}

GENERIC_TAGS = {
    "khám phá",
    "tham quan",
    "địa điểm",
}

MAX_TAGS_FOR_TYPED_RECORD = 6

STRICT_WORD_KEYWORDS = {
    "bai",
    "bar",
    "bus",
    "cafe",
    "cho",
    "dao",
    "doi",
    "hon",
    "kids",
    "lake",
    "mall",
    "mart",
    "nui",
    "park",
    "pub",
    "shop",
    "spa",
    "taxi",
    "tour",
    "view",
}

KEYWORD_TAG_RULES = [
    (["biển", "bien", "bãi", "bai", "beach"], ["biển", "ngoài trời"]),
    (["núi", "nui", "đồi", "doi", "hill", "mountain"], ["thiên nhiên", "ngoài trời"]),
    (["thác", "thac", "waterfall", "suối", "suoi"], ["thiên nhiên", "ngoài trời"]),
    (
        [
            "lake",
            "hồ tây",
            "ho tay",
            "hồ hoàn kiếm",
            "ho hoan kiem",
            "hồ tràm",
            "ho tram",
            "hồ mây",
            "ho may",
            "hồ cá",
            "ho ca",
        ],
        ["thiên nhiên", "thư giãn"],
    ),
    (["hòn", "hon", "island"], ["thiên nhiên", "biển"]),
    (
        ["chùa", "chua", "đền thờ", "den tho", "pagoda", "temple", "church"],
        ["tâm linh", "văn hóa"],
    ),
    (["museum", "bảo tàng", "bao tang", "gallery"], ["văn hóa", "trong nhà"]),
    (["cafe", "coffee", "cà phê", "ca phe"], ["cafe", "thư giãn"]),
    (
        [
            "restaurant",
            "nhà hàng",
            "nha hang",
            "quán ăn",
            "quan an",
            "pho bo",
            "pho ga",
            "pho thin",
            "pho bat dan",
            "pho 10",
        ],
        ["ẩm thực"],
    ),
    (
        ["spa", "massage", "wellness", "onsen", "tắm bùn", "tam bun"],
        ["spa", "thư giãn"],
    ),
    (["bar", "pub", "club", "beer", "nightclub", "rooftop"], ["nightlife", "giải trí"]),
    (["mall", "market", "chợ", "cho", "shop", "mart", "tailor"], ["mua sắm"]),
    (["park", "công viên", "cong vien", "garden"], ["ngoài trời", "gia đình"]),
    (["kids", "children", "trẻ em", "tre em", "family"], ["gia đình", "trẻ em"]),
    (["tour", "cooking class", "excursion", "easyrider"], ["tour", "trải nghiệm"]),
    (
        [
            "cable car",
            "cáp treo",
            "cap treo",
            "bến tàu",
            "ben tau",
            "tàu cao tốc",
            "tau cao toc",
            "bus",
            "taxi",
        ],
        ["di chuyển"],
    ),
    (["check in", "check-in", "view", "photo", "studio"], ["check-in"]),
]


def normalize_text(value) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = text.replace("\u0111", "d")
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


def normalize_tags(tags) -> list[str]:
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []

    normalized = []
    for tag in tags:
        tag = str(tag).strip()
        if tag and tag not in normalized:
            normalized.append(tag)

    return normalized


def dedupe_tags(tags: list[str]) -> list[str]:
    deduped = []
    seen = set()

    for tag in tags:
        tag = str(tag).strip()
        tag_key = normalize_text(tag)
        if tag and tag_key not in seen:
            deduped.append(tag)
            seen.add(tag_key)

    return deduped


def build_search_text(record: dict) -> str:
    name = record.get("name", "")

    return normalize_text(name)


def infer_keyword_tags(record: dict) -> list[str]:
    search_text = build_search_text(record)
    inferred = []

    for keywords, tags in KEYWORD_TAG_RULES:
        if any(keyword_matches(search_text, keyword) for keyword in keywords):
            inferred.extend(tags)

    return dedupe_tags(inferred)


def enrich_tags(record: dict) -> tuple[list[str], int]:
    old_tags = normalize_tags(record.get("tags", []))
    place_type = str(record.get("type") or "").strip()
    keyword_tags = infer_keyword_tags(record)

    if place_type == "other":
        new_tags = dedupe_tags(old_tags + keyword_tags)
        return new_tags, max(len(new_tags) - len(old_tags), 0)

    base_tags = TYPE_BASE_TAGS.get(place_type, [])
    preserved_tags = [
        tag
        for tag in old_tags
        if normalize_text(tag)
        not in {normalize_text(generic) for generic in GENERIC_TAGS}
    ]
    new_tags = dedupe_tags(base_tags + keyword_tags + preserved_tags)
    new_tags = new_tags[:MAX_TAGS_FOR_TYPED_RECORD]
    return new_tags, max(len(new_tags) - len(old_tags), 0)


def clean_tag_file(input_path: Path, output_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"{input_path.name} phải tồn tại trong JSON list")

    other_count = 0
    changed_count = 0
    total_added_tags = 0
    empty_tags_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue

        old_tags = normalize_tags(record.get("tags", []))
        new_tags, added_tags = enrich_tags(record)

        if record.get("type") == "other":
            other_count += 1

        if new_tags != old_tags:
            record["tags"] = new_tags
            changed_count += 1
            total_added_tags += added_tags

        if not new_tags:
            empty_tags_count += 1

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return {
        "filename": input_path.name,
        "total_records": len(records),
        "other_count": other_count,
        "changed_tag_count": changed_count,
        "total_added_tags": total_added_tags,
        "empty_tags_count": empty_tags_count,
        "output_path": str(output_path),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_records = 0
    total_other = 0
    total_changed = 0
    total_added_tags = 0
    total_empty_tags = 0

    for input_path in sorted(INPUT_DIR.glob("*.json")):
        output_path = OUTPUT_DIR / input_path.name
        summary = clean_tag_file(input_path, output_path)

        total_files += 1
        total_records += summary["total_records"]
        total_other += summary["other_count"]
        total_changed += summary["changed_tag_count"]
        total_added_tags += summary["total_added_tags"]
        total_empty_tags += summary["empty_tags_count"]

        print(
            f"\n[OK] {summary['filename']} | "
            f"records={summary['total_records']} | "
            f"other={summary['other_count']} | "
            f"changed_tags={summary['changed_tag_count']} | "
            f"added_tags={summary['total_added_tags']} | "
            f"empty_tags={summary['empty_tags_count']} | "
            f"output={summary['output_path']}"
        )

    print(
        "\n[DONE] "
        f"files={total_files} | "
        f"records={total_records} | "
        f"other={total_other} | "
        f"changed_tags={total_changed} | "
        f"added_tags={total_added_tags} | "
        f"empty_tags={total_empty_tags}"
    )


if __name__ == "__main__":
    main()
