from pathlib import Path
import json

INPUT_DIR = Path(r"D:\KLTN\Project\BE_ChatBot\src\source_data\places_data")

OUTPUT_DIR = Path(r"D:\KLTN\Project\BE_ChatBot\src\utils\enrich_data")

REGION_BY_FILENAME = {
    "hanoi_merged.json": "Hà Nội",
    "hcm_merged.json": "TP. Hồ Chí Minh",
    "danang_merged.json": "Đà Nẵng",
    "nhatrang_merged.json": "Nha Trang",
    "dalat_merged.json": "Đà Lạt",
    "vungtau_merged.json": "Vũng Tàu",
}


# CLEAN REGION
def clean_region_file(input_path: Path, output_path: Path, expected_region: str):
    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"{input_path.name} phải tồn tại trong JSON list")

    changed_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue

        old_region = record.get("region")
        if old_region != expected_region:
            record["region"] = expected_region
            changed_count += 1

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return {
        "filename": input_path.name,
        "expected_region": expected_region,
        "total_records": len(records),
        "changed_region_count": changed_count,
        "unchanged_region_count": len(records) - changed_count,
        "output_path": str(output_path),
    }


# CHECK REGION IS VALID
def check_region_matches(data_dir: Path = OUTPUT_DIR):
    total_files = 0
    total_records = 0
    total_matched = 0
    total_unmatched = 0

    print("\n[CHECK REGION MATCH]")

    for json_path in sorted(data_dir.glob("*.json")):
        expected_region = REGION_BY_FILENAME.get(json_path.name)

        if expected_region is None:
            print(f"[SKIP] Unknown region for file: {json_path.name}")
            continue

        with json_path.open("r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            raise ValueError(f"{json_path.name} phải tồn tại trong list JSON")

        matched_count = 0
        unmatched_count = 0

        for record in records:
            if not isinstance(record, dict):
                unmatched_count += 1
                continue

            if record.get("region") == expected_region:
                matched_count += 1
            else:
                unmatched_count += 1

        total_files += 1
        total_records += len(records)
        total_matched += matched_count
        total_unmatched += unmatched_count

        print(
            f"[CHECK] {json_path.name} | "
            f"expected={expected_region} | "
            f"matched={matched_count} | "
            f"unmatched={unmatched_count}"
        )

    print(
        "\n[CHECK DONE] "
        f"files={total_files} | "
        f"records={total_records} | "
        f"matched={total_matched} | "
        f"unmatched={total_unmatched}"
    )

    return {
        "total_files": total_files,
        "total_records": total_records,
        "matched": total_matched,
        "unmatched": total_unmatched,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_records = 0
    total_changed = 0

    for input_path in sorted(INPUT_DIR.glob("*.json")):
        expected_region = REGION_BY_FILENAME.get(input_path.name)

        if expected_region is None:
            print(f"[SKIP] Unknown region for file: {input_path.name}")
            continue

        output_path = OUTPUT_DIR / input_path.name
        summary = clean_region_file(input_path, output_path, expected_region)

        total_files += 1
        total_records += summary["total_records"]
        total_changed += summary["changed_region_count"]

        print(
            f"\n [OK] {summary['filename']} | "
            f"region={summary['expected_region']} | "
            f"records={summary['total_records']} | "
            f"changed={summary['changed_region_count']} | "
            f"output={summary['output_path']}"
        )

    print(
        "\n[DONE] "
        f"files={total_files} | "
        f"records={total_records} | "
        f"region_changed={total_changed}"
    )

    check_region_matches(OUTPUT_DIR)


if __name__ == "__main__":
    main()
