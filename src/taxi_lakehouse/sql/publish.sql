-- All statements run inside the caller's transaction.
CREATE TABLE IF NOT EXISTS silver AS
SELECT * EXCLUDE(rejection_reason) FROM classified WHERE false;

CREATE TABLE IF NOT EXISTS quarantine AS
SELECT * FROM classified WHERE false;

DELETE FROM silver WHERE source_month = $month;
DELETE FROM quarantine WHERE source_month = $month;

INSERT INTO silver
SELECT * EXCLUDE(rejection_reason) FROM classified WHERE rejection_reason IS NULL;

INSERT INTO quarantine
SELECT * FROM classified WHERE rejection_reason IS NOT NULL;

CREATE TABLE IF NOT EXISTS gold_daily_zone (
    source_month VARCHAR,
    service_date DATE,
    pickup_zone_id INTEGER,
    trips BIGINT,
    gross_amount DECIMAL(38,2),
    avg_ticket DOUBLE,
    distance_miles DOUBLE,
    avg_duration_minutes DOUBLE,
    PRIMARY KEY (source_month, service_date, pickup_zone_id)
);

-- A revised monthly snapshot affects only its own Gold partition.
DELETE FROM gold_daily_zone WHERE source_month = $month;

INSERT INTO gold_daily_zone
SELECT source_month, CAST(pickup_at AS DATE) AS service_date,
    pickup_zone_id, count(*) AS trips,
    sum(total_amount) AS gross_amount,
    avg(total_amount) AS avg_ticket,
    sum(distance_miles) AS distance_miles,
    avg(date_diff('second', pickup_at, dropoff_at)/60.0) AS avg_duration_minutes
FROM silver
WHERE source_month = $month
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW gold_monthly AS
SELECT source_month, sum(trips) AS trips, sum(gross_amount) AS gross_amount
FROM gold_daily_zone GROUP BY 1;
