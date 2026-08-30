# CLI conventions

## Authentication

- `datacore auth login` opens the DataCore authorization page. Password, Feishu, or Bohrium login all resolve to the same DataCore identity.
- When the user gives an explicit one-time Agent install instruction from DataCore, install the official CLI and pass its `dc_install_…` value only through standard input to `datacore setup --install-token-stdin --allow-file-credential`. Never place it in a command argument, log, generated file, or final response.
- The install token expires in about 10 minutes and is consumed once. The exchanged `dc_cli_…` credential is written directly to the operating-system keychain or, only with the explicit fallback flag, a local `0600` file; it must never be printed.
- `datacore auth logout` revokes the current client authorization, not merely the local token.
- The user can inspect or revoke clients in DataCore Personal Center.
- Never put a long-lived DataCore token or Bohrium AccessKey into arguments, prompts, logs, or generated files. DataCore resolves the OAuth-connected user's Bohrium AK server-side. If binding is required, open the returned personal-center URL instead of asking for a secret. The short-lived installation material is the only exception and must be treated as single-use bootstrap input.

## Output

Use `--json` for automation. Successful output has `ok`, `command`, `summary`, `data`, `artifacts`, and `warnings`. Failed output has `ok=false` and an `error` with stable `code`, `message`, `action`, `retryable`, and `details`.

## Long-running tasks

Submitting a command and watching it are separate. Interrupting a local watch does not cancel the cloud task. Run a status command before retrying to avoid duplicate work.

## Quotas

- Run `datacore --json quota` to inspect remaining read, write, tool, and compute allowance.
- The same CLI invocation shares one request ID, so an orchestration that performs several HTTP calls in one bucket is charged once for its daily allowance.
- The per-minute burst limit still counts raw requests. Respect `rate_limit_exceeded`; wait until `resetAt` instead of retrying rapidly.
- Daily allowances reset naturally at 00:00 Asia/Shanghai. If a legitimate batch needs more, ask a DataCore administrator for a permanent override or a today-only grant.

## Files

Input paths must be explicit local files. Output files are written to the requested path and returned in `artifacts`. Do not infer that an exported file has been uploaded elsewhere.

Complex mutations use `--file payload.json --yes`. Inspect the JSON and resolved target before confirmation. Do not generate speculative fields; use the DataCore page or API error to obtain the required schema.
