"""Fill zero entrance fees with deterministic demo values.

Run this script manually from the project root:
    python BE_ChatBot/utils/fill_demo_entrance_fees.py
"""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata


DATA_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "source_data"
    / "places_data"
)
EXPECTED_FILE_COUNT = 6
EXPECTED_PLACE_COUNT = 600
PRICE_STEP = 10_000

PRICE_RANGES = {
    "cafe": (30_000, 100_000),
    "restaurant": (50_000, 200_000),
    "resort": (100_000, 300_000),
    "farm": (30_000, 100_000),
    "market": (20_000, 60_000),
    "spiritual": (10_000, 30_000),
    "square": (10_000, 30_000),
    "landmark": (10_000, 50_000),
    "park": (10_000, 50_000),
    "nature": (20_000, 80_000),
    "lake": (20_000, 80_000),
    "historical": (20_000, 80_000),
    "culture": (20_000, 80_000),
}
DEFAULT_PRICE_RANGE = (20_000, 100_000)

BRANCH_SUFFIX_PATTERN = re.compile(
    r"\s*\(Cụm/Chi nhánh\s+\d+\)\s*$",
    re.IGNORECASE,
)


def _normalize_text(value):
    normalized = unicodedata.normalize("NFC", str(value))
    return " ".join(normalized.split()).casefold()


def _canonical_name(name):
    normalized = unicodedata.normalize("NFC", str(name))
    without_branch_suffix = BRANCH_SUFFIX_PATTERN.sub("", normalized)
    return _normalize_text(without_branch_suffix)


def _group_key(place):
    region = _normalize_text(place.get("region", ""))
    name = _canonical_name(place.get("name", ""))
    if not region or not name:
        raise ValueError(
            f"Place {place.get('id', '<missing id>')} must have region and name."
        )
    return f"{region}|{name}"


def _validate_entrance_fee(place):
    entrance_fee = place.get("entrance_fee")
    is_number = isinstance(entrance_fee, (int, float)) and not isinstance(
        entrance_fee,
        bool,
    )
    if not is_number or entrance_fee < 0:
        raise ValueError(
            f"Place {place.get('id', '<missing id>')} has invalid entrance_fee: "
            f"{entrance_fee!r}."
        )


def _load_places():
    json_files = sorted(DATA_DIRECTORY.glob("*.json"))
    if len(json_files) != EXPECTED_FILE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_FILE_COUNT} JSON files in {DATA_DIRECTORY}, "
            f"found {len(json_files)}."
        )

    places_by_file = {}
    total_places = 0

    for json_file in json_files:
        places = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(places, list):
            raise ValueError(f"{json_file.name} must contain a JSON array.")

        for place in places:
            if not isinstance(place, dict):
                raise ValueError(f"{json_file.name} contains a non-object place.")
            _validate_entrance_fee(place)

        places_by_file[json_file] = places
        total_places += len(places)

    if total_places != EXPECTED_PLACE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_PLACE_COUNT} places, found {total_places}."
        )

    return places_by_file


def _deterministic_price(group_key, place_type):
    minimum, maximum = PRICE_RANGES.get(
        _normalize_text(place_type),
        DEFAULT_PRICE_RANGE,
    )
    price_count = ((maximum - minimum) // PRICE_STEP) + 1
    digest = sha256(group_key.encode("utf-8")).digest()
    price_index = int.from_bytes(digest[:8], byteorder="big") % price_count
    return minimum + price_index * PRICE_STEP


def _select_group_fee(group_key, places):
    positive_places = sorted(
        (place for place in places if place["entrance_fee"] > 0),
        key=lambda place: str(place.get("id", "")),
    )
    if positive_places:
        return positive_places[0]["entrance_fee"]

    representative = min(places, key=lambda place: str(place.get("id", "")))
    return _deterministic_price(group_key, representative.get("type", ""))


def _write_places(json_file, places):
    with json_file.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(places, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def main():
    places_by_file = _load_places()
    grouped_places = defaultdict(list)

    for places in places_by_file.values():
        for place in places:
            grouped_places[_group_key(place)].append(place)

    group_fees = {
        group_key: _select_group_fee(group_key, places)
        for group_key, places in grouped_places.items()
    }

    updated_by_file = defaultdict(int)
    for json_file, places in places_by_file.items():
        for place in places:
            if place["entrance_fee"] == 0:
                place["entrance_fee"] = group_fees[_group_key(place)]
                updated_by_file[json_file] += 1

    all_places = [
        place
        for places in places_by_file.values()
        for place in places
    ]
    if any(place["entrance_fee"] <= 0 for place in all_places):
        raise ValueError("All entrance_fee values must be greater than zero.")

    updated_count = sum(updated_by_file.values())
    if updated_count == 0:
        print("No zero entrance fees found. No files were changed.")
        return

    for json_file, places in places_by_file.items():
        if updated_by_file[json_file] > 0:
            _write_places(json_file, places)
            print(f"{json_file.name}: updated {updated_by_file[json_file]} places")

    print(
        f"Completed: updated {updated_count} places; "
        f"{len(all_places)} entrance fees are now greater than zero."
    )


if __name__ == "__main__":
    main()
