from unittest.mock import Mock

import pytest
import requests

from taxi_lakehouse.ingest import download


def response(status=200, chunks=(b"parquet-bytes",)):
    result = Mock()
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    result.iter_content.return_value = chunks
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=Mock(status_code=status))
    return result


def test_success_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr("taxi_lakehouse.ingest.requests.get", Mock(return_value=response()))
    out = tmp_path / "file.parquet"
    download("https://example.test/data", out)
    assert out.read_bytes() == b"parquet-bytes"
    assert not out.with_suffix(".part").exists()


@pytest.mark.parametrize("status", [404, 403])
def test_nontransient_status_is_not_retried(tmp_path, monkeypatch, status):
    get = Mock(return_value=response(status))
    monkeypatch.setattr("taxi_lakehouse.ingest.requests.get", get)
    with pytest.raises(requests.HTTPError):
        download("https://example.test/data", tmp_path / "file.parquet")
    assert get.call_count == 1


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_status_is_retried(tmp_path, monkeypatch, status):
    get = Mock(side_effect=[response(status), response()])
    sleep = Mock()
    monkeypatch.setattr("taxi_lakehouse.ingest.requests.get", get)
    monkeypatch.setattr("taxi_lakehouse.ingest.time.sleep", sleep)
    download("https://example.test/data", tmp_path / "file.parquet")
    assert get.call_count == 2
    sleep.assert_called_once_with(1)


def test_interruption_cleans_partial_and_preserves_previous(tmp_path, monkeypatch):
    out = tmp_path / "file.parquet"
    out.write_bytes(b"previous")
    bad = response()

    def interrupted(_size):
        yield b"partial"
        raise requests.ConnectionError("interrupted")

    bad.iter_content.side_effect = interrupted
    monkeypatch.setattr("taxi_lakehouse.ingest.requests.get", Mock(return_value=bad))
    monkeypatch.setattr("taxi_lakehouse.ingest.time.sleep", Mock())
    with pytest.raises(requests.ConnectionError):
        download("https://example.test/data", out)
    assert out.read_bytes() == b"previous"
    assert not out.with_suffix(".part").exists()
