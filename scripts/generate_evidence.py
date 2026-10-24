"""Generate aggregate-only evidence and figures from an actual local publication.

Run from the repository root after processing January 2024:
    uv run --extra analysis python scripts/generate_evidence.py
No synthetic result is substituted if the warehouse is missing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

root = Path("data")
out = Path("docs/assets")
out.mkdir(parents=True, exist_ok=True)
with duckdb.connect(str(root / "warehouse.duckdb"), read_only=True) as con:
    raw, valid, rejected, sha = con.execute("""
        SELECT rows_raw, rows_valid, rows_rejected, sha
        FROM manifests WHERE source_month='2024-01'
    """).fetchone()
    dates, trips = zip(
        *con.execute("""
        SELECT service_date, sum(trips) FROM gold_daily_zone
        WHERE source_month='2024-01' GROUP BY 1 ORDER BY 1
    """).fetchall(),
        strict=True,
    )
    gold_rows, gold_trips, amount = con.execute("""
        SELECT count(*), sum(trips), sum(gross_amount)
        FROM gold_daily_zone WHERE source_month='2024-01'
    """).fetchone()
    silver_amount = con.execute("""
        SELECT sum(total_amount) FROM silver WHERE source_month='2024-01'
    """).fetchone()[0]
    reasons = dict(
        con.execute("""
        SELECT rejection_reason,count(*) FROM quarantine
        WHERE source_month='2024-01' GROUP BY 1
    """).fetchall()
    )
assert raw == valid + rejected
assert gold_trips == valid and amount == silver_amount
evidence = {
    "generated_at_utc": datetime.now(UTC).isoformat(),
    "dataset": "NYC TLC Yellow Taxi",
    "source_month": "2024-01",
    "source_url": "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet",
    "sha256": sha,
    "raw_rows": raw,
    "valid_rows": valid,
    "rejected_rows": rejected,
    "rejected_ratio": rejected / raw,
    "gold_rows": gold_rows,
    "gold_trip_count": int(gold_trips),
    "silver_total_amount_usd": str(silver_amount),
    "gold_gross_amount_usd": str(amount),
    "rejection_reasons": reasons,
    "reconciliation_passed": True,
}
Path("docs/real_run.json").write_text(json.dumps(evidence, indent=2) + "\n")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), gridspec_kw={"width_ratios": [2.2, 1]})
fig.patch.set_facecolor("#f7f9fc")
for axis in axes:
    axis.set_facecolor("#f7f9fc")
    axis.spines[["top", "right"]].set_visible(False)
axes[0].plot(dates, trips, color="#126782", linewidth=2.5)
axes[0].fill_between(dates, trips, alpha=0.1, color="#126782")
axes[0].set_title("Accepted trips per day · January 2024", loc="left", fontweight="bold", pad=16)
axes[0].set_ylabel("Accepted source records")
axes[0].tick_params(axis="x", rotation=30)
axes[0].grid(axis="y", alpha=0.18)
axes[1].bar(
    ["Accepted", "Quarantined"],
    [valid / raw * 100, rejected / raw * 100],
    color=["#126782", "#d27b34"],
    width=0.55,
)
axes[1].set_ylim(0, 112)
axes[1].set_ylabel("% of source records")
axes[1].set_title("Quality gate results", loc="left", fontweight="bold", pad=16)
for index, value in enumerate([valid / raw * 100, rejected / raw * 100]):
    axes[1].text(index, value + 3, f"{value:.2f}%", ha="center", fontweight="bold")
fig.text(
    0.06,
    0.015,
    "Source: NYC TLC · Project-defined quality rules · Aggregates from an actual pipeline run",
    color="#536171",
    fontsize=9,
)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out / "january-2024-results.png", dpi=160)
plt.close(fig)
print(json.dumps(evidence, indent=2))
