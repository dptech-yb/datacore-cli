from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx

from .credentials import delete_token, load_token, save_token
from .engine import CommandEngine
from .errors import DataCoreCliError, exit_code_for_error
from .platform import PlatformEngine
from .skill_install import install_skills, skills_status, uninstall_skills
from .transport import DataCoreTransport

DEFAULT_BASE_URL = "https://datacore.dp.qifalab.cn"
RELEASE_REPOSITORY = "dptech-yb/datacore-cli"
STANDARD_SCOPES = [
    "platform:read",
    "projects:read",
    "projects:write",
    "experiments:read",
    "experiments:write",
    "catalog:read",
    "booking:read",
    "booking:write",
    "reagent:read",
    "reagent:write",
    "tools:read",
    "conductivity:read",
    "conductivity:export",
    "conductivity:write",
    "conductivity:compute",
]


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


def _install_skills(
    *, force: bool, requested_agents: list[str] | None = None, copy: bool = False
) -> dict[str, Any]:
    source_root, names = _skill_inventory()
    try:
        data = install_skills(
            source_root,
            names,
            package_version=_version(),
            force=force,
            requested_agents=requested_agents,
            copy=copy,
        )
    except ValueError as exc:
        raise DataCoreCliError(
            str(exc),
            code="invalid_agent",
            action="使用 datacore skills install --help 查看支持的 Agent。",
        ) from exc
    warnings = data.pop("warnings")
    return {
        "ok": True,
        "command": "skills.install",
        "summary": f"已同步 {len(names)} 个通用 DataCore Skills",
        "data": data,
        "artifacts": [],
        "warnings": [
            *warnings,
            *(["已存在的 Skill 未覆盖；如需更新请使用 --force。"] if data["skipped"] else []),
        ],
    }


def _upgrade_from_release(target_version: str) -> dict[str, str]:
    requested = target_version.strip().lstrip("v")
    if requested and not re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9._-]*)", requested):
        raise DataCoreCliError(
            f"版本号格式无效：{target_version}",
            code="invalid_version",
            action="使用类似 datacore update --version 0.4.0 的版本号。",
        )

    release_root = f"https://github.com/{RELEASE_REPOSITORY}/releases"
    if requested:
        tag = f"v{requested}"
        asset_root = f"{release_root}/download/{tag}"
    else:
        tag = ""
        asset_root = f"{release_root}/latest/download"

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=60.0,
            headers={"User-Agent": f"datacore-cli/{_version()}"},
        ) as client:
            if not requested:
                release = client.get(
                    f"https://api.github.com/repos/{RELEASE_REPOSITORY}/releases/latest"
                )
                release.raise_for_status()
                try:
                    latest_tag = release.json().get("tag_name")
                except (AttributeError, ValueError) as exc:
                    raise DataCoreCliError(
                        "无法识别最新 DataCore CLI 版本",
                        code="release_version_missing",
                        action="稍后重试，或使用 datacore update --version X.Y.Z。",
                    ) from exc
                if not isinstance(latest_tag, str) or not re.fullmatch(
                    r"v\d+\.\d+\.\d+(?:[A-Za-z0-9._-]*)", latest_tag
                ):
                    raise DataCoreCliError(
                        "无法识别最新 DataCore CLI 版本",
                        code="release_version_missing",
                        action="稍后重试，或使用 datacore update --version X.Y.Z。",
                    )
                tag = latest_tag
                requested = tag.removeprefix("v")
                asset_root = f"{release_root}/download/{tag}"

            checksums = client.get(f"{asset_root}/SHA256SUMS")
            checksums.raise_for_status()

            wheel_name = f"datacore_cli-{requested}-py3-none-any.whl"
            expected = ""
            for line in checksums.text.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[-1].lstrip("*") == wheel_name:
                    expected = parts[0].lower()
                    break
            if not re.fullmatch(r"[a-f0-9]{64}", expected):
                raise DataCoreCliError(
                    f"Release 校验清单中缺少 {wheel_name}",
                    code="release_checksum_missing",
                    action="不要跳过校验；请检查目标版本或稍后重试。",
                )

            wheel = client.get(f"{asset_root}/{wheel_name}")
            wheel.raise_for_status()
    except DataCoreCliError:
        raise
    except httpx.HTTPError as exc:
        raise DataCoreCliError(
            "下载 DataCore CLI Release 失败",
            code="update_download_failed",
            action="检查网络后重试，或重新运行官网的一键安装命令。",
        ) from exc

    actual = hashlib.sha256(wheel.content).hexdigest()
    if actual != expected:
        raise DataCoreCliError(
            "DataCore CLI Release 的 SHA256 校验失败",
            code="release_checksum_mismatch",
            action="已拒绝安装；请稍后重试并确认网络中间设备未替换下载内容。",
        )

    with tempfile.TemporaryDirectory(prefix="datacore-cli-update-") as temporary:
        wheel_path = Path(temporary) / wheel_name
        wheel_path.write_bytes(wheel.content)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                str(wheel_path),
            ],
            check=False,
        )
    if completed.returncode != 0:
        raise DataCoreCliError(
            "CLI 升级失败",
            code="update_failed",
            action="检查 Python 环境后重试，或重新运行官网的一键安装命令。",
        )
    return {"version": requested, "tag": tag, "asset": wheel_name}


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
        "scopes": STANDARD_SCOPES,
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


def _auth_login_with_install_token(
    base_url: str,
    *,
    as_json: bool,
    allow_file_credential: bool,
) -> int:
    """从标准输入消费短时安装 Token；正式令牌永不写入终端输出。"""

    if sys.stdin.isatty():
        raise DataCoreCliError(
            "--install-token-stdin 只从标准输入读取一次性安装 Token",
            code="install_token_stdin_required",
            action="让 Agent 通过标准输入传入 Token，不要把 Token 放进命令参数。",
        )
    install_token = sys.stdin.readline(4096).strip()
    if not install_token.startswith("dc_install_"):
        raise DataCoreCliError(
            "标准输入中的 Agent 安装 Token 格式不正确",
            code="invalid_install_token",
            action="在 DataCore /cli 页面重新生成一次性安装 Token。",
        )
    body = {
        "installToken": install_token,
        "deviceName": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/cli-auth/agent-install/exchange",
            json=body,
            headers={"Cache-Control": "no-store"},
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or {}
            except (ValueError, TypeError):
                detail = {}
            raise DataCoreCliError(
                str(detail.get("message") or "Agent 安装 Token 无效或已失效"),
                code=str(detail.get("code") or "invalid_install_token"),
                status_code=response.status_code,
                action="在 DataCore /cli 页面重新生成一次性安装 Token。",
            )
        formal_token = str(response.json().get("token") or "")
        if not formal_token.startswith("dc_cli_"):
            raise DataCoreCliError(
                "平台没有返回有效的 CLI 凭据",
                code="invalid_authorization_response",
            )
        try:
            storage = save_token(
                base_url,
                formal_token,
                allow_file=allow_file_credential,
            )
        except RuntimeError as exc:
            # 安全存储失败时立即撤销刚兑换的正式凭据，避免遗留无人管理的授权。
            try:
                client.delete(
                    f"{base_url.rstrip('/')}/api/cli-auth/session",
                    headers={"Authorization": f"Bearer {formal_token}"},
                )
            except httpx.HTTPError:
                pass
            raise DataCoreCliError(
                str(exc),
                code="credential_storage_unavailable",
                action=(
                    "配置系统 Keyring 后重新生成安装 Token；无桌面 Agent 可明确添加 "
                    "--allow-file-credential，使用权限为 0600 的本地凭据文件。"
                ),
            ) from exc
    result = {
        "ok": True,
        "command": "auth.login",
        "summary": "DataCore Agent 授权安装成功",
        "data": {"baseUrl": base_url, "storage": storage},
        "artifacts": [],
        "warnings": (
            [] if storage == "keychain" else ["凭据已按明确选择保存到权限为 0600 的本地配置文件。"]
        ),
    }
    _print(result, as_json=as_json)
    return 0


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
    setup.add_argument("--install-token-stdin", action="store_true")
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
    login.add_argument(
        "--install-token-stdin",
        action="store_true",
        help="从标准输入安全兑换一次性 Agent 安装 Token",
    )
    login.add_argument("--allow-file-credential", action="store_true")
    auth_sub.add_parser("logout", help="撤销当前设备授权")
    auth_sub.add_parser("status", help="查看当前登录身份与授权状态")

    skills = sub.add_parser("skills", help="安装或查看 DataCore Skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    install = skills_sub.add_parser("install", help="将内置 Skills 同步到通用 Agent 目录")
    install.add_argument("--force", action="store_true")
    install.add_argument(
        "--agent",
        action="append",
        default=[],
        metavar="NAME",
        help="为指定的非通用 Agent 添加适配目录；可重复，使用 * 表示全部",
    )
    install.add_argument(
        "--copy",
        action="store_true",
        help="复制到 Agent 目录而非创建符号链接",
    )
    skills_sub.add_parser("list", help="列出 CLI 自带的 Skills")
    read_skill = skills_sub.add_parser("read", help="读取一个内置 Skill 的完整说明")
    read_skill.add_argument("name", help="Skill 名称")
    remove_skills = skills_sub.add_parser("uninstall", help="移除 DataCore Skills")
    remove_skills.add_argument("--yes", action="store_true")

    sub.add_parser("quota", help="查看今日自动化额度")
    sub.add_parser("capabilities", help="查看平台开放能力目录")

    def add_id(parent: argparse._SubParsersAction, name: str, help_text: str):
        item = parent.add_parser(name, help=help_text)
        item.add_argument("id", type=int)
        return item

    def add_json_write(item: argparse.ArgumentParser) -> None:
        item.add_argument("--file", required=True, help="JSON 请求文件")
        item.add_argument("--yes", action="store_true", help="确认本次写入")

    project = sub.add_parser("project", help="研发项目")
    psub = project.add_subparsers(dest="project_command", required=True)
    psub.add_parser("list", help="列出有权访问的项目")
    add_id(psub, "show", "查看项目详情")
    add_id(psub, "lineage", "查看项目数据血缘")
    add_json_write(psub.add_parser("create", help="从 JSON 创建项目"))
    add_json_write(add_id(psub, "update", "从 JSON 更新项目"))

    experiment = sub.add_parser("experiment", help="实验记录")
    esub = experiment.add_subparsers(dest="experiment_command", required=True)
    esub.add_parser("list", help="列出有权访问的实验")
    add_id(esub, "show", "查看实验完整记录")
    add_id(esub, "lineage", "查看实验数据血缘")
    create_exp = esub.add_parser("create", help="在任务下从 JSON 创建实验")
    create_exp.add_argument("task_id", type=int)
    add_json_write(create_exp)
    add_json_write(add_id(esub, "update", "从 JSON 更新实验"))

    chemical = sub.add_parser("chemical", help="平台物质库")
    chsub = chemical.add_subparsers(dest="chemical_command", required=True)
    search = chsub.add_parser("search", help="搜索物质")
    search.add_argument("q", nargs="?", default="")
    search.add_argument("--category", default="")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--offset", type=int, default=0)
    add_id(chsub, "show", "查看物质详情")
    resolve = chsub.add_parser("resolve", help="批量解析物质名称")
    resolve.add_argument("names", nargs="+")

    booking = sub.add_parser("booking", help="工站预约")
    bsub = booking.add_subparsers(dest="booking_command", required=True)
    blist = bsub.add_parser("list", help="查看预约")
    blist.add_argument("--year", type=int)
    blist.add_argument("--month", type=int)
    add_id(bsub, "show", "查看预约详情")
    qualified = bsub.add_parser("qualified", help="查看可选执行人")
    qualified.add_argument("--station", default="")
    qualified.add_argument("--material-state", choices=["liquid", "solid"], default="")
    add_json_write(bsub.add_parser("create", help="从 JSON 创建预约"))
    add_json_write(add_id(bsub, "update", "从 JSON 更新预约"))
    cancel = add_id(bsub, "cancel", "取消预约")
    cancel.add_argument("--yes", action="store_true")

    reagent = sub.add_parser("reagent", help="试剂库存与任务")
    rsub = reagent.add_subparsers(dest="reagent_command", required=True)
    for name, label in (
        ("inventory", "查询库存"),
        ("substances", "查询试剂物质"),
        ("workbench", "查看工作台"),
        ("tasks", "查看任务"),
    ):
        item = rsub.add_parser(name, help=label)
        item.add_argument("--q", default="")
        item.add_argument("--status", default="")
        item.add_argument("--limit", type=int, default=50)
        item.add_argument("--offset", type=int, default=0)
    task = rsub.add_parser("task", help="查看任务详情")
    task.add_argument("id")
    add_json_write(rsub.add_parser("create-task", help="从 JSON 创建任务"))
    for name, label in (("assign", "指派任务"), ("status", "更新任务状态")):
        item = rsub.add_parser(name, help=label)
        item.add_argument("id")
        add_json_write(item)
    confirm = rsub.add_parser("confirm", help="确认任务")
    confirm.add_argument("id")
    confirm.add_argument("--yes", action="store_true")

    tool = sub.add_parser("tool", help="数据工具")
    tsub = tool.add_subparsers(dest="tool_command", required=True)
    history = tsub.add_parser("history", help="查看本人的工具运行历史")
    history.add_argument("--limit", type=int, default=50)

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
            release = _upgrade_from_release(args.target_version)
            skill_update = subprocess.run(
                [sys.executable, "-m", "datacore_cli", "skills", "install", "--force"],
                check=False,
            )
            if skill_update.returncode != 0:
                raise DataCoreCliError(
                    "CLI 已升级，但 Skills 同步失败",
                    code="skill_update_failed",
                    action="运行 datacore skills install --force；仍失败时运行 datacore doctor。",
                )
            _print(
                {
                    "ok": True,
                    "command": "update",
                    "summary": "DataCore CLI 与 Skills 已更新",
                    "data": release,
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
            uninstall_skills(names)
            completed = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", "datacore-cli"],
                check=False,
            )
            return completed.returncode

        if args.group == "skills":
            _source_root, names = _skill_inventory()
            if args.skills_command == "list":
                status = skills_status(names)
                result = {
                    "ok": True,
                    "command": "skills.list",
                    "summary": f"内置 {len(names)} 个 DataCore Skills",
                    "data": {"skills": names, "installation": status},
                    "artifacts": [],
                    "warnings": [],
                }
            elif args.skills_command == "read":
                if args.name not in names:
                    raise DataCoreCliError(
                        f"未知 Skill：{args.name}",
                        code="skill_not_found",
                        action=f"可选值：{', '.join(names)}。",
                    )
                content = (_source_root / args.name / "SKILL.md").read_text(encoding="utf-8")
                result = {
                    "ok": True,
                    "command": "skills.read",
                    "summary": f"已读取 {args.name}",
                    "data": {"name": args.name, "content": content},
                    "artifacts": [],
                    "warnings": [],
                }
            elif args.skills_command == "uninstall":
                if not args.yes:
                    raise DataCoreCliError(
                        "移除 DataCore Skills 尚未确认",
                        code="confirmation_required",
                        action="确认后使用 datacore skills uninstall --yes。",
                    )
                data = uninstall_skills(names)
                warnings = data.pop("warnings")
                result = {
                    "ok": True,
                    "command": "skills.uninstall",
                    "summary": "DataCore Skills 已移除",
                    "data": data,
                    "artifacts": [],
                    "warnings": warnings,
                }
            else:
                result = _install_skills(
                    force=args.force,
                    requested_agents=args.agent,
                    copy=args.copy,
                )
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
                    ).get("/api/cli-platform/capabilities")
                    _print(
                        {
                            "ok": True,
                            "command": "setup",
                            "summary": "DataCore CLI、Skills 与平台授权均已就绪",
                            "data": skills_result["data"],
                            "artifacts": [],
                            "warnings": skills_result["warnings"],
                        },
                        as_json=args.as_json,
                    )
                    return 0
                except DataCoreCliError:
                    delete_token(base_url)
            if args.install_token_stdin:
                return _auth_login_with_install_token(
                    base_url,
                    as_json=args.as_json,
                    allow_file_credential=args.allow_file_credential,
                )
            return _auth_login(
                base_url,
                as_json=args.as_json,
                no_browser=args.no_browser,
                allow_file_credential=args.allow_file_credential,
            )

        if args.group == "doctor":
            _source_root, names = _skill_inventory()
            skill_check = skills_status(names)
            installed = skill_check["installed"]
            checks: dict[str, Any] = {
                "version": _version(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "skills": skill_check,
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
                    ).get("/api/cli-platform/capabilities")
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
            if args.install_token_stdin:
                return _auth_login_with_install_token(
                    base_url,
                    as_json=args.as_json,
                    allow_file_credential=args.allow_file_credential,
                )
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
                remote = transport.get("/api/cli-auth/quota")
                result = {
                    "ok": True,
                    "command": "auth.status",
                    "summary": "DataCore CLI 授权有效",
                    "data": {
                        "baseUrl": base_url,
                        "quota": remote,
                    },
                    "artifacts": [],
                    "warnings": [],
                }
            _print(result, as_json=args.as_json)
            return 0

        params = vars(args).copy()
        params["confirmed"] = bool(params.pop("yes", False))
        if "total_mass_g" in params:
            params["totalMassG"] = params.pop("total_mass_g")
        if "no_merge" in params:
            params["merge"] = not params.pop("no_merge")
        if args.group == "conductivity":
            command = f"conductivity.{args.conductivity_command}"
            result = CommandEngine(transport).execute(command, params)
        elif args.group in {"quota", "capabilities"}:
            command = "quota.status" if args.group == "quota" else "capabilities.list"
            result = PlatformEngine(transport).execute(command, params)
        else:
            command = f"{args.group}.{getattr(args, f'{args.group}_command')}"
            result = PlatformEngine(transport).execute(command, params)
        _print(result, as_json=args.as_json)
        return 0
    except DataCoreCliError as exc:
        envelope = {
            "ok": False,
            "error": exc.to_dict(),
            "command": next(
                (
                    getattr(args, key)
                    for key in vars(args)
                    if key.endswith("_command") and getattr(args, key, None)
                ),
                getattr(args, "group", None),
            ),
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
