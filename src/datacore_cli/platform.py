"""DataCore ordinary-user platform commands shared by terminal and AI Agents."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .errors import DataCoreCliError
from .transport import DataCoreTransport


class PlatformEngine:
    def __init__(self, transport: DataCoreTransport) -> None:
        self.transport = transport

    @staticmethod
    def _result(command: str, summary: str, data: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "command": command,
            "summary": summary,
            "data": data,
            "artifacts": [],
            "warnings": [],
        }

    @staticmethod
    def _confirmed(params: dict[str, Any], action: str) -> None:
        if not bool(params.get("confirmed") or params.get("yes")):
            raise DataCoreCliError(
                f"{action}会修改 DataCore，尚未确认",
                code="confirmation_required",
                action="检查目标和 JSON 后使用 --yes；Agent 必须先取得用户明确同意。",
            )

    @staticmethod
    def _payload(params: dict[str, Any]) -> dict[str, Any]:
        raw = str(params.get("file") or "").strip()
        if not raw:
            raise DataCoreCliError("写操作需要 --file JSON", code="file_not_found")
        path = Path(raw).expanduser()
        if not path.is_file():
            raise DataCoreCliError(f"文件不存在：{path}", code="file_not_found")
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataCoreCliError(f"无法读取 JSON：{exc}", code="invalid_json") from exc
        if not isinstance(value, dict):
            raise DataCoreCliError("JSON 顶层必须是对象", code="invalid_json")
        return value

    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        values = dict(params or {})
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "quota.status": self._quota,
            "capabilities.list": self._capabilities,
            "project.list": self._project_list,
            "project.show": self._project_show,
            "project.lineage": self._project_lineage,
            "project.create": self._project_create,
            "project.update": self._project_update,
            "experiment.list": self._experiment_list,
            "experiment.show": self._experiment_show,
            "experiment.lineage": self._experiment_lineage,
            "experiment.create": self._experiment_create,
            "experiment.update": self._experiment_update,
            "chemical.search": self._chemical_search,
            "chemical.show": self._chemical_show,
            "chemical.resolve": self._chemical_resolve,
            "booking.list": self._booking_list,
            "booking.show": self._booking_show,
            "booking.qualified": self._booking_qualified,
            "booking.create": self._booking_create,
            "booking.update": self._booking_update,
            "booking.cancel": self._booking_cancel,
            "reagent.inventory": self._reagent_inventory,
            "reagent.substances": self._reagent_substances,
            "reagent.workbench": self._reagent_workbench,
            "reagent.tasks": self._reagent_tasks,
            "reagent.task": self._reagent_task,
            "reagent.create-task": self._reagent_create_task,
            "reagent.assign": self._reagent_assign,
            "reagent.status": self._reagent_status,
            "reagent.confirm": self._reagent_confirm,
            "tool.history": self._tool_history,
        }
        handler = handlers.get(command)
        if handler is None:
            raise DataCoreCliError(f"未知命令：{command}", code="unknown_command")
        return handler(values)

    def _quota(self, _params: dict[str, Any]) -> dict[str, Any]:
        return self._result(
            "quota.status", "已读取今日自动化额度", self.transport.get("/api/cli-auth/quota")
        )

    def _capabilities(self, _params: dict[str, Any]) -> dict[str, Any]:
        return self._result(
            "capabilities.list",
            "已读取当前平台能力目录",
            self.transport.get("/api/cli-platform/capabilities"),
        )

    def _project_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        return self._result("project.list", "已列出可访问项目", self.transport.get("/api/projects"))

    def _project_show(self, params: dict[str, Any]) -> dict[str, Any]:
        pid = int(params["id"])
        return self._result(
            "project.show", f"已读取项目 {pid}", self.transport.get(f"/api/projects/{pid}")
        )

    def _project_lineage(self, params: dict[str, Any]) -> dict[str, Any]:
        pid = int(params["id"])
        return self._result(
            "project.lineage",
            f"已读取项目 {pid} 的数据血缘",
            self.transport.get(f"/api/projects/{pid}/lineage"),
        )

    def _write(
        self,
        command: str,
        summary: str,
        params: dict[str, Any],
        call: Callable[[dict[str, Any]], Any],
    ) -> dict[str, Any]:
        self._confirmed(params, summary)
        payload = self._payload(params)
        return self._result(command, summary, call(payload))

    def _project_create(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._write(
            "project.create",
            "创建项目",
            params,
            lambda body: self.transport.post("/api/projects", json_body=body),
        )

    def _project_update(self, params: dict[str, Any]) -> dict[str, Any]:
        pid = int(params["id"])
        return self._write(
            "project.update",
            f"更新项目 {pid}",
            params,
            lambda body: self.transport.patch(f"/api/projects/{pid}", json_body=body),
        )

    def _experiment_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        return self._result(
            "experiment.list",
            "已列出可访问实验",
            self.transport.get("/api/projects/experiments/navigable"),
        )

    def _experiment_show(self, params: dict[str, Any]) -> dict[str, Any]:
        exp_id = int(params["id"])
        return self._result(
            "experiment.show",
            f"已读取实验 {exp_id}",
            self.transport.get(f"/api/projects/experiments/{exp_id}"),
        )

    def _experiment_lineage(self, params: dict[str, Any]) -> dict[str, Any]:
        exp_id = int(params["id"])
        return self._result(
            "experiment.lineage",
            f"已读取实验 {exp_id} 的数据血缘",
            self.transport.get(f"/api/projects/experiments/{exp_id}/lineage"),
        )

    def _experiment_create(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = int(params["task_id"])
        return self._write(
            "experiment.create",
            f"在任务 {task_id} 下创建实验",
            params,
            lambda body: self.transport.post(
                f"/api/projects/tasks/{task_id}/experiments", json_body=body
            ),
        )

    def _experiment_update(self, params: dict[str, Any]) -> dict[str, Any]:
        exp_id = int(params["id"])
        return self._write(
            "experiment.update",
            f"更新实验 {exp_id}",
            params,
            lambda body: self.transport.patch(
                f"/api/projects/experiments/{exp_id}", json_body=body
            ),
        )

    def _chemical_search(self, params: dict[str, Any]) -> dict[str, Any]:
        query = {
            key: params[key]
            for key in ("q", "category", "limit", "offset")
            if params.get(key) not in (None, "")
        }
        return self._result(
            "chemical.search",
            "已搜索平台物质库",
            self.transport.get("/api/chemicals", params=query),
        )

    def _chemical_show(self, params: dict[str, Any]) -> dict[str, Any]:
        chem_id = int(params["id"])
        return self._result(
            "chemical.show",
            f"已读取物质 {chem_id}",
            self.transport.get(f"/api/chemicals/{chem_id}"),
        )

    def _chemical_resolve(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._result(
            "chemical.resolve",
            "已解析物质名称",
            self.transport.post(
                "/api/chemicals/resolve", json_body={"names": list(params.get("names") or [])}
            ),
        )

    def _booking_list(self, params: dict[str, Any]) -> dict[str, Any]:
        query = {
            key: value
            for key, value in params.items()
            if key in {"year", "month"} and value not in (None, "")
        }
        return self._result(
            "booking.list",
            "已读取工站预约",
            self.transport.get("/api/cli-platform/bookings", params=query),
        )

    def _booking_show(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = int(params["id"])
        return self._result(
            "booking.show",
            f"已读取预约 {task_id}",
            self.transport.get(f"/api/cli-platform/bookings/{task_id}"),
        )

    def _booking_qualified(self, params: dict[str, Any]) -> dict[str, Any]:
        query = {"station": params.get("station") or ""}
        if params.get("material_state"):
            query["material_state"] = params["material_state"]
        return self._result(
            "booking.qualified",
            "已读取可选执行人",
            self.transport.get("/api/cli-platform/bookings/qualified", params=query),
        )

    def _booking_create(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._write(
            "booking.create",
            "创建预约",
            params,
            lambda body: self.transport.post("/api/cli-platform/bookings", json_body=body),
        )

    def _booking_update(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = int(params["id"])
        return self._write(
            "booking.update",
            f"更新预约 {task_id}",
            params,
            lambda body: self.transport.put(
                f"/api/cli-platform/bookings/{task_id}", json_body=body
            ),
        )

    def _booking_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        self._confirmed(params, "取消预约")
        task_id = int(params["id"])
        return self._result(
            "booking.cancel",
            f"已取消预约 {task_id}",
            self.transport.delete(f"/api/cli-platform/bookings/{task_id}"),
        )

    def _reagent_read(
        self,
        command: str,
        resource: str,
        label: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        query = {
            key: value
            for key, value in params.items()
            if key in {"q", "status", "limit", "offset"} and value not in (None, "")
        }
        return self._result(
            command,
            f"已读取试剂{label}",
            self.transport.get(f"/api/cli-platform/reagents/{resource}", params=query),
        )

    def _reagent_inventory(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_read("reagent.inventory", "inventory", "库存", params)

    def _reagent_substances(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_read("reagent.substances", "substances", "物质", params)

    def _reagent_workbench(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_read("reagent.workbench", "workbench", "工作台", params)

    def _reagent_tasks(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_read("reagent.tasks", "tasks", "任务", params)

    def _reagent_task(self, params: dict[str, Any]) -> dict[str, Any]:
        recipe_id = str(params["id"])
        return self._result(
            "reagent.task",
            f"已读取试剂任务 {recipe_id}",
            self.transport.get(f"/api/cli-platform/reagents/tasks/{recipe_id}"),
        )

    def _reagent_create_task(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._write(
            "reagent.create-task",
            "创建试剂任务",
            params,
            lambda body: self.transport.post("/api/cli-platform/reagents/tasks", json_body=body),
        )

    def _reagent_action(self, command: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        recipe_id = str(params["id"])
        return self._write(
            command,
            f"更新试剂任务 {recipe_id}",
            params,
            lambda body: self.transport.patch(
                f"/api/cli-platform/reagents/tasks/{recipe_id}/{action}", json_body=body
            ),
        )

    def _reagent_assign(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_action("reagent.assign", "assign", params)

    def _reagent_status(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._reagent_action("reagent.status", "status", params)

    def _reagent_confirm(self, params: dict[str, Any]) -> dict[str, Any]:
        self._confirmed(params, "确认试剂任务")
        recipe_id = str(params["id"])
        return self._result(
            "reagent.confirm",
            f"已确认试剂任务 {recipe_id}",
            self.transport.post(
                f"/api/cli-platform/reagents/tasks/{recipe_id}/confirm", json_body={}
            ),
        )

    def _tool_history(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._result(
            "tool.history",
            "已读取本人工具运行历史",
            self.transport.get(
                "/api/tool-runs/me", params={"limit": int(params.get("limit") or 50)}
            ),
        )


__all__ = ["PlatformEngine"]
