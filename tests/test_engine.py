"""DataCore CLI 命令引擎的稳定输出、确认与恢复语义。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from datacore_cli.engine import CommandEngine
from datacore_cli.errors import DataCoreCliError


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs.get("params")))
        if path.endswith("/chains/18"):
            return {"rounds": [{"ordinal": 2, "roundRef": "round28002"}]}
        if path.endswith("/round/progress"):
            return {"phase": "training", "nextAction": "watch"}
        if path.endswith("/recommend/status"):
            return {"phase": "completed"}
        if path.endswith("/finetune/status"):
            return {"phase": "running", "jobs": [{"fold": 3, "state": "failed"}]}
        if path.endswith("/ingest/template.csv"):
            return {"content": b"a,b\n1,2\n", "contentType": "text/csv"}
        return {"phase": "completed"}

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs.get("json_body") or kwargs.get("data")))
        return {"phase": "submitted", "operationId": "op-1"}


TARGET = "https://datacore.dp.qifalab.cn/experiments/123?tab=big-device&flow=conductivity&boChain=18&boTurn=2"


def test_status_resolves_page_url_and_returns_all_states() -> None:
    out = CommandEngine(FakeTransport()).execute("conductivity.status", {"target": TARGET})
    assert out["ok"] is True
    assert out["data"]["roundId"] == "round28002"
    assert out["data"]["progress"]["phase"] == "training"
    assert out["data"]["finetune"]["jobs"][0]["fold"] == 3


def test_write_requires_explicit_confirmation_before_network_mutation() -> None:
    transport = FakeTransport()
    with pytest.raises(DataCoreCliError) as caught:
        CommandEngine(transport).execute("conductivity.recommend", {"target": TARGET})
    assert caught.value.code == "confirmation_required"
    assert transport.calls == []


def test_retry_fold_preserves_completed_work() -> None:
    transport = FakeTransport()
    out = CommandEngine(transport).execute(
        "conductivity.retry-fold", {"target": TARGET, "fold": 3, "confirmed": True}
    )
    assert out["data"]["requestedFold"] == 3
    submits = [call for call in transport.calls if call[0] == "POST"]
    assert submits[-1][2]["rerun"] is False


def test_export_writes_explicit_file() -> None:
    transport = FakeTransport()
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "demo.csv"
        out = CommandEngine(transport).execute(
            "conductivity.export",
            {"target": TARGET, "format": "demo", "output": str(output)},
        )
        assert output.read_text() == "a,b\n1,2\n"
        assert out["artifacts"][0]["path"] == str(output.resolve())
