"""Warehouse schema, SQL publication and reconciliation boundaries."""

from importlib.resources import files

import duckdb


def initialize(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
      CREATE TABLE IF NOT EXISTS manifests (
        source_month VARCHAR PRIMARY KEY, sha VARCHAR, raw_path VARCHAR,
        rows_raw BIGINT, rows_valid BIGINT, rows_rejected BIGINT,
        published_at TIMESTAMPTZ, processing_key VARCHAR);
      CREATE TABLE IF NOT EXISTS runs (
        run_id VARCHAR PRIMARY KEY, source_month VARCHAR, status VARCHAR,
        details VARCHAR, created_at TIMESTAMPTZ DEFAULT current_timestamp);
    """)
    # Additive migration from the first portfolio prototype.
    con.execute("ALTER TABLE manifests ADD COLUMN IF NOT EXISTS processing_key VARCHAR")


def publish(con: duckdb.DuckDBPyConnection, month: str) -> None:
    sql = files("taxi_lakehouse").joinpath("sql/publish.sql").read_text(encoding="utf-8")
    # Each statement is fixed repository SQL; only the month is parameterized.
    for statement in sql.split(";"):
        if statement.strip():
            if "$month" in statement:
                con.execute(statement, {"month": month})
            else:
                con.execute(statement)


def reconcile(con: duckdb.DuckDBPyConnection, month: str, raw: int, rejected: int) -> int:
    valid, amount = con.execute(
        "SELECT count(*), coalesce(sum(total_amount),0) FROM silver WHERE source_month=?",
        [month],
    ).fetchone()
    count_gold, amount_gold = con.execute(
        "SELECT trips,gross_amount FROM gold_monthly WHERE source_month=?", [month]
    ).fetchone()
    if valid + rejected != raw or count_gold != valid or amount_gold != amount:
        raise ValueError("Reconciliation failed: raw/Silver/quarantine/Gold disagree")
    return valid
