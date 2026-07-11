from __future__ import annotations

from pathlib import Path
from typing import Any

from src.eval.common.path_utils import ensure_output_dir, read_csv_dicts, write_csv, write_json


SUMMARY_FILES = (
    "dataset_coverage_summary.csv",
    "retrieval_summary.csv",
    "output_validity_summary.csv",
)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Benchmark report\n\nNo benchmark rows found.\n"

    columns = list(rows[0].keys())
    lines = [
        "# Benchmark report",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "\\|").replace("\n", " ") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return "\n".join(lines)


def build_report(output_dir: Path | None = None) -> tuple[Path, Path, Path]:
    output_dir = ensure_output_dir(output_dir)
    rows: list[dict[str, Any]] = []
    sources: dict[str, int] = {}

    for file_name in SUMMARY_FILES:
        file_rows = read_csv_dicts(output_dir / file_name)
        sources[file_name] = len(file_rows)
        rows.extend(file_rows)

    csv_path = output_dir / "benchmark_table.csv"
    json_path = output_dir / "benchmark_summary.json"
    markdown_path = output_dir / "benchmark_report.md"

    write_csv(csv_path, rows)
    write_json(
        json_path,
        {
            "source_files": sources,
            "total_rows": len(rows),
            "rows": rows,
        },
    )
    markdown_path.write_text(_markdown_table(rows), encoding="utf-8")
    return csv_path, json_path, markdown_path


def main() -> None:
    csv_path, json_path, markdown_path = build_report()
    print(f"Benchmark table written to {csv_path}")
    print(f"Benchmark summary written to {json_path}")
    print(f"Benchmark markdown written to {markdown_path}")


if __name__ == "__main__":
    main()
