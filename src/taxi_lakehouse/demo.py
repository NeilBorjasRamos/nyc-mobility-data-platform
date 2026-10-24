"""Deterministic synthetic records for an offline end-to-end demonstration."""

from pathlib import Path

import duckdb

from .transform import literal


def create_demo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect() as con:
        con.execute(f"""
          COPY (
            SELECT TIMESTAMP '2024-01-15 10:00:00' AS tpep_pickup_datetime,
              TIMESTAMP '2024-01-15 10:15:00' AS tpep_dropoff_datetime,
              1 AS PULocationID, 2 AS DOLocationID,
              2.5 AS trip_distance, 10 AS fare_amount,
              CASE WHEN i=0 THEN -20 ELSE 20 END AS total_amount,
              1 AS payment_type FROM range(20) t(i)
          ) TO {literal(path)} (FORMAT PARQUET)
        """)
