from __future__ import annotations

from typing import Any


class DataCoreCliError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "datacore_error",
        status_code: int = 1,
        details: Any = None,
        action: str = "",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.action = action
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "action": self.action or None,
            "retryable": self.retryable,
            "details": self.details,
        }


def exit_code_for_error(error: DataCoreCliError) -> int:
    """Map stable error classes to process exit codes for scripts and agents."""

    if error.code in {"authentication_required", "device_denied", "device_expired"}:
        return 10
    if error.status_code == 403 or "permission" in error.code or "forbidden" in error.code:
        return 11
    if error.status_code == 404 or error.code.endswith("_not_found"):
        return 12
    if error.status_code == 409 or "conflict" in error.code:
        return 13
    if error.status_code == 429 or "rate" in error.code:
        return 14
    if error.code == "network_error":
        return 20
    if "timeout" in error.code:
        return 21
    if error.status_code >= 500:
        return 22
    if error.code in {"file_not_found", "invalid_response"}:
        return 30
    return 2


__all__ = ["DataCoreCliError", "exit_code_for_error"]
