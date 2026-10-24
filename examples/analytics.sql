-- Run against data/warehouse.duckdb.
SELECT * FROM gold_monthly ORDER BY source_month;
SELECT rejection_reason, count(*) AS rows
FROM quarantine GROUP BY 1 ORDER BY 2 DESC;
SELECT source_month, sum(gross_amount) / nullif(sum(trips),0) AS weighted_ticket
FROM gold_daily_zone GROUP BY 1;
SELECT pickup_zone_id, sum(trips) AS trips
FROM gold_daily_zone GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
SELECT source_month, status, created_at FROM runs ORDER BY created_at;
