# Roadmap
Only the release behavior described in the README is implemented.

| Priority | Enhancement | Acceptance evidence |
|---|---|---|
| 1 | dim_zone with versioned lookup | Unique LocationID; no row multiplication; explicit unknown zones |
| 2 | Strict ID/domain checks and all reason codes | Fractional IDs rejected; multi-reason fixtures |
| 3 | Conditional HTTP and download bounds | ETag/304 tests, byte/time limits, Retry-After behavior |
| 4 | Schema migration framework | Upgrade and rollback fixtures for old database versions |
| 5 | Published-month discovery and scheduling | HTML/catalog fixture tests; missing-month recovery |
| 6 | Spark/Delta migration | Equivalent counts/amounts, benchmark and publication-manifest protocol |
| 7 | Azure deployment | IaC, managed identity, budget, teardown and measured costs |

Do not present roadmap items as deployed capabilities. A real multi-month
performance benchmark remains future work; current real evidence covers one month.
