# Validation evidence
Date: 24 October 2026. Local environment: Python 3.12.14, DuckDB 1.4.3.
This is functional evidence, not a cross-platform benchmark.

## Checks performed
- 28 offline tests passed.
- Statement coverage: 93% across the application package.
- Ruff lint and formatting checks passed.
- GitHub Actions are pinned to immutable commits verified against upstream tags.
- Source distribution and wheel built.
- Wheel installed in a separate virtual environment outside the source directory.
- Installed CLI demo published 20 synthetic rows: 19 accepted and 1 quarantined.
- Installed CLI verified published Bronze checksums.
- Current model processed the real January 2024 source.
- Real warehouse export and Bronze verification passed.

See tests/, pyproject.toml and .github/workflows/ci.yml for reproducible commands.
Coverage measures executed statements; it is not a completeness or security guarantee.

## Real-source integration
URL: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
Downloaded bytes: 49,961,641.
SHA-256: c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510

| Result | Observed |
|---|---:|
| Raw | 2,964,624 |
| Accepted | 2,926,173 |
| Quarantined | 38,451 |
| Gold rows | 6,947 |
| Silver total amount | USD 80,302,017.00 |
| Gold gross amount | USD 80,302,017.00 |

Rejection reasons: invalid_amount 37,563; nonpositive_duration 870;
outside_source_month 18. Only the first matching reason is assigned.
These are project-defined classifications, not official TLC error declarations.

Machine-readable evidence: real_run.json.
Figure: assets/january-2024-results.png.
Rebuild both with scripts/generate_evidence.py after loading the same month.

## What is not claimed
Docker, remote GitHub Actions, Python 3.11/3.13 and Windows/macOS execution have
not been validated in the authoring environment. CI is configured to test three
Python versions on Ubuntu. A real multi-month benchmark, cloud deployment,
Spark migration and hosted dashboard are not implemented or measured.

The replay and multi-month correction tests use controlled synthetic fixtures.
The real source integration covers one month. Dependency versions are locked,
not guaranteed free of vulnerabilities. No runtime datasets are committed.
