from __future__ import annotations

import json
from pathlib import Path

import pytest

from datacore_cli import credentials
from datacore_cli.errors import DataCoreCliError, exit_code_for_error
from datacore_cli.main import main


def test_file_credential_requires_explicit_opt_in(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(credentials, "_keyring", lambda: None)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(RuntimeError, match="--allow-file-credential"):
        credentials.save_token("https://example.test", "secret")

    storage = credentials.save_token("https://example.test", "secret", allow_file=True)
    assert storage == "file-0600"
    path = tmp_path / "datacore" / "credentials.json"
    assert json.loads(path.read_text("utf-8"))["https://example.test"] == "secret"
    assert path.stat().st_mode & 0o777 == 0o600


def test_stable_exit_codes() -> None:
    assert exit_code_for_error(DataCoreCliError("login", code="authentication_required")) == 10
    assert exit_code_for_error(DataCoreCliError("denied", status_code=403)) == 11
    assert exit_code_for_error(DataCoreCliError("rate", status_code=429)) == 14
    assert exit_code_for_error(DataCoreCliError("network", code="network_error")) == 20
    assert exit_code_for_error(DataCoreCliError("timeout", code="request_timeout")) == 21


def test_doctor_is_actionable_without_authorization(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("datacore_cli.main.load_token", lambda _base_url: "")
    exit_code = main(["--json", "doctor"])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["command"] == "doctor"
    assert output["data"]["authorization"] == "not-configured"
    assert output["warnings"]


def test_skills_install_is_idempotent(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["--json", "skills", "install"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert sorted(first["data"]["installed"]) == ["datacore", "datacore-conductivity"]

    assert main(["--json", "skills", "install"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert sorted(second["data"]["skipped"]) == ["datacore", "datacore-conductivity"]
