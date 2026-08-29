---
name: datacore
description: "Use DataCore platform capabilities through the datacore CLI. Apply when a user asks to inspect or operate DataCore projects, experiments, conductivity optimization, reports, tools, reservations, reagents, or other DataCore resources. The CLI always acts as the signed-in DataCore user and preserves platform permissions."
metadata:
  version: "0.4.5"
  requires:
    bins: ["datacore"]
  cliHelp: "datacore --help"
---

# DataCore

Use `datacore` as the deterministic execution layer. Do not reproduce DataCore business rules in shell, Python, or the model.

1. Run read-only discovery or status commands before proposing a write.
2. Use `--json` when another program or agent will consume the result.
3. For a write or cloud-compute command, show the resolved target and action, obtain explicit confirmation, then pass `--yes`.
4. Never request, print, log, or pass DataCore bearer tokens or Bohrium AccessKeys on the command line. A one-time Agent install token may only be consumed from standard input and must not be repeated in the final response. Compute commands use the current user's encrypted credential already managed by DataCore.
5. Treat permission, validation, and lifecycle errors as authoritative platform decisions. Follow the returned `action`; do not bypass them.
6. Check `datacore --json capabilities` when uncertain whether a capability is currently exposed.
7. Check `datacore --json quota` before large batches. Quotas belong to the DataCore user, reset at Beijing midnight, and are shared by CLI, Skills, and third-party Agents.
8. If the task concerns conductivity optimization, read the sibling `datacore-conductivity/SKILL.md` and follow it.

Read only the reference needed for the task:

- [CLI conventions](references/cli-conventions.md): authentication, JSON output, files, errors, or quotas.
- [Projects and experiments](references/projects-and-experiments.md): project or experiment discovery, lineage, create, or update.
- [Experimental resources](references/experimental-resources.md): bookings, reagents, chemicals, or tool history.
