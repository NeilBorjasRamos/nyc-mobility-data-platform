"""Command-line entry point with machine-readable results and nonzero failures."""

import argparse
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import duckdb
import requests

from .demo import create_demo
from .ingest import check_month
from .pipeline import export, run, verify_bronze


def months(start: str, end: str) -> Iterator[str]:
    check_month(start)
    check_month(end)
    if start > end:
        raise ValueError("start must be <= end")
    year, month = map(int, start.split("-"))
    while f"{year:04}-{month:02}" <= end:
        yield f"{year:04}-{month:02}"
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible monthly NYC TLC data platform")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data"),
        help="Data directory; specify before the subcommand",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    single = sub.add_parser("run", help="Acquire and publish one monthly snapshot")
    single.add_argument("--month", required=True)
    single.add_argument("--input", type=Path, help="Local source instead of HTTP")
    single.add_argument("--max-reject-ratio", type=float, default=0.10)
    single.add_argument("--force", action="store_true")
    backfill = sub.add_parser("backfill", help="Run an inclusive month range, stopping on failure")
    backfill.add_argument("--start", required=True)
    backfill.add_argument("--end", required=True)
    output = sub.add_parser("export", help="Atomically replace a Gold Parquet snapshot")
    output.add_argument("--output", type=Path)
    sub.add_parser("status", help="Print publication manifests as JSON")
    sub.add_parser("verify", help="Verify checksums of currently published sources")
    sub.add_parser("demo", help="Run 20 clearly synthetic records without network access")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if args.command == "run":
            result = run(args.root, args.month, args.input, args.max_reject_ratio, args.force)
        elif args.command == "backfill":
            for month in months(args.start, args.end):
                print(json.dumps(run(args.root, month)))
            return
        elif args.command == "export":
            output_path = args.output or args.root / "gold" / "daily_zone.parquet"
            export(args.root, output_path)
            result = {"status": "exported", "path": str(output_path)}
        elif args.command == "verify":
            if not verify_bronze(args.root):
                raise ValueError("No published sources or Bronze checksum mismatch")
            result = {"status": "verified"}
        elif args.command == "demo":
            path = args.root / "demo_input.parquet"
            create_demo(path)
            result = run(args.root, "2024-01", path)
            result["dataset"] = "synthetic"
        else:
            with duckdb.connect(str(args.root / "warehouse.duckdb"), read_only=True) as con:
                cursor = con.execute("SELECT * FROM manifests ORDER BY source_month")
                names = [column[0] for column in cursor.description]
                result = {
                    "publications": [
                        dict(zip(names, row, strict=True)) for row in cursor.fetchall()
                    ]
                }
        print(json.dumps(result, default=str))
    except (ValueError, OSError, requests.RequestException, duckdb.Error) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
