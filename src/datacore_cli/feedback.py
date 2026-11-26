"""Feedback commands shared by the terminal and platform command adapter."""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

from .errors import DataCoreCliError
from .transport import DataCoreTransport, save_binary

API = "/api/feedback"
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _result(command: str, summary: str, data: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "summary": summary,
        "data": data,
        "artifacts": [],
        "warnings": [],
    }


def image_data_url(filename: str) -> str:
    """Read only a user-selected, already redacted image; never gather local files."""
    path = Path(filename).expanduser()
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_IMAGE_BYTES + 1)
    except OSError as exc:
        raise DataCoreCliError("无法读取截图文件", code="file_not_found") from exc
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise DataCoreCliError("截图必须非空且不超过 5 MiB", code="invalid_image")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise DataCoreCliError("截图仅支持 PNG、JPEG 或 WebP", code="invalid_image")
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"


class FeedbackEngine:
    def __init__(self, transport: DataCoreTransport) -> None:
        self.transport = transport

    @staticmethod
    def _payload(params: dict[str, Any]) -> dict[str, Any]:
        if isinstance(params.get("payload"), dict):
            return dict(params["payload"])
        filename = str(params.get("file") or "").strip()
        if not filename:
            raise DataCoreCliError("需要 --file JSON（- 表示标准输入）", code="file_not_found")
        try:
            raw = (
                sys.stdin.read()
                if filename == "-"
                else Path(filename).expanduser().read_text("utf-8")
            )
            value = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise DataCoreCliError("无法读取反馈 JSON", code="invalid_json") from exc
        if not isinstance(value, dict):
            raise DataCoreCliError("反馈 JSON 顶层必须是对象", code="invalid_json")
        return value

    @staticmethod
    def _confirmed(params: dict[str, Any]) -> None:
        if not (params.get("confirmed") or params.get("yes")):
            raise DataCoreCliError(
                "反馈写入尚未确认",
                code="confirmation_required",
                action="检查内容后使用 --yes；Agent 必须先取得用户确认。",
            )

    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        values = dict(params or {})
        try:
            return self._execute(command, values)
        except DataCoreCliError as exc:
            if exc.code == "feedback_disabled":
                exc.action = "当前平台尚未开放反馈中心，请联系平台管理员；无需重复提交。"
            elif (
                exc.status_code == 404
                and exc.code == "http_error"
                and command
                in {"feedback.config", "feedback.list", "feedback.submit", "feedback.clarify"}
            ):
                exc.code = "feedback_unavailable"
                exc.message = "当前平台版本尚未提供反馈中心"
                exc.action = "等待平台升级并开放反馈中心后重试；不要重复提交。"
            elif exc.status_code == 403:
                exc.action = (
                    "确认令牌具有 feedback:read / feedback:write 权限；"
                    "旧令牌不会自动扩权，请运行 datacore auth login 重新授权。"
                )
            raise

    def _execute(self, command: str, params: dict[str, Any]) -> dict[str, Any]:
        if command == "feedback.config":
            data = self.transport.get(f"{API}/config")
            if not data.get("enabled"):
                raise DataCoreCliError(
                    "反馈中心暂未开放", code="feedback_disabled", status_code=404
                )
            return _result(command, "已读取统一需求清单", data)
        if command == "feedback.list":
            query = {
                key: params[key]
                for key in ("view", "status", "q", "offset", "limit")
                if params.get(key) is not None
            }
            return _result(command, "已读取反馈列表", self.transport.get(API, params=query))
        if command == "feedback.submit":
            self._confirmed(params)
            payload = self._payload(params)
            context = payload.get("context") or {}
            if not isinstance(context, dict):
                raise DataCoreCliError("context 必须是对象", code="invalid_json")
            context = dict(context)
            for flag, key in (("page", "route"), ("tool", "tool_id"), ("project", "project_id")):
                if params.get(flag) is not None:
                    context[key] = params[flag]
            payload["context"] = context
            if params.get("image"):
                payload["screenshot"] = image_data_url(str(params["image"]))
            # The server owns the checklist. A 422 stays a machine-readable error;
            # incomplete records are saved only after an explicit caller opt-in.
            return _result(command, "反馈已提交", self.transport.post(API, json_body=payload))
        if command == "feedback.clarify":
            payload = self._payload(params)
            final = None
            finished = False
            for event, value in self.transport.stream(f"{API}/clarify", json_body=payload):
                if event == "error":
                    raise DataCoreCliError(
                        str(value.get("message") or "反馈澄清失败"),
                        code=str(value.get("code") or "feedback_clarify_failed"),
                    )
                if event == "result":
                    final = value
                if event == "done":
                    if value.get("ok") is not True:
                        raise DataCoreCliError("反馈澄清未完成", code="feedback_clarify_failed")
                    finished = True
                    break
            if not finished or not isinstance(final, dict):
                raise DataCoreCliError("反馈澄清未返回完整结果", code="invalid_response")
            return _result(command, "已完成一轮需求澄清", final)
        if command not in {
            "feedback.show",
            "feedback.comment",
            "feedback.accept",
            "feedback.reopen",
            "feedback.export",
        }:
            raise DataCoreCliError(f"未知命令：{command}", code="unknown_command")
        feedback_id = str(params["id"])
        if not re.fullmatch(r"[0-9a-fA-F]{32}", feedback_id):
            raise DataCoreCliError("需要平台返回的完整反馈编号", code="invalid_feedback_id")
        path = f"{API}/{feedback_id}"
        if command == "feedback.show":
            return _result(command, f"已读取反馈 {feedback_id}", self.transport.get(path))
        if command == "feedback.export":
            binary = self.transport.get(f"{path}/export", binary=True)
            result = _result(command, f"已导出反馈 {feedback_id}", {"id": feedback_id})
            result["artifacts"] = [save_binary(binary, str(params["output"]))]
            return result
        self._confirmed(params)
        action = command.partition(".")[2]
        payload = {"message": str(params.get("message") or "").strip()}
        if action == "comment" and not payload["message"]:
            raise DataCoreCliError("补充说明不能为空", code="invalid_comment")
        data = self.transport.post(f"{path}/{action}", json_body=payload)
        return _result(command, f"反馈 {feedback_id} 已执行 {action}", data)


def interactive_new(engine: FeedbackEngine, params: dict[str, Any]) -> dict[str, Any]:
    """Terminal-only clarification. Never prompt or confirm on a machine's behalf."""
    if params.get("as_json") or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise DataCoreCliError(
            "feedback new 需要交互终端",
            code="interactive_terminal_required",
            action="Agent 或脚本请使用 feedback submit --json --file feedback.json --yes。",
        )
    config = engine.execute("feedback.config")["data"]
    print("只发送你输入的文字和明确选择的截图。截图请先打码；不会读取其他本机文件。")
    message = str(params.get("message") or input("想改哪里、希望怎样改？ ")).strip()
    if not message:
        raise DataCoreCliError("反馈内容不能为空", code="invalid_feedback")
    payload: dict[str, Any] = {
        "message": message,
        "context": {},
        "answers": {},
        "conversation": [],
        "public": bool(params.get("public", False)),
        "allow_incomplete": bool(params.get("allow_incomplete", False)),
    }
    for flag, key in (("page", "route"), ("tool", "tool_id"), ("project", "project_id")):
        if params.get(flag) is not None:
            payload["context"][key] = params[flag]
    if params.get("image"):
        screenshot = image_data_url(str(params["image"]))
        if not config.get("vision_enabled", False):
            print("当前平台仅用文字澄清；截图作为反馈附件存档，AI 不会读取图片。")
        if input("将所选截图发送给平台？[y/N] ").strip().lower() not in {"y", "yes"}:
            return _result("feedback.new", "已取消，未提交反馈", {"cancelled": True})
        payload["screenshot"] = screenshot
    current = message
    turns = min(12, max(1, int(config.get("max_clarify_turns") or 6)))
    if config.get("clarify_enabled", True):
        for _ in range(turns):
            previous = list(payload["conversation"])
            # Keep every user's words even if this round's provider disconnects.
            payload["conversation"].append({"role": "user", "content": current})
            try:
                result = engine.execute(
                    "feedback.clarify",
                    {
                        "payload": {
                            "message": current,
                            "conversation": previous,
                            "context": payload["context"],
                            "answers": payload["answers"],
                            **(
                                {"screenshot": payload["screenshot"]}
                                if payload.get("screenshot")
                                else {}
                            ),
                        }
                    },
                )["data"]
            except DataCoreCliError as exc:
                if (
                    exc.code in {"feedback_disabled", "authentication_required"}
                    or exc.status_code == 403
                ):
                    raise
                print(f"澄清助手暂不可用（{exc.code}），继续按需求清单填写。")
                break
            response = str(result.get("message") or "")
            print(response)
            for question in result.get("questions") or []:
                print(f"- {question['question']}")
            payload["conversation"].append({"role": "assistant", "content": response})
            payload["answers"].update(result.get("answers") or {})
            for key in ("summary", "plan"):
                if result.get(key):
                    payload[key] = result[key]
            if result.get("ready") or _ == turns - 1:
                break
            current = input("补充说明（/submit 进入确认，/cancel 取消）： ").strip()
            if current == "/cancel":
                return _result("feedback.new", "已取消，未提交反馈", {"cancelled": True})
            if not current or current == "/submit":
                break
    for question in config.get("questions") or []:
        key = question["id"]
        if question.get("required") and not str(payload["answers"].get(key) or "").strip():
            payload["answers"][key] = input(f"{question['question']}（可留空）： ").strip()
    print("请确认以下内容：")
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "screenshot"},
            ensure_ascii=False,
            indent=2,
        )
    )
    print("可见范围：" + ("公开摘要和截图；对话不公开" if payload["public"] else "仅自己和超管"))
    if input("确认提交？[y/N] ").strip().lower() not in {"y", "yes"}:
        return _result("feedback.new", "已取消，未提交反馈", {"cancelled": True})
    return engine.execute("feedback.submit", {"payload": payload, "confirmed": True})
