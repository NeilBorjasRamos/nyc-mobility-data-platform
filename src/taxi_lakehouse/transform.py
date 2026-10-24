"""Explicit projection and deterministic business rules; no inferred trip key."""

from datetime import datetime

REQUIRED = {
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "trip_distance",
    "fare_amount",
    "total_amount",
    "payment_type",
}


def literal(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def stage(con, path, month, sha):
    columns = {
        row[0]
        for row in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({literal(path)}, hive_partitioning=false)"
        ).fetchall()
    }
    missing = REQUIRED - columns
    if missing:
        raise ValueError(f"Schema contract: faltan {sorted(missing)}")
    start = datetime.strptime(month, "%Y-%m")
    end = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE staging AS
        SELECT {literal(month)} AS source_month, {literal(sha)} AS source_sha,
          file_row_number + 1 AS source_row,
          try_cast(tpep_pickup_datetime AS TIMESTAMP) AS pickup_at,
          try_cast(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_at,
          try_cast(PULocationID AS INTEGER) AS pickup_zone_id,
          try_cast(DOLocationID AS INTEGER) AS dropoff_zone_id,
          try_cast(trip_distance AS DOUBLE) AS distance_miles,
          try_cast(fare_amount AS DECIMAL(18,2)) AS fare_amount,
          try_cast(total_amount AS DECIMAL(18,2)) AS total_amount,
          try_cast(payment_type AS INTEGER) AS payment_type
        FROM read_parquet({literal(path)}, hive_partitioning=false, file_row_number=true)
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE classified AS
        SELECT *, CASE
          WHEN pickup_at IS NULL OR dropoff_at IS NULL THEN 'invalid_timestamp'
          WHEN pickup_at < TIMESTAMP {literal(start)} OR pickup_at >= TIMESTAMP {literal(end)}
            THEN 'outside_source_month'
          WHEN dropoff_at <= pickup_at THEN 'nonpositive_duration'
          WHEN distance_miles IS NULL OR NOT isfinite(distance_miles) OR distance_miles < 0
            THEN 'invalid_distance'
          WHEN fare_amount IS NULL OR total_amount IS NULL
            OR fare_amount < 0 OR total_amount < 0 THEN 'invalid_amount'
          WHEN pickup_zone_id IS NULL OR dropoff_zone_id IS NULL
            OR pickup_zone_id NOT BETWEEN 1 AND 265 OR dropoff_zone_id NOT BETWEEN 1 AND 265
            THEN 'invalid_zone'
          ELSE NULL END AS rejection_reason
        FROM staging
    """)
    return columns
