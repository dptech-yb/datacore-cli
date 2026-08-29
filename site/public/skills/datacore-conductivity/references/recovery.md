# Recovery

- Authentication errors: run `datacore auth login`; do not request another person's token.
- Permission errors: the current DataCore user lacks project or block access. Do not bypass or switch identities silently.
- Validation errors: report the specific row/column/recommendation mismatch and keep the operation read-only.
- Bohrium credential errors: direct the user to manage their own AccessKey and project in DataCore; never use a platform fallback.
- Rate limits or transient provider errors: honor `retryable`, use bounded backoff, then run status before resubmitting.
- Local watch timeout/disconnect: the cloud operation may continue. Run status; do not duplicate the task.
- Partial five-fold failure: show all folds, call `retry-fold` for an unfinished fold, and explain that the server preserves completed folds.
