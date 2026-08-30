---
name: datacore-conductivity
description: "Inspect and operate DataCore's conductivity Bayesian-optimization loop through the datacore CLI. Apply for conductivity round status, recommendations, UniLab exports, measured-result validation/upload, five-fold training, fold recovery, model comparison, stop/continue decisions, or opening the next round."
metadata:
  version: "0.4.8"
  requires:
    bins: ["datacore"]
  cliHelp: "datacore conductivity --help"
---

# DataCore Conductivity

Resolve the work in the same terms the user sees in DataCore:

1. If no project is established, run `datacore --json project list`. Show project names and ask only if multiple reasonable choices remain.
2. Run `datacore --json experiment list --project-id ID`. Show experiment names, not internal identifiers, and resolve the experiment.
3. Run `datacore --json conductivity list ID` to list that experiment's exploration records and rounds. Present only exploration titles, round labels, status, and the available actions. If there is one viable choice, select it; otherwise ask the user.
4. Keep the selected `pageUrl` for subsequent commands, but do not expose or ask the user for internal chain, turn, or round-reference fields.
5. Run `conductivity status` on the selected round and execute only the next valid action reported by DataCore. “Continue” means resume that round from its server-reported state. “Open next round” means use `conductivity next` on the selected exploration after DataCore allows it. Starting a separate exploration from baseline is a different action and remains page-driven because it requires experiment configuration.
6. Validate a returned CSV before upload. Validation is read-only.
7. Before recommend, upload, train, retry, decide, or next, summarize the exact action and obtain explicit confirmation; only then pass `--yes`.
8. After submitting cloud work, report that it is queued/running and use status polling. Never treat a local timeout as task failure.
9. Show all five fold states when training. Retry only unfinished work; completed folds must not be duplicated.
10. Use the Bohrium account connected to the current DataCore user. The platform resolves that user's AK server-side. Never substitute a platform credential and never ask for an AK or other secret in chat.
11. If DataCore returns `bohrium_binding_required`, show the returned personal-center URL and stop. Continue the original command only after the user has completed OAuth connection and explicitly asks to resume.

Read [commands](references/commands.md) for exact syntax. Read [recovery](references/recovery.md) only when a command returns an error or a long-running operation stalls.
