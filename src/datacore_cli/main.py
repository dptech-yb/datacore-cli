from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx

from .credentials import delete_token, load_token, save_token
from .engine import CommandEngine
from .errors import DataCoreCliError, exit_code_for_error
from .transport import DataCoreTransport

DEFAULT_BASE_URL = "https://datacore.dp.qifalab.cn"


def _configure_console() -> None:
    """Keep Chinese output readable in Windows shells with legacy code pages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _version() -> str:
    try:
        return importlib.metadata.version("datacore-cli")
    except importlib.metadata.PackageNotFoundError:
        from . import __version__

        return __version__


def _print(value: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, default=str))
        return
    print(value.get("summary") or "完成")
    for artifact in value.get("artifacts") or []:
        print(f"文件：{artifact.get('path')} ({artifact.get('size')} bytes)")
    if value.get("warnings"):
        for warning in value["warnings"]:
            print(f"警告：{warning}")
    if value.get("data") is not None:
        print(json.dumps(value["data"], ensure_ascii=False, indent=2, default=str))


def _skill_inventory() -> tuple[Path, list[str]]:
    source_root = Path(__file__).resolve().parent / "skills"
    names = sorted(item.name for item in source_root.iterdir() if (item / "SKILL.md").is_file())
    return source_root, names


def _install_skills(*, force: bool) -> dict[str, Any]:
    source_root, names = _skill_inventory()
    target_root = Path.home() / ".codex" / "skills"
    installed: list[str] = []
    skipped: list[str] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = target_root / name
        if target.exists() and not force:
            skipped.append(name)
            continue
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source_root / name, target)
        installed.append(name)
    return {
        "ok": True,
        "command": "skills.install",
        "summary": f"已安装 {len(installed)} 个 DataCore Skills",
        "data": {"installed": installed, "skipped": skipped, "path": str(target_root)},
        "artifacts": [],
        "warnings": ["已存在的 Skill 未覆盖；如需更新请使用 --force。"] if skipped else [],
    }


def _auth_login(
    base_url: str,
    *,
    as_json: bool,
    no_browser: bool,
    allow_file_credential: bool,
) -> int:
    body = {
        "clientName": "DataCore CLI",
        "deviceName": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
        "scopes": [
            "conductivity:read",
            "conductivity:export",
            "conductivity:write",
            "conductivity:compute",
        ],
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(f"{base_url.rstrip('/')}/api/cli-auth/device/start", json=body)
        response.raise_for_status()
        data = response.json()
        if not as_json:
            print(f"请在浏览器确认 DataCore 授权：{data['verificationUri']}")
            print(f"设备码：{data['userCode']}")
        if not no_browser:
            webbrowser.open(str(data["verificationUri"]))
        deadline = time.monotonic() + int(data.get("expiresIn") or 600)
        while time.monotonic() < deadline:
            status = client.get(
                f"{base_url.rstrip('/')}/api/cli-auth/device/status/{data['deviceCode']}"
            )
            status.raise_for_status()
            current = status.json()
            if current.get("status") == "authorized":
                try:
                    storage = save_token(
                        base_url,
                        str(data["pendingToken"]),
                        allow_file=allow_file_credential,
                    )
                except RuntimeError as exc:
                    raise DataCoreCliError(
                        str(exc),
                        code="credential_storage_unavailable",
                        action=(
                            "安装系统 Keyring 后重试；无桌面环境使用 DATACORE_TOKEN。"
                            "如确需本地 0600 文件，使用 --allow-file-credential。"
                        ),
                    ) from exc
                result = {
                    "ok": True,
                    "command": "auth.login",
                    "summary": "DataCore CLI 登录成功",
                    "data": {"baseUrl": base_url, "storage": storage},
                    "artifacts": [],
                    "warnings": []
                    if storage == "keychain"
                    else ["令牌已按你的明确选择保存到权限为 0600 的本地配置文件。"],
                }
                _print(result, as_json=as_json)
                return 0
            if current.get("status") in {"denied", "expired"}:
                raise DataCoreCliError(
                    f"设备授权{current.get('status')}",
                    code=f"device_{current.get('status')}",
                )
            time.sleep(max(1, int(data.get("interval") or 2)))
    raise DataCoreCliError("设备授权已超时，请重新运行 auth login", code="device_expired")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datacore", description="DataCore CLI")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--request-id", default="", help="为本次调用指定可追踪请求 ID")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP 请求超时秒数")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    sub = parser.add_subparsers(dest="group", required=True)

    setup = sub.add_parser("setup", help="安装 Skills 并登录 DataCore")
    setup.add_argument("--no-browser", action="store_true")
    setup.add_argument("--allow-file-credential", action="store_true")

    sub.add_parser("doctor", help="检查 CLI、Skills、网络和授权状态")

    update = sub.add_parser("update", help="升级 CLI 并同步 Skills")
    update.add_argument("--version", dest="target_version", default="")

    uninstall = sub.add_parser("uninstall", help="撤销授权并卸载 CLI 与 Skills")
    uninstall.add_argument("--yes", action="store_true")

    auth = sub.add_parser("auth", help="平台登录授权")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    login = auth_sub.add_parser("login", help="在浏览器中授权当前设备")
    login.add_argument("--no-browser", action="store_true")
    login.add_argument("--allow-file-credential", action="store_true")
    auth_sub.add_parser("logout", help="撤销当前设备授权")
    auth_sub.add_parser("status", help="查看当前登录身份与授权状态")

    skills = sub.add_parser("skills", help="安装或查看 DataCore Skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    install = skills_sub.add_parser("install", help="将内置 Skills 同步到本机")
    install.add_argument("--force", action="store_true")
    skills_sub.add_parser("list", help="列出 CLI 自带的 Skills")

    conductivity = sub.add_parser("conductivity", help="电导完整工作流")
    csub = conductivity.add_subparsers(dest="conductivity_command", required=True)
    conductivity_help = {
        "status": "查看轮次状态与下一步动作",
        "recommend": "提交本轮推荐配方计算",
        "export": "导出 UniLab、称量单或示例文件",
        "train": "提交五折训练并跟踪状态",
        "compare": "比较当前模型与推荐基线",
        "next": "确认并开启下一轮",
    }
    for name in ("status", "recommend", "export", "train", "compare", "next"):
        item = csub.add_parser(name, help=conductivity_help[name])
        item.add_argument("target")
        if name in {"recommend", "train", "next"}:
            item.add_argument("--yes", action="store_true")
        if name in {"recommend", "train"}:
            item.add_argument("--wait", action="store_true")
            item.add_argument("--timeout", type=int)
    export = csub.choices["export"]
    export.add_argument("--format", choices=["unilab", "xlsx", "csv", "demo"], default="unilab")
    export.add_argument("--output")
    export.add_argument("--total-mass-g", type=float, default=50.0)

    validate = csub.add_parser("validate", help="只读校验实测 CSV")
    validate.add_argument("target")
    validate.add_argument("file")
    upload = csub.add_parser("upload", help="校验并上传实测 CSV")
    upload.add_argument("target")
    upload.add_argument("file")
    upload.add_argument("--yes", action="store_true")
    upload.add_argument("--no-merge", action="store_true")
    retry = csub.add_parser("retry-fold", help="只重试一个未完成训练折")
    retry.add_argument("target")
    retry.add_argument("--fold", type=int, required=True)
    retry.add_argument("--yes", action="store_true")
    decide = csub.add_parser("decide", help="记录继续或停止的轮次结论")
    decide.add_argument("target")
    decide.add_argument("decision", choices=["continue", "stop"])
    decide.add_argument("--reason", default="")
    decide.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    args = _parser().parse_args(argv)
    base_url = args.base_url.rstrip("/")
    try:
        if args.group == "update":
            package = "datacore-cli"
            if args.target_version:
                package += f"=={args.target_version.lstrip('v')}"
            completed = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                check=False,
            )
            if completed.returncode != 0:
                raise DataCoreCliError(
                    "CLI 升级失败",
                    code="update_failed",
                    action="检查网络和 Python 环境后重试，或重新运行官方安装脚本。",
                )
            subprocess.run(
                [sys.executable, "-m", "datacore_cli", "skills", "install", "--force"],
                check=False,
            )
            _print(
                {
                    "ok": True,
                    "command": "update",
                    "summary": "DataCore CLI 与 Skills 已更新",
                    "data": {"package": package},
                    "artifacts": [],
                    "warnings": [],
                },
                as_json=args.as_json,
            )
            return 0

        if args.group == "uninstall":
            if not args.yes:
                raise DataCoreCliError(
                    "卸载会移除本机 CLI 授权与 DataCore Skills，尚未确认",
                    code="confirmation_required",
                    action="确认后使用 datacore uninstall --yes。",
                )
            delete_token(base_url)
            _source_root, names = _skill_inventory()
            for name in names:
                target = Path.home() / ".codex" / "skills" / name
                if target.exists():
                    shutil.rmtree(target)
            completed = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", "datacore-cli"],
                check=False,
            )
            return completed.returncode

        if args.group == "skills":
            _source_root, names = _skill_inventory()
            if args.skills_command == "list":
                result = {
                    "ok": True,
                    "command": "skills.list",
                    "summary": f"内置 {len(names)} 个 DataCore Skills",
                    "data": {"skills": names},
                    "artifacts": [],
                    "warnings": [],
                }
            else:
                result = _install_skills(force=args.force)
            _print(result, as_json=args.as_json)
            return 0

        if args.group == "setup":
            skills_result = _install_skills(force=True)
            token = load_token(base_url)
            if token:
                try:
                    DataCoreTransport(
                        base_url=base_url,
                        token=token,
                        timeout=args.timeout,
                        request_id=args.request_id,
                    ).get("/api/tools/chemical-space/config")
                    _print(
                        {
                            "ok": True,
                            "command": "setup",
                            "summary": "DataCore CLI、Skills 与平台授权均已就绪",
                            "data": skills_result["data"],
                            "artifacts": [],
                            "warnings": [],
                        },
                        as_json=args.as_json,
                    )
                    return 0
                except DataCoreCliError:
                    delete_token(base_url)
            return _auth_login(
                base_url,
                as_json=args.as_json,
                no_browser=args.no_browser,
                allow_file_credential=args.allow_file_credential,
            )

        if args.group == "doctor":
            _source_root, names = _skill_inventory()
            installed = [
                name
                for name in names
                if (Path.home() / ".codex" / "skills" / name / "SKILL.md").is_file()
            ]
            checks: dict[str, Any] = {
                "version": _version(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "skills": {"expected": names, "installed": installed},
                "credential": "present" if load_token(base_url) else "missing",
            }
            token = load_token(base_url)
            if token:
                try:
                    DataCoreTransport(
                        base_url=base_url,
                        token=token,
                        timeout=min(args.timeout, 20),
                        request_id=args.request_id,
                    ).get("/api/tools/chemical-space/config")
                    checks["authorization"] = "valid"
                except DataCoreCliError as exc:
                    checks["authorization"] = "invalid"
                    checks["authorizationError"] = exc.to_dict()
            else:
                checks["authorization"] = "not-configured"
            ready = len(installed) == len(names) and checks["authorization"] == "valid"
            _print(
                {
                    "ok": ready,
                    "command": "doctor",
                    "summary": "DataCore CLI 已就绪" if ready else "DataCore CLI 需要完成配置",
                    "data": checks,
                    "artifacts": [],
                    "warnings": [] if ready else ["运行 datacore setup 完成 Skills 与平台授权。"],
                },
                as_json=args.as_json,
            )
            return 0 if ready else 1

        if args.group == "auth" and args.auth_command == "login":
            return _auth_login(
                base_url,
                as_json=args.as_json,
                no_browser=args.no_browser,
                allow_file_credential=args.allow_file_credential,
            )
        token = load_token(base_url)
        if not token:
            raise DataCoreCliError(
                "尚未登录 DataCore CLI",
                code="authentication_required",
                action="运行 datacore auth login。",
            )
        transport = DataCoreTransport(
            base_url=base_url,
            token=token,
            timeout=args.timeout,
            request_id=args.request_id,
        )
        if args.group == "auth":
            if args.auth_command == "logout":
                try:
                    transport.delete("/api/cli-auth/session")
                finally:
                    delete_token(base_url)
                result = {
                    "ok": True,
                    "command": "auth.logout",
                    "summary": "已撤销当前 CLI 授权",
                    "data": {},
                    "artifacts": [],
                    "warnings": [],
                }
            else:
                # 不把“本地有 token”误报成“仍然登录”：由服务端同时验证撤销、过期与 scope。
                remote = transport.get("/api/tools/chemical-space/config")
                result = {
                    "ok": True,
                    "command": "auth.status",
                    "summary": "DataCore CLI 授权有效",
                    "data": {
                        "baseUrl": base_url,
                        "conductivityEnabled": bool(remote.get("enabled", True)),
                    },
                    "artifacts": [],
                    "warnings": [],
                }
            _print(result, as_json=args.as_json)
            return 0

        command = f"conductivity.{args.conductivity_command}"
        params = vars(args).copy()
        params["confirmed"] = bool(params.pop("yes", False))
        if "total_mass_g" in params:
            params["totalMassG"] = params.pop("total_mass_g")
        if "no_merge" in params:
            params["merge"] = not params.pop("no_merge")
        result = CommandEngine(transport).execute(command, params)
        _print(result, as_json=args.as_json)
        return 0
    except DataCoreCliError as exc:
        envelope = {
            "ok": False,
            "error": exc.to_dict(),
            "command": getattr(args, "conductivity_command", None)
            or getattr(args, "auth_command", None),
        }
        if args.as_json:
            print(json.dumps(envelope, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"错误：{exc.message}", file=sys.stderr)
            if exc.action:
                print(f"建议：{exc.action}", file=sys.stderr)
        return exit_code_for_error(exc)
    except httpx.HTTPError as exc:
        if args.as_json:
            print(
                json.dumps(
                    {"ok": False, "error": {"code": "auth_http_error", "message": str(exc)}},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"登录请求失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
