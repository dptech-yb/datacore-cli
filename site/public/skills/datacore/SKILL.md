---
name: datacore
description: "Use DataCore platform capabilities through the datacore CLI. Apply when a user asks to inspect or operate DataCore projects, experiments, conductivity optimization, reports, tools, reservations, reagents, or other DataCore resources. The CLI always acts as the signed-in DataCore user and preserves platform permissions."
---

# DataCore

Use `datacore` as the deterministic execution layer. Do not reproduce DataCore business rules in shell, Python, or the model.

1. Run read-only discovery or status commands before proposing a write.
2. Use `--json` when another program or agent will consume the result.
3. For a write or cloud-compute command, show the resolved target and action, obtain explicit confirmation, then pass `--yes`.
4. Never request, print, log, or pass Bohrium AccessKeys on the command line. Compute commands use the current user's encrypted credential already managed by DataCore.
5. Treat permission, validation, and lifecycle errors as authoritative platform decisions. Follow the returned `action`; do not bypass them.
6. If the task concerns conductivity optimization, read the sibling `datacore-conductivity/SKILL.md` and follow it.

Read [CLI conventions](references/cli-conventions.md) only when authentication, JSON output, files, or error recovery matters.
