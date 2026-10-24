# ADR 001 — Local SQL engine before distributed processing
Status: accepted.

Context: the first portfolio release needs reproducible multi-million-row batch
processing on a laptop, with meaningful failure tests and no paid infrastructure.
Decision: use DuckDB and Parquet; keep orchestration, transformation and storage
boundaries explicit. Use Python packaging rather than notebooks as the entry point.
Consequence: low operational overhead and simple transactional publication, but
single-writer execution and local capacity limits. Spark/Delta is a future
migration driven by measured capacity or a platform requirement, not claimed here.
