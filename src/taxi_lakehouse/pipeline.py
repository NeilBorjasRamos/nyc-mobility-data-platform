"""Monthly orchestration: acquire, classify, gate and atomically publish."""

import json
import logging
import time
import uuid
from pathlib import Path

import duckdb

from . import warehouse
from .config import PipelineConfig
from .ingest import acquire, check_month, checksum
from .storage import write_json, writer_lock
from .transform import literal, stage

LOG = logging.getLogger(__name__)


def run(
    root: Path,
    month: str,
    local: Path | None = None,
    max_reject_ratio: float = 0.10,
    force: bool = False,
    config: PipelineConfig | None = None,
) -> dict:
    """Publish one complete source-month snapshot; no inferred trip deduplication."""
    check_month(month)
    config = config or PipelineConfig(max_reject_ratio=max_reject_ratio)
    root = root.resolve()
    with writer_lock(root), duckdb.connect(str(root / "warehouse.duckdb")) as con:
        con.execute("SET memory_limit = ?", [config.memory_limit])
        con.execute("SET threads = ?", [config.threads])
        warehouse.initialize(con)
        run_id = str(uuid.uuid4())
        started = time.perf_counter()
        report = {"run_id": run_id, "month": month, "config": config.as_dict()}
        try:
            raw, sha = acquire(root, month, local)
            report.update(sha=sha, raw_bytes=raw.stat().st_size)
            old = con.execute(
                "SELECT sha, processing_key FROM manifests WHERE source_month=?", [month]
            ).fetchone()
            if old == (sha, config.fingerprint) and not force:
                report.update(
                    status="skipped", elapsed_seconds=round(time.perf_counter() - started, 4)
                )
                _audit(con, report)
                LOG.info(json.dumps(report))
                return report
            columns = stage(con, raw, month, sha)
            total, rejects = con.execute("""
                SELECT count(*), count(*) FILTER (WHERE rejection_reason IS NOT NULL)
                FROM classified
            """).fetchone()
            reasons = dict(
                con.execute("""
                SELECT rejection_reason, count(*) FROM classified
                WHERE rejection_reason IS NOT NULL GROUP BY 1
            """).fetchall()
            )
            report.update(
                raw=total,
                valid=total - rejects,
                rejected=rejects,
                reject_ratio=rejects / total if total else None,
                rejection_reasons=reasons,
                columns_observed=sorted(columns),
            )
            if total == 0 or rejects == total or rejects / total > config.max_reject_ratio:
                raise ValueError(
                    f"Quality gate: raw={total}, rejected={rejects}; publication aborted"
                )
            con.execute("BEGIN")
            try:
                warehouse.publish(con, month)
                warehouse.reconcile(con, month, total, rejects)
                con.execute("DELETE FROM manifests WHERE source_month=?", [month])
                con.execute(
                    """
                    INSERT INTO manifests
                    (source_month,sha,raw_path,rows_raw,rows_valid,rows_rejected,published_at,processing_key)
                    VALUES (?,?,?,?,?,?,current_timestamp,?)
                """,
                    [
                        month,
                        sha,
                        str(raw.relative_to(root)),
                        total,
                        total - rejects,
                        rejects,
                        config.fingerprint,
                    ],
                )
                report.update(
                    status="published", elapsed_seconds=round(time.perf_counter() - started, 4)
                )
                _audit(con, report)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
        except Exception as exc:
            report.update(
                status="failed",
                error=str(exc),
                elapsed_seconds=round(time.perf_counter() - started, 4),
            )
            _audit(con, report)
            LOG.error(json.dumps(report))
            try:
                write_json(root / "reports" / f"{run_id}.json", report)
            except OSError:
                LOG.exception(
                    "Could not write supplemental failure report; audit remains in DuckDB"
                )
            raise
        # Supplemental report failure cannot change a committed publication into 'failed'.
        try:
            write_json(root / "reports" / f"{run_id}.json", report)
        except OSError:
            LOG.exception("Could not write supplemental report; publication is committed")
        LOG.info(json.dumps(report))
        return report


def _audit(con: duckdb.DuckDBPyConnection, report: dict) -> None:
    con.execute(
        "INSERT INTO runs(run_id,source_month,status,details) VALUES (?,?,?,?)",
        [report["run_id"], report["month"], report["status"], json.dumps(report)],
    )


def export(root: Path, output: Path) -> None:
    """Replace a BI snapshot atomically on the same filesystem."""
    root, output = root.resolve(), output.resolve()
    if output.suffix.lower() != ".parquet":
        raise ValueError("Export output must end in .parquet")
    if root / "bronze" in output.parents:
        raise ValueError("Export must not overwrite Bronze")
    with writer_lock(root):
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{uuid.uuid4()}.tmp")
        try:
            with duckdb.connect(str(root / "warehouse.duckdb"), read_only=True) as con:
                con.execute(
                    f"COPY gold_daily_zone TO {literal(temporary)} "
                    "(FORMAT PARQUET, COMPRESSION ZSTD)"
                )
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


def verify_bronze(root: Path) -> bool:
    """Verify all currently published sources; empty warehouse is not success."""
    root = root.resolve()
    with duckdb.connect(str(root / "warehouse.duckdb"), read_only=True) as con:
        rows = con.execute("SELECT raw_path,sha FROM manifests").fetchall()
    if not rows:
        return False
    return all((root / path).is_file() and checksum(root / path) == sha for path, sha in rows)
