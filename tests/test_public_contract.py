from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from datacore_cli import CommandEngine, credentials
from datacore_cli.errors import DataCoreCliError, exit_code_for_error
from datacore_cli.main import main
from datacore_cli.transport import DataCoreTransport


def test_public_package_exports_command_engine() -> None:
    assert CommandEngine.__name__ == "CommandEngine"


def test_file_credential_requires_explicit_opt_in(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(credentials, "_keyring", lambda: None)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(RuntimeError, match="--allow-file-credential"):
        credentials.save_token("https://example.test", "secret")

    storage = credentials.save_token("https://example.test", "secret", allow_file=True)
    assert storage == "file-0600"
    path = tmp_path / "datacore" / "credentials.json"
    assert json.loads(path.read_text("utf-8"))["https://example.test"] == "secret"
    if os.name != "nt":
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


def test_transport_reuses_one_request_id_for_a_command() -> None:
    transport = DataCoreTransport(base_url="https://example.test", token="token")
    first = transport._headers()["X-Request-ID"]
    second = transport._headers()["X-Request-ID"]
    assert first
    assert first == second


def test_agent_install_token_is_read_from_stdin_and_never_printed(
    monkeypatch, capsys
) -> None:
    install_token = "dc_install_short_lived_secret"
    formal_token = "dc_cli_long_lived_secret"
    saved: dict[str, str] = {}

    class Response:
        status_code = 200

        def json(self):
            return {"token": formal_token, "authorization": {"id": "auth-1"}}

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, _url, *, json, headers):
            assert json["installToken"] == install_token
            assert headers["Cache-Control"] == "no-store"
            return Response()

        def delete(self, *_args, **_kwargs):
            raise AssertionError("successful storage must not revoke")

    monkeypatch.setattr("datacore_cli.main.httpx.Client", Client)
    monkeypatch.setattr("datacore_cli.main.sys.stdin", io.StringIO(f"{install_token}\n"))
    monkeypatch.setattr(
        "datacore_cli.main.save_token",
        lambda base_url, token, allow_file=False: (
            saved.update(base_url=base_url, token=token, allow_file=str(allow_file))
            or "keychain"
        ),
    )
    assert main(["--json", "auth", "login", "--install-token-stdin"]) == 0
    output = capsys.readouterr().out
    assert install_token not in output
    assert formal_token not in output
    assert saved["token"] == formal_token
    assert json.loads(output)["data"]["storage"] == "keychain"


def test_failed_agent_credential_storage_revokes_new_authorization(
    monkeypatch, capsys
) -> None:
    formal_token = "dc_cli_must_be_revoked"
    revoked: list[str] = []

    class Response:
        status_code = 200

        def json(self):
            return {"token": formal_token}

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            return Response()

        def delete(self, _url, *, headers):
            revoked.append(headers["Authorization"])
            return Response()

    monkeypatch.setattr("datacore_cli.main.httpx.Client", Client)
    monkeypatch.setattr(
        "datacore_cli.main.sys.stdin", io.StringIO("dc_install_one_time\n")
    )
    monkeypatch.setattr(
        "datacore_cli.main.save_token",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no keyring")),
    )
    assert main(["auth", "login", "--install-token-stdin"]) != 0
    output = capsys.readouterr()
    assert formal_token not in output.out + output.err
    assert revoked == [f"Bearer {formal_token}"]
