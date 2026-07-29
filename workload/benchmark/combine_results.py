#!/usr/bin/env python3
"""Combine per-schema/per-size benchmark summaries."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: combine_results.py RESULTS_ROOT")

    root = Path(sys.argv[1])
    summary_files = sorted(
        path
        for path in root.rglob("summary.csv")
        if path.name == "summary.csv" and path.parent != root
    )
    if not summary_files:
        raise RuntimeError(f"No per-scenario summary.csv files found below {root}")

    rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None

    for path in summary_files:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise RuntimeError(f"Missing CSV header: {path}")
            if fieldnames is None:
                fieldnames = reader.fieldnames
            elif reader.fieldnames != fieldnames:
                raise RuntimeError(f"Summary header mismatch: {path}")
            rows.extend(reader)

    assert fieldnames is not None
    combined_csv = root / "combined_summary.csv"
    with combined_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row.get("status") != "PASS"]
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": [str(path.relative_to(root)) for path in summary_files],
        "summary_row_count": len(rows),
        "failed_summary_row_count": len(failed),
        "status": "PASS" if not failed else "FAIL",
        "rows": rows,
    }
    (root / "combined_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"SUMMARY_FILES={len(summary_files)}")
    print(f"SUMMARY_ROWS={len(rows)}")
    print(f"FAILED_SUMMARY_ROWS={len(failed)}")
    print(f"COMBINED_CSV={combined_csv}")
    print(f"COMBINED_RESULTS={payload['status']}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
