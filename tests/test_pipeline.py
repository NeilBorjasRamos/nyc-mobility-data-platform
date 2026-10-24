from pathlib import Path

import duckdb
import pytest

from taxi_lakehouse.cli import months
from taxi_lakehouse.pipeline import run, verify_bronze


def fixture(path: Path, bad=0, amount=20, missing=False):
    with duckdb.connect() as con:
        projection = "" if missing else ", 1 AS payment_type"
        con.execute(f"""
            COPY (
              SELECT TIMESTAMP '2024-01-15 10:00:00' AS tpep_pickup_datetime,
                TIMESTAMP '2024-01-15 10:15:00' AS tpep_dropoff_datetime,
                1 AS PULocationID, 2 AS DOLocationID,
                CASE WHEN i < {bad} THEN -1 ELSE 2.5 END AS trip_distance,
                10 AS fare_amount, {amount} AS total_amount {projection}
              FROM range(10) t(i)
            ) TO '{path}' (FORMAT PARQUET)
        """)
    return path


def scalar(root, sql):
    with duckdb.connect(str(root / "warehouse.duckdb"), read_only=True) as con:
        return con.execute(sql).fetchone()[0]


def test_replay_preserves_identical_legitimate_rows(tmp_path):
    raw = fixture(tmp_path / "input.parquet")
    root = tmp_path / "lake"
    assert run(root, "2024-01", raw)["valid"] == 10
    assert run(root, "2024-01", raw)["status"] == "skipped"
    assert run(root, "2024-01", raw, force=True)["valid"] == 10
    assert scalar(root, "SELECT count(*) FROM silver") == 10
    assert scalar(root, "SELECT count(DISTINCT source_row) FROM silver") == 10
    assert scalar(root, "SELECT sum(trips) FROM gold_daily_zone") == 10
    assert verify_bronze(root)


def test_quarantine_and_reconciliation(tmp_path):
    root = tmp_path / "lake"
    result = run(root, "2024-01", fixture(tmp_path / "input.parquet", bad=1))
    assert result["rejected"] == 1
    assert scalar(root, "SELECT count(*) FROM quarantine") == 1
    assert scalar(root, "SELECT sum(gross_amount) FROM gold_daily_zone") == 180


def test_failed_quality_preserves_previous_snapshot(tmp_path):
    root = tmp_path / "lake"
    run(root, "2024-01", fixture(tmp_path / "good.parquet"))
    with pytest.raises(ValueError, match="Quality gate"):
        run(root, "2024-01", fixture(tmp_path / "bad.parquet", bad=5, amount=50))
    assert scalar(root, "SELECT sum(total_amount) FROM silver") == 200
    assert scalar(root, "SELECT count(*) FROM runs WHERE status='failed'") == 1


def test_missing_schema_fails_without_publication(tmp_path):
    root = tmp_path / "lake"
    with pytest.raises(ValueError, match="Schema contract"):
        run(root, "2024-01", fixture(tmp_path / "missing.parquet", missing=True))
    assert scalar(root, "SELECT count(*) FROM manifests") == 0


def test_writer_lock(tmp_path):
    root = tmp_path / "lake"
    root.mkdir()
    (root / "writer.lock").write_text("another process")
    with pytest.raises(FileExistsError):
        run(root, "2024-01", tmp_path / "none")
    assert (root / "writer.lock").exists()


def test_backfill_boundaries():
    assert list(months("2023-12", "2024-02")) == ["2023-12", "2024-01", "2024-02"]
    with pytest.raises(ValueError):
        list(months("2024-02", "2024-01"))


def test_configuration_change_reprocesses_same_source(tmp_path):
    from taxi_lakehouse.config import PipelineConfig

    root = tmp_path / "lake"
    raw = fixture(tmp_path / "input.parquet")
    run(root, "2024-01", raw)
    assert (
        run(root, "2024-01", raw, config=PipelineConfig(model_version="next"))["status"]
        == "published"
    )


def test_rollback_after_reconciliation_failure(tmp_path, monkeypatch):
    from taxi_lakehouse import warehouse

    root = tmp_path / "lake"
    run(root, "2024-01", fixture(tmp_path / "good.parquet"))

    def fail(*args):
        raise ValueError("Injected reconciliation failure")

    monkeypatch.setattr(warehouse, "reconcile", fail)
    with pytest.raises(ValueError, match="Injected"):
        run(root, "2024-01", fixture(tmp_path / "revised.parquet", amount=50))
    assert scalar(root, "SELECT sum(gross_amount) FROM gold_daily_zone") == 200
    assert scalar(root, "SELECT sum(total_amount) FROM silver") == 200
    assert scalar(root, "SELECT rows_valid FROM manifests") == 10


def test_failed_quality_has_persistent_diagnostics(tmp_path):
    import json

    root = tmp_path / "lake"
    with pytest.raises(ValueError, match="Quality gate"):
        run(root, "2024-01", fixture(tmp_path / "bad.parquet", bad=5))
    report = json.loads(next((root / "reports").glob("*.json")).read_text())
    assert report["rejection_reasons"] == {"invalid_distance": 5}
    assert report["status"] == "failed"


def test_multimonth_revision_preserves_other_month(tmp_path):
    root = tmp_path / "lake"
    jan = fixture(tmp_path / "jan.parquet")
    feb = tmp_path / "feb.parquet"
    with duckdb.connect() as con:
        con.execute(f"""
          COPY (SELECT * REPLACE(
            TIMESTAMP '2024-02-15 10:00:00' AS tpep_pickup_datetime,
            TIMESTAMP '2024-02-15 10:15:00' AS tpep_dropoff_datetime
          ) FROM read_parquet('{jan}')) TO '{feb}' (FORMAT PARQUET)
        """)
    run(root, "2024-01", jan)
    run(root, "2024-02", feb)
    run(root, "2024-01", fixture(tmp_path / "revised.parquet", amount=50))
    assert scalar(root, "SELECT gross_amount FROM gold_monthly WHERE source_month='2024-02'") == 200
    assert scalar(root, "SELECT gross_amount FROM gold_monthly WHERE source_month='2024-01'") == 500


def test_export_can_be_replaced_and_failure_keeps_old_file(tmp_path, monkeypatch):
    from taxi_lakehouse.pipeline import export

    root = tmp_path / "lake"
    run(root, "2024-01", fixture(tmp_path / "good.parquet"))
    out = tmp_path / "gold.parquet"
    export(root, out)
    before = out.read_bytes()
    export(root, out)
    assert out.exists()
    with pytest.raises(ValueError):
        export(root, tmp_path / "warehouse.duckdb")
    assert out.read_bytes() == before

    def fail_connect(*args, **kwargs):
        raise RuntimeError("Injected export failure")

    monkeypatch.setattr("taxi_lakehouse.pipeline.duckdb.connect", fail_connect)
    with pytest.raises(RuntimeError, match="Injected export"):
        export(root, out)
    assert out.read_bytes() == before
    assert not list(out.parent.glob(".gold.parquet.*.tmp"))


def test_corrupted_existing_bronze_is_detected(tmp_path):
    root = tmp_path / "lake"
    raw = fixture(tmp_path / "input.parquet")
    run(root, "2024-01", raw)
    bronze = next((root / "bronze").rglob("*.parquet"))
    bronze.write_bytes(b"corrupted")
    assert not verify_bronze(root)
    with pytest.raises(ValueError, match="integrity"):
        run(root, "2024-01", raw)


def test_all_rejected_fails_even_with_ratio_one(tmp_path):
    with pytest.raises(ValueError, match="Quality gate"):
        run(
            tmp_path / "lake",
            "2024-01",
            fixture(tmp_path / "bad.parquet", bad=10),
            max_reject_ratio=1,
        )


@pytest.mark.parametrize("month", ["2024-00", "2024-13", "24-01", "2024-1", "../2024-01"])
def test_invalid_month(month, tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, month)


def test_additive_source_schema_is_tolerated(tmp_path):
    raw = fixture(tmp_path / "input.parquet")
    extra = tmp_path / "extra.parquet"
    with duckdb.connect() as con:
        con.execute(
            f"COPY (SELECT *, 2.5 AS cbd_congestion_fee FROM read_parquet('{raw}')) "
            f"TO '{extra}' (FORMAT PARQUET)"
        )
    result = run(tmp_path / "lake", "2024-01", extra)
    assert "cbd_congestion_fee" in result["columns_observed"]
    assert result["valid"] == 10
