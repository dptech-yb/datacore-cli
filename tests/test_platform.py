from __future__ import annotations

import json

import pytest

from datacore_cli.errors import DataCoreCliError
from datacore_cli.platform import PlatformEngine


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs.get("params")))
        return {"path": path, "params": kwargs.get("params")}

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs.get("json_body")))
        return {"path": path, "body": kwargs.get("json_body")}

    def patch(self, path: str, **kwargs):
        self.calls.append(("PATCH", path, kwargs.get("json_body")))
        return {"path": path, "body": kwargs.get("json_body")}


def test_read_command_uses_stable_platform_endpoint() -> None:
    out = PlatformEngine(FakeTransport()).execute("project.show", {"id": 7})
    assert out["command"] == "project.show"
    assert out["data"]["path"] == "/api/projects/7"


def test_json_write_requires_confirmation_before_network(tmp_path) -> None:
    payload = tmp_path / "project.json"
    payload.write_text(json.dumps({"name": "Demo"}), "utf-8")
    transport = FakeTransport()
    with pytest.raises(DataCoreCliError) as caught:
        PlatformEngine(transport).execute("project.create", {"file": str(payload)})
    assert caught.value.code == "confirmation_required"
    assert transport.calls == []


def test_confirmed_write_reads_reviewed_json(tmp_path) -> None:
    payload = tmp_path / "experiment.json"
    payload.write_text(json.dumps({"code": "EXP-1"}), "utf-8")
    out = PlatformEngine(FakeTransport()).execute(
        "experiment.create",
        {"task_id": 3, "file": str(payload), "confirmed": True},
    )
    assert out["data"]["path"] == "/api/projects/tasks/3/experiments"
    assert out["data"]["body"] == {"code": "EXP-1"}
