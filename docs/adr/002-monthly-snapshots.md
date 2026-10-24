# ADR 002 — Replace complete monthly snapshots
Status: accepted.

Context: TLC has no trip identifier in this projection and can revise published
files. Equal-valued rows do not prove duplicate business events.
Decision: immutable source files keyed by SHA-256; monthly replacement in one
warehouse transaction; replay identity includes model/policy fingerprint.
Consequence: replay does not duplicate records, legitimate identical rows survive,
and corrections are explainable. Incremental row-level CDC is not inferred.
Physical Parquet row numbers provide provenance only within exact source bytes.
