# CLI conventions

## Authentication

- `datacore auth login` opens the DataCore authorization page. Password, Feishu, or Bohrium login all resolve to the same DataCore identity.
- `datacore auth logout` revokes the current client authorization, not merely the local token.
- The user can inspect or revoke clients in DataCore Personal Center.
- Never put a token or Bohrium AccessKey into arguments, prompts, logs, or generated files.

## Output

Use `--json` for automation. Successful output has `ok`, `command`, `summary`, `data`, `artifacts`, and `warnings`. Failed output has `ok=false` and an `error` with stable `code`, `message`, `action`, `retryable`, and `details`.

## Long-running tasks

Submitting a command and watching it are separate. Interrupting a local watch does not cancel the cloud task. Run a status command before retrying to avoid duplicate work.

## Files

Input paths must be explicit local files. Output files are written to the requested path and returned in `artifacts`. Do not infer that an exported file has been uploaded elsewhere.
