"""DataCore CLI 命令引擎的稳定输出、确认与恢复语义。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from datacore_cli.engine import CommandEngine
from datacore_cli.errors import DataCoreCliError
from datacore_cli.target import parse_target


class FakeTransport:
    def __init__(self) -> None:
        self.base_url = "https://datacore.dp.qifalab.cn"
        self.calls: list[tuple[str, str, object]] = []
        self.chains = [
            {
                "chainSeq": 18,
                "title": "电导闭环 A",
                "currentOrdinal": 2,
                "status": "completed",
                "canResume": True,
                "canContinue": True,
            }
        ]

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs.get("params")))
        if path.endswith("/chains"):
            return {"chains": self.chains}
        if "/chains/" in path:
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
EXPERIMENT_URL = "https://datacore.dp.qifalab.cn/experiments/123?tab=big-device&flow=conductivity"


def test_status_resolves_page_url_and_returns_all_states() -> None:
    out = CommandEngine(FakeTransport()).execute("conductivity.status", {"target": TARGET})
    assert out["ok"] is True
    assert out["data"]["roundId"] == "round28002"
    assert out["data"]["progress"]["phase"] == "training"
    assert out["data"]["finetune"]["jobs"][0]["fold"] == 3


def test_status_discovers_single_chain_from_plain_experiment_url() -> None:
    transport = FakeTransport()
    out = CommandEngine(transport).execute("conductivity.status", {"target": EXPERIMENT_URL})

    assert out["data"]["target"]["experiment_id"] == 123
    assert out["data"]["target"]["chain_seq"] == 18
    assert out["data"]["target"]["ordinal"] == 2
    assert ("GET", "/api/tools/chemical-space/chains", {"experimentId": 123}) in transport.calls


def test_list_returns_human_readable_explorations_and_round_links() -> None:
    transport = FakeTransport()
    out = CommandEngine(transport).execute("conductivity.list", {"experiment": "123"})

    assert out["summary"] == "已列出实验中的 1 条电导探索记录"
    assert out["data"]["experimentId"] == 123
    exploration = out["data"]["explorations"][0]
    assert exploration["title"] == "电导闭环 A"
    assert exploration["rounds"][0]["label"] == "第 2 轮"
    assert exploration["rounds"][0]["pageUrl"].endswith("flow=conductivity&boChain=18&boTurn=2")
    assert [item["label"] for item in exploration["availableActions"]] == [
        "继续当前轮次",
        "新开一轮",
    ]


def test_status_returns_human_choices_when_experiment_has_multiple_chains() -> None:
    transport = FakeTransport()
    transport.chains.append(
        {
            "chainSeq": 19,
            "title": "低温电导探索",
            "currentOrdinal": 1,
            "status": "training",
        }
    )

    with pytest.raises(DataCoreCliError) as caught:
        CommandEngine(transport).execute("conductivity.status", {"target": EXPERIMENT_URL})

    assert caught.value.code == "target_selection_required"
    assert [item["title"] for item in caught.value.details["choices"]] == [
        "电导闭环 A",
        "低温电导探索",
    ]
    assert caught.value.details["choices"][1]["pageUrl"].endswith(
        "flow=conductivity&boChain=19&boTurn=1"
    )
    assert "chainSeq" not in caught.value.details["choices"][0]
    assert "ordinal" not in caught.value.details["choices"][0]
    assert [call[1] for call in transport.calls] == ["/api/tools/chemical-space/chains"]


def test_chain_zero_and_chain_only_url_are_valid_targets() -> None:
    parsed = parse_target("https://datacore.dp.qifalab.cn/experiments/123?boChain=0")
    assert parsed.chain_seq == 0
    assert parsed.ordinal is None

    out = CommandEngine(FakeTransport()).execute("conductivity.status", {"target": parsed.raw})
    assert out["data"]["target"]["chain_seq"] == 0
    assert out["data"]["target"]["ordinal"] == 2


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
