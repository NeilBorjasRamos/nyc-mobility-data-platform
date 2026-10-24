# ADR 003 — One transactional warehouse, separate consumer snapshots
Status: accepted.

Context: publishing Silver, rejected rows and aggregates independently risks
inconsistent counts when an execution fails.
Decision: replace all affected warehouse tables, manifest and success audit
inside one DuckDB transaction. Publish external Parquet through temporary file
and atomic rename after the warehouse commit, as an explicit export command.
Consequence: warehouse consumers see reconciled publications; snapshot consumers
may see an older export until export runs. A failed supplemental JSON report does
not change a successful publication to failed. Multi-table Delta publication
would need a separate version-manifest protocol in a future distributed design.
