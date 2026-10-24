import json

import pytest

from taxi_lakehouse.cli import main


def test_offline_demo_and_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["taxi", "--root", str(tmp_path), "demo"])
    main()
    result = json.loads(capsys.readouterr().out)
    assert result["dataset"] == "synthetic"
    assert result["valid"] == 19
    monkeypatch.setattr("sys.argv", ["taxi", "--root", str(tmp_path), "status"])
    main()
    assert len(json.loads(capsys.readouterr().out)["publications"]) == 1


def test_cli_error_is_machine_readable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["taxi", "--root", str(tmp_path), "run", "--month", "bad"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
