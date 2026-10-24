# Operations and recovery
## Commands
```bash
taxi --root data run --month 2024-01
taxi --root data status
taxi --root data verify
taxi --root data export
taxi --root data backfill --start 2024-01 --end 2024-03
```
stdout is JSON; operational logs go to stderr. Failures exit nonzero. Backfill is
sequential, stops at first failure and safely skips completed matching months on
restart. A source is reacquired even for replay to detect upstream revisions.
--force rebuilds a matching publication; a changed model version or threshold
already triggers reprocessing.

## Failure procedures
| Signal | Investigate | Recovery |
|---|---|---|
| 404 | Month/link availability on official portal | Correct month or wait for publication |
| 429/5xx/timeouts | Source availability and rate limits | Three bounded retries; rerun later |
| Schema contract | Missing fields and source dictionary | Review contract/migration before rerun |
| Quality gate | reports/RUN_ID.json and Bronze | Inspect reason counts; fix policy only with justification |
| Reconciliation failure | Silver/Gold semantics | Fix and test; previous snapshot remains published |
| writer.lock | PID/timestamp and live process | Remove only after verifying no writer is active |
| Integrity mismatch | Published SHA versus bytes | Restore a verified backup; investigate modification |
| Disk full | Warehouse, temp and Bronze versions | Free disk, verify snapshot, rerun |

A failed quality batch has a persisted aggregate diagnostic but no published
quarantine table for that revision. Original bytes remain in Bronze for replay.
Each report exposes only aggregate diagnostics and source schema, not row contents.

Do not change the threshold merely to make a run pass. Model semantic changes
must bump MODEL_VERSION. A version bump is not a physical database migration.
The current additive migration only introduces the processing_key manifest field.

## Backup and restore drill
Stop writers, copy the entire root (warehouse plus Bronze), restore into another
directory, run verify, status and aggregate queries. New relative paths support
relocation. Do not copy a live writable database as if that were a safe snapshot.
Old absolute-path manifests need reprocessing before a portable backup.

## Operational limits
No scheduler or alert transport is installed. Logs and runs are observable, not
a production monitoring service. There is no distributed locking or automatic
stale-lock deletion. A process crash can prevent audit completion.
The downloader has connection/read timeouts but no total transfer deadline or
maximum byte limit; only use the built-in public source or trusted local files.
Retention is manual; never prune raw versions without a recovery policy.
