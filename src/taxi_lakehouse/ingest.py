"""Immutable content-addressed Bronze, streaming HTTP and bounded retries."""

import hashlib
import os
import re
import time
import uuid
from pathlib import Path

import requests

BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def check_month(value: str) -> str:
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", value):
        raise ValueError("Mes requerido: YYYY-MM, entre 2000 y 2099")
    return value


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    """No credentials; fail fast on 4xx except 429; retry transient failures."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        part = destination.with_suffix(".part")
        try:
            with requests.get(
                url, stream=True, timeout=(10, 120), headers={"User-Agent": "taxi-portfolio/0.1"}
            ) as response:
                response.raise_for_status()
                with part.open("wb") as out:
                    for chunk in response.iter_content(1024 * 1024):
                        out.write(chunk)
                    out.flush()
                    os.fsync(out.fileno())
            part.replace(destination)
            return
        except requests.RequestException as exc:
            part.unlink(missing_ok=True)
            status = getattr(exc.response, "status_code", None)
            if status is not None and status < 500 and status != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(2**attempt)


def acquire(root: Path, month: str, local: Path | None = None) -> tuple[Path, str]:
    check_month(month)
    folder = root / "bronze" / f"source_month={month}"
    folder.mkdir(parents=True, exist_ok=True)
    temp = folder / f"{uuid.uuid4()}.parquet"
    try:
        if local is None:
            download(f"{BASE}/yellow_tripdata_{month}.parquet", temp)
        else:
            import shutil

            shutil.copyfile(local, temp)
        sha = checksum(temp)
        target = folder / f"{sha}.parquet"
        if target.exists():
            if checksum(target) != sha:
                raise ValueError(
                    "Bronze integrity mismatch: existing content-addressed file is corrupted"
                )
            temp.unlink()
        else:
            temp.replace(target)
        return target, sha
    finally:
        temp.unlink(missing_ok=True)
