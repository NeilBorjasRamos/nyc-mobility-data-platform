# Data contract and metric definitions
Source: [TLC trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
Dataset: Yellow Taxi, one complete file per source month. Provider corrections
are treated as replacement snapshots. TLC does not guarantee source accuracy.

## Required source fields
| Field | Silver field/type | Rule |
|---|---|---|
| tpep_pickup_datetime | pickup_at / TIMESTAMP | Required, within requested source month |
| tpep_dropoff_datetime | dropoff_at / TIMESTAMP | Required, strictly after pickup |
| PULocationID | pickup_zone_id / INTEGER | Convertible, range 1–265 |
| DOLocationID | dropoff_zone_id / INTEGER | Convertible, range 1–265 |
| trip_distance | distance_miles / DOUBLE | Finite, >= 0 |
| fare_amount | fare_amount / DECIMAL(18,2) | Required, >= 0 |
| total_amount | total_amount / DECIMAL(18,2) | Required, >= 0 |
| payment_type | payment_type / INTEGER | Column required; null value allowed |

Additive columns are reported and ignored until modeled; missing required columns
fail the run. Conversions use try_cast, and invalid mandatory values are rejected.
The contract is semantic plus presence validation, not strict physical-type
validation. Integer casts follow DuckDB conversion rules; upstream fractional IDs
are not separately validated in this version. Source timestamps are retained as
local, timezone-naive values, not converted to UTC.

## Quality rules
First matching reason wins:
invalid_timestamp → outside_source_month → nonpositive_duration →
invalid_distance → invalid_amount → invalid_zone.
A nonempty batch with at least one accepted row and reject ratio <= threshold
passes. Default threshold 10% is a project policy, not TLC's recommendation.
An empty or entirely rejected batch always fails.

Negative amounts can represent legitimate corrections/refunds. Quarantining
them defines this operational analytics product; it does not prove source error.
Range checks are weaker than a lookup-table foreign key and may accept special
zones. There are no maximum distance/duration rules without a justified baseline.
Zero distance is retained. No statistical anomaly is called fraud.

## Gold metrics
| Metric | Definition | Interpretation |
|---|---|---|
| trips | count of accepted records | Observed accepted demand |
| gross_amount | sum(total_amount) | Recorded gross USD amount, not net profit |
| avg_ticket | avg(total_amount) | USD per accepted record |
| distance_miles | sum(trip_distance) | Total recorded miles |
| avg_duration_minutes | avg(dropoff - pickup, seconds)/60 | Mean elapsed minutes |

To aggregate ticket across groups: sum(gross_amount)/sum(trips). Do not average
group averages. DECIMAL controls money aggregation precision. Payment categories
and tips have source-specific limitations; no inference of missing cash tips.

## Invariants
raw_rows = valid_rows + rejected_rows.
For the affected month: Gold trips = Silver rows; Gold gross = Silver total_amount.
Replaying source SHA + processing fingerprint does not republish.
Failed quality or reconciliation does not replace the last published snapshot.
