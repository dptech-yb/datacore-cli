from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DOCS = SITE / "src" / "content" / "docs"
PUBLIC = SITE / "public"
AGENT_SKILLS_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
sys.path.insert(0, str(ROOT / "src"))

from datacore_cli import __version__  # noqa: E402
from datacore_cli.main import _parser  # noqa: E402


def parser_help(parser: argparse.ArgumentParser) -> dict[str, str]:
    result: dict[str, str] = {}
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for choice in action._choices_actions:
            result[choice.dest] = choice.help or ""
    return result


def argument_record(action: argparse.Action) -> dict[str, Any]:
    flags = list(action.option_strings)
    return {
        "name": action.dest,
        "flags": flags,
        "required": bool(getattr(action, "required", False) or not flags),
        "help": action.help if action.help not in {None, argparse.SUPPRESS} else "",
        "choices": list(action.choices) if action.choices is not None else [],
        "default": None if action.default is argparse.SUPPRESS else action.default,
    }


def walk_commands(
    parser: argparse.ArgumentParser,
    path: list[str],
    inherited: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    local = [
        argument_record(action)
        for action in parser._actions
        if not isinstance(action, (argparse._HelpAction, argparse._SubParsersAction))
    ]
    subparsers = next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )
    if subparsers is None:
        arguments = [*inherited, *local]
        flags = {flag for item in arguments for flag in item["flags"]}
        return [
            {
                "command": " ".join(path),
                "summary": parser.description or "",
                "arguments": arguments,
                "requiresConfirmation": "--yes" in flags,
                "supportsJson": "--json" in flags,
            }
        ]

    help_by_name = parser_help(parser)
    records: list[dict[str, Any]] = []
    for name, child in subparsers.choices.items():
        child.description = child.description or help_by_name.get(name, "")
        records.extend(walk_commands(child, [*path, name], [*inherited, *local]))
    return records


def frontmatter_and_body(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return path.stem, text
    marker = text.find("\n---\n", 4)
    if marker < 0:
        return path.stem, text
    frontmatter = text[4:marker]
    body = text[marker + 5 :]
    title = path.stem
    for line in frontmatter.splitlines():
        if line.startswith("title:"):
            title = line.partition(":")[2].strip().strip('"')
            break
    return title, body


def frontmatter_value(path: Path, key: str) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    marker = text.find("\n---\n", 4)
    if marker < 0:
        return ""
    prefix = f"{key}:"
    for line in text[4:marker].splitlines():
        if line.startswith(prefix):
            return line.partition(":")[2].strip().strip('"').strip("'")
    return ""


def regular_skill_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Skill source must not contain symbolic links: {path}")
        if path.is_file():
            files.append(path)
    return files


def write_skill_archive(source: Path, target: Path) -> str:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in regular_skill_files(source):
            info = zipfile.ZipInfo(path.relative_to(source).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"


def write_command_reference(commands: list[dict[str, Any]]) -> None:
    lines = [
        "---",
        "title: CLI 命令参考",
        "description: 由当前 DataCore CLI 参数定义自动生成的命令与选项参考。",
        "---",
        "",
        "> 本页由 CLI 参数定义自动生成。命令变更后，文档构建会同步更新并检查差异。",
        "",
    ]
    for command in commands:
        lines.extend(
            [
                f"## `{command['command']}`",
                "",
                command["summary"] or "DataCore CLI 命令。",
                "",
            ]
        )
        positional = [item for item in command["arguments"] if not item["flags"]]
        options = [item for item in command["arguments"] if item["flags"]]
        if positional:
            lines.extend(["### 参数", "", "| 名称 | 必填 | 可选值 |", "| --- | --- | --- |"])
            for item in positional:
                choices = " / ".join(str(value) for value in item["choices"]) or "—"
                lines.append(f"| `{item['name']}` | 是 | {choices} |")
            lines.append("")
        if options:
            lines.extend(["### 选项", "", "| 选项 | 说明 |", "| --- | --- |"])
            for item in options:
                flags = ", ".join(f"`{flag}`" for flag in item["flags"])
                help_text = item["help"] or "—"
                lines.append(f"| {flags} | {help_text} |")
            lines.append("")
    (DOCS / "reference" / "commands.md").write_text("\n".join(lines), encoding="utf-8")


def write_agent_surfaces(commands: list[dict[str, Any]]) -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "commands.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1",
                "cli": "datacore",
                "version": __version__,
                "generatedFrom": "src/datacore_cli/main.py",
                "commands": commands,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    skill_dirs = [
        ROOT / "src" / "datacore_cli" / "skills" / "datacore",
        ROOT / "src" / "datacore_cli" / "skills" / "datacore-conductivity",
    ]
    skill_files = {source: regular_skill_files(source) for source in skill_dirs}
    for source in skill_dirs:
        target = PUBLIC / "skills" / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

    legacy_discovery = {
        "skills": [
            {
                "name": source.name,
                "description": frontmatter_value(source / "SKILL.md", "description"),
                "files": [path.relative_to(source).as_posix() for path in skill_files[source]],
            }
            for source in skill_dirs
        ]
    }
    preferred_root = PUBLIC / ".well-known" / "agent-skills"
    if preferred_root.exists():
        shutil.rmtree(preferred_root)
    preferred_root.mkdir(parents=True)
    preferred_entries: list[dict[str, str]] = []
    for source in skill_dirs:
        archive_name = f"{source.name}.zip"
        digest = write_skill_archive(source, preferred_root / archive_name)
        preferred_entries.append(
            {
                "name": source.name,
                "type": "archive",
                "description": frontmatter_value(source / "SKILL.md", "description"),
                "url": archive_name,
                "digest": digest,
            }
        )
    (preferred_root / "index.json").write_text(
        json.dumps(
            {"$schema": AGENT_SKILLS_SCHEMA, "skills": preferred_entries},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    legacy_root = PUBLIC / ".well-known" / "skills"
    if legacy_root.exists():
        shutil.rmtree(legacy_root)
    legacy_root.mkdir(parents=True)
    (legacy_root / "index.json").write_text(
        json.dumps(legacy_discovery, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for source in skill_dirs:
        shutil.copytree(source, legacy_root / source.name)

    raw_pages: list[tuple[str, str, str]] = []
    for source in sorted(DOCS.rglob("*.md")):
        title, body = frontmatter_and_body(source)
        relative = source.relative_to(DOCS)
        target = PUBLIC / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = f"# {title}\n\n{body.strip()}\n"
        target.write_text(raw, encoding="utf-8")
        raw_pages.append((title, "/" + relative.as_posix(), raw))

    index_text = """# DataCore CLI

DataCore CLI 将平台能力提供给终端、自动化程序和 AI Agent。
当前版本覆盖项目、实验、物质、预约、试剂、工具记录与完整电导率预测迭代，
并沿用当前登录用户的 DataCore 权限。

- 人类文档：https://datacore-cli.dp.cd.mba/
- 命令清单：https://datacore-cli.dp.cd.mba/commands.json
- Skills 发现：https://datacore-cli.dp.cd.mba/.well-known/agent-skills/index.json
- 基础 Skill：https://datacore-cli.dp.cd.mba/skills/datacore/SKILL.md
- 电导 Skill：https://datacore-cli.dp.cd.mba/skills/datacore-conductivity/SKILL.md
"""
    (PUBLIC / "index.md").write_text(index_text, encoding="utf-8")

    llms = [
        "# DataCore CLI",
        "",
        "> DataCore 平台 CLI 与可安装 Agent Skills。统一开放普通用户平台能力。",
        "",
        "## Start here",
        "",
        "- [安装与快速开始](/getting-started/install.md)",
        "- [身份、授权与权限](/getting-started/authentication.md)",
        "- [第三方 Agent 接入](/agents/index.md)",
        "- [电导率预测迭代](/workflows/conductivity.md)",
        "- [CLI 命令参考](/reference/commands.md)",
        "- [结构化输出约定](/reference/output-contract.md)",
        "- [故障恢复](/troubleshooting.md)",
        "",
        "## Machine-readable",
        "",
        "- [commands.json](/commands.json)",
        "- [Agent Skills discovery](/.well-known/agent-skills/index.json)",
        "- [DataCore Skill](/skills/datacore/SKILL.md)",
        "- [Conductivity Skill](/skills/datacore-conductivity/SKILL.md)",
        "",
    ]
    (PUBLIC / "llms.txt").write_text("\n".join(llms), encoding="utf-8")
    full_sections = [index_text]
    for _title, path, raw in raw_pages:
        full_sections.append(f"\n---\n\nSource: {path}\n\n{raw}")
    for source in skill_dirs:
        full_sections.append(
            f"\n---\n\nSource: /skills/{source.name}/SKILL.md\n\n"
            + (source / "SKILL.md").read_text(encoding="utf-8")
        )
    (PUBLIC / "llms-full.txt").write_text("\n".join(full_sections), encoding="utf-8")
    (PUBLIC / "agent.json").write_text(
        json.dumps(
            {
                "name": "DataCore CLI",
                "description": "DataCore CLI and installable Agent Skills",
                "documentation": "https://datacore-cli.dp.cd.mba/",
                "llms": "https://datacore-cli.dp.cd.mba/llms.txt",
                "commands": "https://datacore-cli.dp.cd.mba/commands.json",
                "skillDiscovery": (
                    "https://datacore-cli.dp.cd.mba/.well-known/agent-skills/index.json"
                ),
                "skills": [
                    "https://datacore-cli.dp.cd.mba/skills/datacore/SKILL.md",
                    "https://datacore-cli.dp.cd.mba/skills/datacore-conductivity/SKILL.md",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    commands = walk_commands(_parser(), ["datacore"], [])
    write_command_reference(commands)
    write_agent_surfaces(commands)


if __name__ == "__main__":
    main()
