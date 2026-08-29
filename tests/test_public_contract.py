from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from datacore_cli import CommandEngine, credentials
from datacore_cli.errors import DataCoreCliError, exit_code_for_error
from datacore_cli.main import _upgrade_from_release, main
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
    assert first["data"]["canonicalPath"] == str(tmp_path / ".agents" / "skills")
    assert (tmp_path / ".agents" / "skills" / "datacore" / "SKILL.md").is_file()

    assert main(["--json", "skills", "install"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert sorted(second["data"]["skipped"]) == ["datacore", "datacore-conductivity"]


def test_skills_install_migrates_codex_and_adapts_detected_claude(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    legacy = tmp_path / ".codex" / "skills" / "datacore"
    legacy.mkdir(parents=True)
    (legacy / "SKILL.md").write_text("custom legacy skill\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()

    assert main(["--json", "skills", "install", "--force"]) == 0
    result = json.loads(capsys.readouterr().out)
    canonical = tmp_path / ".agents" / "skills"

    assert (tmp_path / ".codex" / "skills" / "datacore").is_symlink()
    assert (tmp_path / ".claude" / "skills" / "datacore").is_symlink()
    assert (canonical / "datacore" / "SKILL.md").is_file()
    assert result["data"]["backups"]
    assert sorted(result["data"]["agents"]) == ["Claude Code", "Codex"]


def test_skills_uninstall_removes_managed_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".claude").mkdir()
    assert main(["--json", "skills", "install", "--force"]) == 0
    capsys.readouterr()

    assert main(["--json", "skills", "uninstall", "--yes"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["command"] == "skills.uninstall"
    assert not (tmp_path / ".agents" / "skills" / "datacore").exists()
    assert not (tmp_path / ".claude" / "skills" / "datacore").exists()


def test_skills_install_supports_explicit_agent_and_read(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert main(["--json", "skills", "install", "--agent", "gemini-cli", "--force"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["agents"] == ["Gemini CLI"]
    assert (tmp_path / ".gemini" / "skills" / "datacore").is_symlink()

    assert main(["--json", "skills", "read", "datacore"]) == 0
    skill = json.loads(capsys.readouterr().out)
    assert skill["data"]["name"] == "datacore"
    assert "DataCore" in skill["data"]["content"]


def test_skills_uninstall_ignores_tampered_adapter_path(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["--json", "skills", "install", "--agent", "codex", "--force"]) == 0
    capsys.readouterr()

    unrelated = tmp_path / "unrelated" / "datacore"
    unrelated.mkdir(parents=True)
    sentinel = unrelated / "keep.txt"
    sentinel.write_text("do not delete\n", encoding="utf-8")
    manifest_path = tmp_path / ".agents" / "datacore-skill-install.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["adapters"].append(
        {
            "agent": "codex",
            "displayName": "Codex",
            "path": str(unrelated),
            "method": "copy",
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert main(["--json", "skills", "uninstall", "--yes"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert sentinel.read_text(encoding="utf-8") == "do not delete\n"
    assert any("路径超出支持范围" in warning for warning in result["warnings"])


@pytest.mark.skipif(os.name == "nt" or shutil.which("sh") is None, reason="requires POSIX sh")
def test_unix_uninstaller_refuses_unmarked_directory(tmp_path: Path) -> None:
    install_root = tmp_path / "not-datacore"
    install_root.mkdir()
    sentinel = install_root / "keep.txt"
    sentinel.write_text("do not delete\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = home / "bin"
    bin_dir.mkdir()
    script = Path(__file__).resolve().parents[1] / "install.sh"
    environment = {
        **os.environ,
        "HOME": str(home),
        "DATACORE_INSTALL_ROOT": str(install_root),
        "DATACORE_BIN_DIR": str(bin_dir),
    }

    completed = subprocess.run(
        ["sh", str(script), "--uninstall"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "not a DataCore CLI installation" in completed.stderr
    assert sentinel.read_text(encoding="utf-8") == "do not delete\n"


def test_update_downloads_verified_github_release(monkeypatch) -> None:
    wheel_content = b"verified wheel"
    wheel_digest = __import__("hashlib").sha256(wheel_content).hexdigest()
    wheel_name = "datacore_cli-0.4.0-py3-none-any.whl"

    class Response:
        def __init__(self, url: str, *, content: bytes = b"", text: str = "") -> None:
            self.url = httpx.URL(url)
            self.content = content
            self.text = text

        def raise_for_status(self) -> None:
            return None

    class Client:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url: str):
            if url.endswith("SHA256SUMS"):
                return Response(
                    "https://github.com/dptech-yb/datacore-cli/releases/download/v0.4.0/SHA256SUMS",
                    text=f"{wheel_digest}  {wheel_name}\n",
                )
            assert url.endswith(f"/v0.4.0/{wheel_name}")
            return Response(url, content=wheel_content)

    calls: list[list[str]] = []
    monkeypatch.setattr("datacore_cli.main.httpx.Client", Client)
    monkeypatch.setattr(
        "datacore_cli.main.subprocess.run",
        lambda command, check: calls.append(command) or SimpleNamespace(returncode=0),
    )

    result = _upgrade_from_release("")

    assert result == {"version": "0.4.0", "tag": "v0.4.0", "asset": wheel_name}
    assert calls and calls[0][-2] == "--upgrade"


def test_update_rejects_release_with_wrong_checksum(monkeypatch) -> None:
    wheel_name = "datacore_cli-0.4.0-py3-none-any.whl"

    class Response:
        def __init__(self, url: str, *, content: bytes = b"", text: str = "") -> None:
            self.url = httpx.URL(url)
            self.content = content
            self.text = text

        def raise_for_status(self) -> None:
            return None

    class Client:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url: str):
            if url.endswith("SHA256SUMS"):
                return Response(url, text=f"{'0' * 64}  {wheel_name}\n")
            return Response(url, content=b"replaced wheel")

    monkeypatch.setattr("datacore_cli.main.httpx.Client", Client)

    with pytest.raises(DataCoreCliError, match="SHA256") as caught:
        _upgrade_from_release("0.4.0")
    assert caught.value.code == "release_checksum_mismatch"


def test_transport_reuses_one_request_id_for_a_command() -> None:
    transport = DataCoreTransport(base_url="https://example.test", token="token")
    first = transport._headers()["X-Request-ID"]
    second = transport._headers()["X-Request-ID"]
    assert first
    assert first == second


def test_agent_install_token_is_read_from_stdin_and_never_printed(monkeypatch, capsys) -> None:
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
            saved.update(base_url=base_url, token=token, allow_file=str(allow_file)) or "keychain"
        ),
    )
    assert main(["--json", "auth", "login", "--install-token-stdin"]) == 0
    output = capsys.readouterr().out
    assert install_token not in output
    assert formal_token not in output
    assert saved["token"] == formal_token
    assert json.loads(output)["data"]["storage"] == "keychain"


def test_failed_agent_credential_storage_revokes_new_authorization(monkeypatch, capsys) -> None:
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
    monkeypatch.setattr("datacore_cli.main.sys.stdin", io.StringIO("dc_install_one_time\n"))
    monkeypatch.setattr(
        "datacore_cli.main.save_token",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no keyring")),
    )
    assert main(["auth", "login", "--install-token-stdin"]) != 0
    output = capsys.readouterr()
    assert formal_token not in output.out + output.err
    assert revoked == [f"Bearer {formal_token}"]
