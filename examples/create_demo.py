"""Generate clearly synthetic data for an offline demonstration."""

from pathlib import Path

import duckdb

path = Path("demo.parquet")
with duckdb.connect() as con:
    con.execute("""
      COPY (
        SELECT TIMESTAMP '2024-01-15 10:00:00' AS tpep_pickup_datetime,
          TIMESTAMP '2024-01-15 10:15:00' AS tpep_dropoff_datetime,
          1 AS PULocationID, 2 AS DOLocationID,
          2.5 AS trip_distance, 10 AS fare_amount,
          CASE WHEN i=0 THEN -20 ELSE 20 END AS total_amount,
          1 AS payment_type FROM range(20) t(i)
      ) TO 'demo.parquet' (FORMAT PARQUET)
    """)
print(f"Created {path}: 20 synthetic rows; 1 negative amount.")
