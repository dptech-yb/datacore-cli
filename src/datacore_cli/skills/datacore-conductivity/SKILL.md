---
name: datacore-conductivity
description: "Inspect and operate DataCore's conductivity Bayesian-optimization loop through the datacore CLI. Apply for conductivity round status, recommendations, UniLab exports, measured-result validation/upload, five-fold training, fold recovery, model comparison, stop/continue decisions, or opening the next round."
---

# Datacore Conductivity

Accept the full DataCore conductivity page URL as the preferred target. It preserves experiment, chain, and round identity; a raw `round...` identifier is acceptable only for round-scoped actions.

Follow the lifecycle instead of guessing:

1. Run `datacore --json conductivity status TARGET`.
2. Execute only the next valid action reported by DataCore.
3. Validate a returned CSV before upload. Validation is read-only.
4. Before recommend, upload, train, retry, decide, or next, summarize the exact action and obtain explicit confirmation; only then pass `--yes`.
5. After submitting cloud work, report that it is queued/running and use status polling. Never treat a local timeout as task failure.
6. Show all five fold states when training. Retry only unfinished work; completed folds must not be duplicated.
7. Use the user's own remembered Bohrium credential. Never substitute a platform credential and never ask for a secret in chat.

Read [commands](references/commands.md) for exact syntax. Read [recovery](references/recovery.md) only when a command returns an error or a long-running operation stalls.
