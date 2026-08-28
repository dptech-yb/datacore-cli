"""DataCore 统一命令引擎。

终端 CLI 与 DataCore Agent 都调用本类；本类只认识稳定 HTTP API，不依赖 Agent、
FastAPI 或前端页面。删除 Agent 不影响命令引擎和 Skills。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .errors import DataCoreCliError
from .target import ConductivityTarget, parse_target
from .transport import DataCoreTransport, save_binary

API = "/api/tools/chemical-space"
TERMINAL_OK = {"completed", "complete", "succeeded", "success", "done", "ready"}
TERMINAL_BAD = {"failed", "error", "cancelled", "canceled", "timeout", "partial_failed"}


def _op_id(value: dict[str, Any]) -> str:
    return str(
        value.get("operationId")
        or value.get("operation_id")
        or (value.get("submit") or {}).get("operation_id")
        or ""
    )


def _phase(value: dict[str, Any]) -> str:
    return str(value.get("phase") or value.get("status") or "").strip().lower()


class CommandEngine:
    """电导 v1 的确定性命令编排，输出稳定 JSON envelope。"""

    def __init__(self, transport: DataCoreTransport) -> None:
        self.transport = transport

    def _result(
        self,
        command: str,
        summary: str,
        data: Any,
        *,
        artifacts: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "command": command,
            "summary": summary,
            "data": data,
            "artifacts": artifacts or [],
            "warnings": warnings or [],
        }

    def _require_confirmed(self, params: dict[str, Any], action: str) -> None:
        if not bool(params.get("confirmed") or params.get("yes")):
            raise DataCoreCliError(
                f"{action}会改变 DataCore 或提交云端任务，尚未确认",
                code="confirmation_required",
                action="检查目标与参数后使用 --yes；Agent 必须先取得用户明确同意。",
            )

    def resolve_round(
        self, raw_target: str
    ) -> tuple[ConductivityTarget, str, dict[str, Any] | None]:
        target = parse_target(raw_target)
        if target.round_id:
            return target, target.round_id, None
        detail = self.transport.get(f"{API}/chains/{target.chain_seq}")
        rounds = list(detail.get("rounds") or [])
        match = next(
            (row for row in rounds if int(row.get("ordinal") or 0) == int(target.ordinal or 0)),
            None,
        )
        if not match or not match.get("roundRef"):
            raise DataCoreCliError(
                f"探索链 {target.chain_seq} 中没有第 {target.ordinal} 轮",
                code="round_not_found",
            )
        return target, str(match["roundRef"]), detail

    def _wait(
        self,
        getter: Callable[[], dict[str, Any]],
        *,
        timeout: int,
        interval: float = 5.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(1, timeout)
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last = getter()
            phase = _phase(last)
            if phase in TERMINAL_OK:
                return last
            if phase in TERMINAL_BAD:
                user_error = last.get("user_error") or {}
                raise DataCoreCliError(
                    str(user_error.get("message") or f"云端任务结束于 {phase}"),
                    code=str(user_error.get("code") or "operation_failed"),
                    action=str(user_error.get("action") or "查看状态与失败折后重试。"),
                    retryable=bool(user_error.get("retryable", True)),
                    details=last,
                )
            time.sleep(max(0.5, interval))
        raise DataCoreCliError(
            "等待超时；任务可能仍在云端运行",
            code="watch_timeout",
            action="稍后运行 status 查看，不要重复提交。",
            retryable=True,
            details=last,
        )

    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(params or {})
        handlers = {
            "conductivity.status": self._status,
            "conductivity.recommend": self._recommend,
            "conductivity.export": self._export,
            "conductivity.validate": self._validate,
            "conductivity.upload": self._upload,
            "conductivity.train": self._train,
            "conductivity.retry-fold": self._retry_fold,
            "conductivity.compare": self._compare,
            "conductivity.decide": self._decide,
            "conductivity.next": self._next,
        }
        handler = handlers.get(command)
        if handler is None:
            raise DataCoreCliError(f"未知命令：{command}", code="unknown_command")
        return handler(params)

    def _status(self, params: dict[str, Any]) -> dict[str, Any]:
        target, round_id, chain = self.resolve_round(str(params.get("target") or ""))
        progress = self.transport.get(f"{API}/round/progress", params={"roundId": round_id})
        recommend = self.transport.get(f"{API}/recommend/status", params={"roundId": round_id})
        finetune = self.transport.get(f"{API}/finetune/status", params={"roundId": round_id})
        return self._result(
            "conductivity.status",
            f"已读取电导轮次 {round_id} 的实时状态",
            {
                "target": target.__dict__,
                "roundId": round_id,
                "progress": progress,
                "recommendation": recommend,
                "finetune": finetune,
                "chain": chain,
            },
        )

    def _recommend(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "计算推荐配方")
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        started = self.transport.post(
            f"{API}/recommend/infer",
            json_body={
                "roundId": round_id,
                "rerun": bool(params.get("rerun", False)),
                "useRemembered": True,
            },
        )
        status = None
        finalized = None
        if params.get("wait"):
            operation_id = _op_id(started)
            status = self._wait(
                lambda: self.transport.get(
                    f"{API}/recommend/status",
                    params={
                        "roundId": round_id,
                        **({"operationId": operation_id} if operation_id else {}),
                    },
                ),
                timeout=int(params.get("timeout") or 1800),
            )
            finalized = self.transport.post(
                f"{API}/recommend/finalize", json_body={"roundId": round_id}
            )
        return self._result(
            "conductivity.recommend",
            "推荐任务已完成" if finalized else "推荐任务已提交，可用 status 查看进度",
            {"roundId": round_id, "started": started, "status": status, "finalized": finalized},
        )

    def _export(self, params: dict[str, Any]) -> dict[str, Any]:
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        fmt = str(params.get("format") or "unilab").lower()
        output = str(params.get("output") or "").strip()
        mass = float(params.get("totalMassG") or 50)
        if fmt == "unilab":
            suffix, endpoint, query = (
                ".xls",
                "/unilab-task.xls",
                {"roundId": round_id, "totalMassG": mass},
            )
        elif fmt in {"xlsx", "weighing"}:
            suffix, endpoint, query = (
                ".xlsx",
                "/experiment-sheet.xlsx",
                {"roundId": round_id, "totalMassG": mass},
            )
        elif fmt in {"csv", "template", "demo"}:
            suffix, endpoint, query = (
                ".csv",
                "/ingest/template.csv",
                {"roundId": round_id, "demo": fmt == "demo"},
            )
        else:
            raise DataCoreCliError("format 仅支持 unilab/xlsx/csv/demo", code="invalid_format")
        if not output:
            output = f"datacore_{round_id}_{fmt}{suffix}"
        binary = self.transport.get(f"{API}{endpoint}", params=query, binary=True)
        artifact = save_binary(binary, output)
        return self._result(
            "conductivity.export",
            f"已导出 {fmt} 文件",
            {"roundId": round_id, "format": fmt},
            artifacts=[artifact],
        )

    def _validate(self, params: dict[str, Any]) -> dict[str, Any]:
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        path = Path(str(params.get("file") or "")).expanduser()
        if not path.is_file():
            raise DataCoreCliError(f"文件不存在：{path}", code="file_not_found")
        result = self.transport.post(
            f"{API}/ingest/validate",
            json_body={"roundId": round_id, "csv": path.read_text("utf-8-sig")},
        )
        return self._result(
            "conductivity.validate",
            "实测结果校验完成（未提交）",
            {"roundId": round_id, "file": str(path.resolve()), "validation": result},
        )

    def _upload(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "上传实测结果")
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        path = Path(str(params.get("file") or "")).expanduser()
        if not path.is_file():
            raise DataCoreCliError(f"文件不存在：{path}", code="file_not_found")
        with path.open("rb") as handle:
            result = self.transport.post(
                f"{API}/ingest/upload",
                files={"file": (path.name, handle, "text/csv")},
                data={
                    "roundId": round_id,
                    "merge": str(bool(params.get("merge", True))).lower(),
                    "validateOnly": "false",
                },
            )
        return self._result(
            "conductivity.upload",
            "实测结果已校验并上传",
            {"roundId": round_id, "file": str(path.resolve()), "result": result},
        )

    def _train(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "更新并训练电导模型")
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        calibration = None
        try:
            evaluated = self.transport.post(
                f"{API}/evaluate",
                json_body={"roundId": round_id, "includeEvaluation": False, "useRemembered": True},
            )
        except DataCoreCliError as exc:
            # evaluate 会在有实际配方偏差时先启动 predict-on-actual。不能越过这一步，
            # 否则评估输入会被永久写死；统一引擎负责等终态后再幂等重放 evaluate。
            if exc.code != "calibration_pending":
                raise
            detail = exc.details if isinstance(exc.details, dict) else {}
            operation_id = str(detail.get("operationId") or "")
            if not operation_id:
                raise
            calibration = self._wait(
                lambda: self.transport.get(
                    f"{API}/evaluate/calibration/status",
                    params={"roundId": round_id, "operationId": operation_id},
                ),
                timeout=int(params.get("timeout") or 7200),
            )
            evaluated = self.transport.post(
                f"{API}/evaluate",
                json_body={"roundId": round_id, "includeEvaluation": False, "useRemembered": True},
            )
        merged = self.transport.post(
            f"{API}/finetune/merge-training",
            json_body={"roundId": round_id, "force": bool(params.get("force", False))},
        )
        split = self.transport.post(
            f"{API}/finetune/split",
            json_body={"roundId": round_id, "force": bool(params.get("force", False))},
        )
        submitted = self.transport.post(
            f"{API}/finetune/submit",
            json_body={"roundId": round_id, "rerun": False, "useRemembered": True},
        )
        status = None
        if params.get("wait"):
            operation_id = _op_id(submitted)
            status = self._wait(
                lambda: self.transport.get(
                    f"{API}/finetune/status",
                    params={
                        "roundId": round_id,
                        **({"operationId": operation_id} if operation_id else {}),
                    },
                ),
                timeout=int(params.get("timeout") or 7200),
            )
        return self._result(
            "conductivity.train",
            "训练完成" if status else "五折训练已提交，可用 status 查看每折状态",
            {
                "roundId": round_id,
                "calibration": calibration,
                "evaluated": evaluated,
                "merged": merged,
                "split": split,
                "submitted": submitted,
                "status": status,
            },
        )

    def _retry_fold(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "重试未完成训练折")
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        fold = int(params.get("fold") or 0)
        if fold < 1:
            raise DataCoreCliError("fold 必须是正整数", code="invalid_fold")
        before = self.transport.get(f"{API}/finetune/status", params={"roundId": round_id})
        jobs = [
            item for item in list(before.get("jobs") or []) if int(item.get("fold") or -1) == fold
        ]
        if not jobs:
            raise DataCoreCliError(f"当前训练状态中没有第 {fold} 折", code="fold_not_found")
        if all(str(item.get("state") or "").lower() in TERMINAL_OK for item in jobs):
            raise DataCoreCliError(
                f"第 {fold} 折已经完成，不需要重试", code="fold_already_completed"
            )
        submitted = self.transport.post(
            f"{API}/finetune/submit",
            json_body={"roundId": round_id, "rerun": False, "useRemembered": True},
        )
        return self._result(
            "conductivity.retry-fold",
            f"已请求安全恢复第 {fold} 折；服务端只补交未完成任务，不重复创建已完成折",
            {"roundId": round_id, "requestedFold": fold, "before": before, "submitted": submitted},
        )

    def _compare(self, params: dict[str, Any]) -> dict[str, Any]:
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        result = self.transport.post(f"{API}/model-compare", json_body={"roundId": round_id})
        return self._result(
            "conductivity.compare",
            "已读取新旧模型五折 R² 对比",
            {"roundId": round_id, "comparison": result},
        )

    def _decide(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "记录是否继续下一轮")
        _target, round_id, _chain = self.resolve_round(str(params.get("target") or ""))
        decision = str(params.get("decision") or "").lower()
        if decision not in {"continue", "stop"}:
            raise DataCoreCliError("decision 必须是 continue 或 stop", code="invalid_decision")
        result = self.transport.post(
            f"{API}/stopping/decision",
            json_body={
                "roundId": round_id,
                "decision": decision,
                "reason": str(params.get("reason") or ""),
            },
        )
        return self._result(
            "conductivity.decide",
            f"已记录决定：{decision}",
            {"roundId": round_id, "result": result},
        )

    def _next(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_confirmed(params, "开启下一轮")
        target = parse_target(str(params.get("target") or ""))
        if target.chain_seq is None:
            raise DataCoreCliError(
                "开下一轮需要包含 boChain 的 DataCore 页面链接", code="chain_target_required"
            )
        result = self.transport.post(f"{API}/chains/{target.chain_seq}/rounds/auto")
        return self._result("conductivity.next", "下一轮已按上一轮冻结配置创建", result)


__all__ = ["CommandEngine"]
