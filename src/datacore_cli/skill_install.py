from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_VERSION = 1
MANIFEST_NAME = "datacore-skill-install.json"


@dataclass(frozen=True)
class AgentTarget:
    name: str
    display_name: str
    skills_root: Path
    markers: tuple[Path, ...]

    def is_detected(self) -> bool:
        return any(marker.exists() for marker in self.markers)


def canonical_skills_root() -> Path:
    override = os.environ.get("DATACORE_SKILLS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".agents" / "skills"


def manifest_path() -> Path:
    return canonical_skills_root().parent / MANIFEST_NAME


def _config_home() -> Path:
    value = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return Path(value).expanduser() if value else Path.home() / ".config"


def _agent_targets() -> dict[str, AgentTarget]:
    home = Path.home()
    config_home = _config_home()
    codex_home = Path(os.environ.get("CODEX_HOME", "").strip() or home / ".codex")
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", "").strip() or home / ".claude")

    openclaw_homes = tuple(
        path for path in (home / ".openclaw", home / ".clawdbot", home / ".moltbot")
    )
    openclaw_home = next((path for path in openclaw_homes if path.exists()), openclaw_homes[0])

    targets = (
        AgentTarget("codex", "Codex", codex_home / "skills", (codex_home,)),
        AgentTarget("claude-code", "Claude Code", claude_home / "skills", (claude_home,)),
        AgentTarget("continue", "Continue", home / ".continue" / "skills", (home / ".continue",)),
        AgentTarget("cursor", "Cursor", home / ".cursor" / "skills", (home / ".cursor",)),
        AgentTarget("crush", "Crush", config_home / "crush" / "skills", (config_home / "crush",)),
        AgentTarget("devin", "Devin", config_home / "devin" / "skills", (config_home / "devin",)),
        AgentTarget("droid", "Droid", home / ".factory" / "skills", (home / ".factory",)),
        AgentTarget("forgecode", "ForgeCode", home / ".forge" / "skills", (home / ".forge",)),
        AgentTarget("gemini-cli", "Gemini CLI", home / ".gemini" / "skills", (home / ".gemini",)),
        AgentTarget(
            "github-copilot",
            "GitHub Copilot",
            home / ".copilot" / "skills",
            (home / ".copilot",),
        ),
        AgentTarget("goose", "Goose", config_home / "goose" / "skills", (config_home / "goose",)),
        AgentTarget("openclaw", "OpenClaw", openclaw_home / "skills", openclaw_homes),
        AgentTarget(
            "opencode", "OpenCode", config_home / "opencode" / "skills", (config_home / "opencode",)
        ),
        AgentTarget(
            "openhands", "OpenHands", home / ".openhands" / "skills", (home / ".openhands",)
        ),
        AgentTarget("qoder", "Qoder", home / ".qoder" / "skills", (home / ".qoder",)),
        AgentTarget("qoder-cn", "Qoder CN", home / ".qoder-cn" / "skills", (home / ".qoder-cn",)),
        AgentTarget("qwen-code", "Qwen Code", home / ".qwen" / "skills", (home / ".qwen",)),
        AgentTarget("roo-code", "Roo Code", home / ".roo" / "skills", (home / ".roo",)),
        AgentTarget("trae", "Trae", home / ".trae" / "skills", (home / ".trae",)),
        AgentTarget("trae-cn", "Trae CN", home / ".trae-cn" / "skills", (home / ".trae-cn",)),
        AgentTarget(
            "windsurf",
            "Windsurf",
            home / ".codeium" / "windsurf" / "skills",
            (home / ".codeium" / "windsurf",),
        ),
    )
    return {target.name: target for target in targets}


def supported_agent_names() -> list[str]:
    return sorted(_agent_targets())


def _load_manifest() -> dict[str, Any]:
    path = manifest_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_manifest(value: dict[str, Any]) -> None:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{MANIFEST_NAME}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(b"symlink\0")
        digest.update(os.readlink(path).encode())
        return digest.hexdigest()
    if not path.exists():
        return ""
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _backup_path(path: Path, *, label: str, skill_name: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = canonical_skills_root().parent / "datacore-skill-backups" / stamp / label
    target = root / skill_name
    counter = 1
    while target.exists():
        target = root / f"{skill_name}-{counter}"
        counter += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        target.write_text(f"symlink: {os.readlink(path)}\n", encoding="utf-8")
    elif path.is_dir():
        shutil.copytree(path, target, symlinks=True)
    else:
        shutil.copy2(path, target)
    return target


def _should_backup(path: Path, *, expected_digest: str, new_digest: str) -> bool:
    if path.is_symlink():
        return False
    actual_digest = _tree_digest(path)
    return bool(actual_digest and actual_digest not in {expected_digest, new_digest})


def _replace_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / f".{target.name}.datacore-stage-{os.getpid()}"
    _remove_path(stage)
    shutil.copytree(source, stage)
    _remove_path(target)
    stage.replace(target)


def _link_or_copy(source: Path, target: Path, *, copy: bool) -> str:
    if copy:
        _replace_copy(source, target)
        return "copy"
    target.parent.mkdir(parents=True, exist_ok=True)
    _remove_path(target)
    try:
        relative = os.path.relpath(source, target.parent)
        target.symlink_to(relative, target_is_directory=True)
        return "symlink"
    except OSError:
        _replace_copy(source, target)
        return "copy-fallback"


def _managed_agent_names(manifest: dict[str, Any]) -> list[str]:
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list):
        return []
    return sorted(
        {
            str(item.get("agent"))
            for item in adapters
            if isinstance(item, dict) and item.get("agent")
        }
    )


def _normalized_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _manifest_adapter_path(item: dict[str, Any], names: list[str]) -> tuple[str, Path] | None:
    agent_name = str(item.get("agent") or "")
    recorded_path = str(item.get("path") or "")
    target = _agent_targets().get(agent_name)
    if target is None or not recorded_path:
        return None
    name = Path(recorded_path).name
    if name not in names:
        return None
    expected = target.skills_root / name
    if _normalized_path(Path(recorded_path)) != _normalized_path(expected):
        return None
    return agent_name, expected


def _selected_targets(
    requested_agents: list[str] | None, manifest: dict[str, Any]
) -> list[AgentTarget]:
    targets = _agent_targets()
    requested = list(requested_agents or [])
    if "*" in requested:
        selected = set(targets)
    elif requested:
        unknown = sorted(set(requested) - set(targets))
        if unknown:
            supported = ", ".join(sorted(targets))
            raise ValueError(f"不支持的 Agent：{', '.join(unknown)}。可选值：{supported} 或 *。")
        selected = set(requested)
    else:
        selected = {name for name, target in targets.items() if target.is_detected()}
        selected.update(name for name in _managed_agent_names(manifest) if name in targets)

    # v0.1-v0.3 installed directly into Codex. Keep that path synchronized during migration.
    codex_target = targets["codex"]
    legacy_names = ("datacore", "datacore-conductivity")
    if any((codex_target.skills_root / name).exists() for name in legacy_names):
        selected.add("codex")
    return [targets[name] for name in sorted(selected)]


def install_skills(
    source_root: Path,
    names: list[str],
    *,
    package_version: str,
    force: bool,
    requested_agents: list[str] | None = None,
    copy: bool = False,
) -> dict[str, Any]:
    canonical_root = canonical_skills_root()
    canonical_root.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    previous_digests = manifest.get("digests") if isinstance(manifest.get("digests"), dict) else {}
    installed: list[str] = []
    skipped: list[str] = []
    backups: list[str] = []
    digests: dict[str, str] = {}

    for name in names:
        source = source_root / name
        target = canonical_root / name
        new_digest = _tree_digest(source)
        digests[name] = new_digest
        if target.exists() or target.is_symlink():
            if not force:
                digests[name] = _tree_digest(target)
                skipped.append(name)
                continue
            if _should_backup(
                target,
                expected_digest=str(previous_digests.get(name) or ""),
                new_digest=new_digest,
            ):
                backups.append(str(_backup_path(target, label="canonical", skill_name=name)))
        _replace_copy(source, target)
        installed.append(name)

    adapters: list[dict[str, str]] = []
    warnings: list[str] = []
    for agent in _selected_targets(requested_agents, manifest):
        for name in names:
            source = canonical_root / name
            target = agent.skills_root / name
            if target == source:
                continue
            if target.is_symlink() and target.resolve(strict=False) == source.resolve(strict=False):
                adapters.append(
                    {
                        "agent": agent.name,
                        "displayName": agent.display_name,
                        "path": str(target),
                        "method": "symlink",
                    }
                )
                continue
            if target.exists() or target.is_symlink():
                if not force:
                    warnings.append(f"{agent.display_name} 已有 {name}，未覆盖。")
                    continue
                if _should_backup(
                    target,
                    expected_digest=str(previous_digests.get(name) or ""),
                    new_digest=digests[name],
                ):
                    backups.append(str(_backup_path(target, label=agent.name, skill_name=name)))
            method = _link_or_copy(source, target, copy=copy)
            if method == "copy-fallback":
                warnings.append(f"{agent.display_name} 不支持符号链接，已改为复制 Skill。")
            adapters.append(
                {
                    "agent": agent.name,
                    "displayName": agent.display_name,
                    "path": str(target),
                    "method": method,
                }
            )

    _write_manifest(
        {
            "schemaVersion": MANIFEST_VERSION,
            "packageVersion": package_version,
            "canonicalRoot": str(canonical_root),
            "skills": names,
            "digests": digests,
            "adapters": adapters,
            "updatedAt": datetime.now(UTC).isoformat(),
        }
    )
    return {
        "installed": installed,
        "skipped": skipped,
        "canonicalPath": str(canonical_root),
        "agents": sorted({item["displayName"] for item in adapters}),
        "adapters": adapters,
        "backups": backups,
        "warnings": warnings,
    }


def skills_status(names: list[str]) -> dict[str, Any]:
    canonical_root = canonical_skills_root()
    manifest = _load_manifest()
    installed = [name for name in names if (canonical_root / name / "SKILL.md").is_file()]
    adapters = manifest.get("adapters") if isinstance(manifest.get("adapters"), list) else []
    active_adapters: list[dict[str, Any]] = []
    ignored_adapters = 0
    for item in adapters:
        if not isinstance(item, dict):
            ignored_adapters += 1
            continue
        validated = _manifest_adapter_path(item, names)
        if validated is None:
            ignored_adapters += 1
            continue
        _agent, expected = validated
        if (expected / "SKILL.md").is_file():
            active_adapters.append({**item, "path": str(expected)})
    return {
        "expected": names,
        "installed": installed,
        "canonicalPath": str(canonical_root),
        "supportedAgents": supported_agent_names(),
        "agents": sorted(
            {str(item.get("displayName")) for item in active_adapters if item.get("displayName")}
        ),
        "adapters": active_adapters,
        "warnings": (
            [f"忽略了 {ignored_adapters} 条无效的 Agent 适配记录。"] if ignored_adapters else []
        ),
    }


def uninstall_skills(names: list[str]) -> dict[str, Any]:
    canonical_root = canonical_skills_root()
    manifest = _load_manifest()
    previous_digests = manifest.get("digests") if isinstance(manifest.get("digests"), dict) else {}
    removed: list[str] = []
    backups: list[str] = []
    warnings: list[str] = []

    adapter_paths: set[tuple[str, str]] = set()
    adapters = manifest.get("adapters") if isinstance(manifest.get("adapters"), list) else []
    for item in adapters:
        if not isinstance(item, dict):
            warnings.append("忽略了一条格式无效的 Agent 适配记录。")
            continue
        validated = _manifest_adapter_path(item, names)
        if validated is None:
            warnings.append("忽略了一条路径超出支持范围的 Agent 适配记录。")
            continue
        agent_name, path = validated
        adapter_paths.add((agent_name, str(path)))

    # Also clean the v0.1-v0.3 Codex-only locations when no manifest recorded them.
    codex = _agent_targets()["codex"]
    for name in names:
        adapter_paths.add(("codex", str(codex.skills_root / name)))

    for label, raw_path in sorted(adapter_paths):
        path = Path(raw_path)
        if not path.exists() and not path.is_symlink():
            continue
        name = path.name
        expected = str(previous_digests.get(name) or "")
        if _should_backup(path, expected_digest=expected, new_digest=expected):
            backups.append(str(_backup_path(path, label=label, skill_name=name)))
        _remove_path(path)
        removed.append(str(path))

    for name in names:
        path = canonical_root / name
        if not path.exists() and not path.is_symlink():
            continue
        expected = str(previous_digests.get(name) or "")
        if _should_backup(path, expected_digest=expected, new_digest=expected):
            backups.append(str(_backup_path(path, label="canonical", skill_name=name)))
        _remove_path(path)
        removed.append(str(path))

    try:
        manifest_path().unlink(missing_ok=True)
    except OSError as exc:
        warnings.append(f"安装记录未能删除：{exc}")
    return {"removed": removed, "backups": backups, "warnings": warnings}
