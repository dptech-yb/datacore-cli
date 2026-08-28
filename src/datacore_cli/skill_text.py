"""读取随 CLI 一起发布的 Skills，供内置 Agent 复用同一份操作约束。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def load_skill(name: str) -> str:
    safe_name = str(name or "").strip()
    if not safe_name or "/" in safe_name or "\\" in safe_name:
        return ""
    path = Path(__file__).resolve().parent / "skills" / safe_name / "SKILL.md"
    try:
        return path.read_text("utf-8").strip()
    except OSError:
        return ""


__all__ = ["load_skill"]
