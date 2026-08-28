"""CLI credentials.

Interactive users use the operating-system keychain.  Headless automation should
provide ``DATACORE_TOKEN``.  A local 0600 file is available only after explicit
opt-in so a missing keyring backend never silently weakens credential storage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

SERVICE = "datacore-cli"


def _key(base_url: str) -> str:
    return base_url.rstrip("/")


def _path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "datacore" / "credentials.json"


def _keyring():
    try:
        import keyring  # type: ignore

        return keyring
    except Exception:
        return None


def load_token(base_url: str) -> str:
    env = str(os.environ.get("DATACORE_TOKEN") or "").strip()
    if env:
        return env
    kr = _keyring()
    if kr is not None:
        try:
            value = kr.get_password(SERVICE, _key(base_url))
            if value:
                return str(value)
        except Exception:
            pass
    path = _path()
    try:
        data = json.loads(path.read_text("utf-8"))
        return str(data.get(_key(base_url)) or "")
    except (OSError, ValueError, TypeError):
        return ""


def save_token(base_url: str, token: str, *, allow_file: bool = False) -> str:
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(SERVICE, _key(base_url), token)
            return "keychain"
        except Exception:
            pass
    if not allow_file:
        raise RuntimeError(
            "系统钥匙串不可用；请配置系统 Keyring、使用 DATACORE_TOKEN，"
            "或明确传入 --allow-file-credential。"
        )
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    try:
        data = dict(json.loads(path.read_text("utf-8")))
    except (OSError, ValueError, TypeError):
        pass
    data[_key(base_url)] = token
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.chmod(path, 0o600)
    return "file-0600"


def delete_token(base_url: str) -> None:
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(SERVICE, _key(base_url))
        except Exception:
            pass
    path = _path()
    try:
        data = dict(json.loads(path.read_text("utf-8")))
        data.pop(_key(base_url), None)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        os.chmod(path, 0o600)
    except (OSError, ValueError, TypeError):
        pass


__all__ = ["delete_token", "load_token", "save_token"]
