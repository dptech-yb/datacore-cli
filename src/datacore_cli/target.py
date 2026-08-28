from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

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
    try:
        chain_seq = int((query.get("boChain") or [""])[0])
        ordinal = int((query.get("boTurn") or [""])[0])
    except ValueError as exc:
        raise DataCoreCliError("链接中的 boChain/boTurn 无效", code="invalid_target") from exc
    if not chain_seq or not ordinal:
        raise DataCoreCliError(
            "电导链接缺少 boChain 与 boTurn",
            code="invalid_target",
            action="在电导轮次页面复制完整链接。",
        )
    return ConductivityTarget(
        raw=raw,
        experiment_id=experiment_id,
        chain_seq=chain_seq,
        ordinal=ordinal,
    )


__all__ = ["ConductivityTarget", "parse_target"]
