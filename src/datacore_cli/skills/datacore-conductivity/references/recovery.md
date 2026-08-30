# Recovery

- Authentication errors: run `datacore auth login`; do not request another person's token.
- Permission errors: the current DataCore user lacks project or block access. Do not bypass or switch identities silently.
- Selection errors: rerun `project list`, `experiment list --project-id ID`, and `conductivity list ID`; present human names and round labels. Never ask the user to copy internal chain or turn parameters.
- Validation errors: report the specific row/column/recommendation mismatch and keep the operation read-only.
- Bohrium binding or credential errors: direct the user to the personal-center URL returned by DataCore to connect or reconnect Bohrium. Do not request an AccessKey and never use a platform fallback.
- Rate limits or transient provider errors: honor `retryable`, use bounded backoff, then run status before resubmitting.
- Local watch timeout/disconnect: the cloud operation may continue. Run status; do not duplicate the task.
- Partial five-fold failure: show all folds, call `retry-fold` for an unfinished fold, and explain that the server preserves completed folds.
