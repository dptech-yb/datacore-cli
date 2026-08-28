# Contributing

1. Create a focused branch and keep platform API changes backwards compatible.
2. Install development dependencies with `python -m pip install -e '.[dev]'`.
3. Run `ruff check .`, `ruff format --check .`, and `pytest` before opening a pull request.
4. Never commit DataCore tokens, user data, internal deployment configuration, or production exports.
5. Commands that write data or start cloud compute must continue to require explicit confirmation.

The public CLI consumes stable DataCore APIs. Server implementation details belong in the DataCore platform repository, not here.
