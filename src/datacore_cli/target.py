from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from .errors import DataCoreCliError


@dataclass(frozen=True)
class ConductivityTarget:
    raw: str
    round_id: str = ""
    experiment_id: int | None = None
    chain_seq: int | None = None
    ordinal: int | None = None


def parse_target(value: str) -> ConductivityTarget:
    raw = str(value or "").strip()
    if not raw:
        raise DataCoreCliError("缺少电导目标", code="target_required")
    if "://" not in raw:
        if raw.lower().startswith("round"):
            return ConductivityTarget(raw=raw, round_id=raw)
        raise DataCoreCliError(
            "目标需使用 DataCore 电导页面链接或 round 编号",
            code="invalid_target",
        )
    parsed = urlparse(raw)
    query = parse_qs(parsed.query)
    segments = [item for item in parsed.path.split("/") if item]
    experiment_id = None
    if len(segments) >= 2 and segments[-2] == "experiments":
        try:
            experiment_id = int(segments[-1])
        except ValueError:
            pass
    chain_value = (query.get("boChain") or query.get("chain") or [""])[0].strip()
    ordinal_value = (query.get("boTurn") or query.get("turn") or [""])[0].strip()
    try:
        chain_seq = int(chain_value) if chain_value else None
        ordinal = int(ordinal_value) if ordinal_value else None
    except ValueError as exc:
        raise DataCoreCliError("页面链接中的探索记录或轮次无效", code="invalid_target") from exc
    if chain_seq is not None and chain_seq < 0:
        raise DataCoreCliError("页面链接中的探索记录无效", code="invalid_target")
    if ordinal is not None and ordinal <= 0:
        raise DataCoreCliError("页面链接中的轮次无效", code="invalid_target")
    if ordinal is not None and chain_seq is None:
        raise DataCoreCliError("页面链接只包含轮次、没有探索记录", code="invalid_target")
    if chain_seq is None and experiment_id is None:
        raise DataCoreCliError(
            "请提供 DataCore 电导实验页面链接或 round 编号",
            code="invalid_target",
        )
    return ConductivityTarget(
        raw=raw,
        experiment_id=experiment_id,
        chain_seq=chain_seq,
        ordinal=ordinal,
    )


def page_url_for_round(value: str, *, chain_seq: int, ordinal: int) -> str:
    """Build a shareable page URL for a resolved exploration and round."""

    parsed = urlparse(page_url_for_experiment(value))
    if not parsed.scheme:
        return value
    segments = [item for item in parsed.path.split("/") if item]
    embedded = len(segments) >= 2 and segments[-2] == "experiments"
    chain_key, turn_key = ("boChain", "boTurn") if embedded else ("chain", "turn")
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend([(chain_key, str(chain_seq)), (turn_key, str(ordinal))])
    return urlunparse(parsed._replace(query=urlencode(query)))


def page_url_for_experiment(value: str) -> str:
    """Remove internal round-selection parameters from an experiment page URL."""

    parsed = urlparse(value)
    if not parsed.scheme:
        return value
    selection_keys = {"boChain", "boTurn", "chain", "turn"}
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in selection_keys
    ]
    return urlunparse(parsed._replace(query=urlencode(query)))


__all__ = [
    "ConductivityTarget",
    "page_url_for_experiment",
    "page_url_for_round",
    "parse_target",
]
