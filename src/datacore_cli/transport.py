from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

from .errors import DataCoreCliError


class DataCoreTransport:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout: float = 120.0,
        request_id: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        # 一个 CLI 命令可能编排多个 HTTP 请求。整条命令共用 request id，服务端据此
        # 做日额度幂等扣费；每个原始请求仍独立进入分钟突发限制。
        self.request_id = request_id.strip() or uuid.uuid4().hex

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-DataCore-Client": "datacore-cli/0.2",
            "X-Request-ID": self.request_id,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        binary: bool = False,
    ) -> Any:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                response = client.request(
                    method,
                    f"{self.base_url}{path}",
                    params=params,
                    json=json_body,
                    files=files,
                    data=data,
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise DataCoreCliError(
                "DataCore 请求超时；云端任务可能仍在继续运行",
                code="request_timeout",
                action="运行 status 查看实际状态，不要立即重复提交。",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise DataCoreCliError(
                f"无法连接 DataCore：{exc}",
                code="network_error",
                action="检查网络和 --base-url 后重试。",
                retryable=True,
            ) from exc
        if not response.is_success:
            try:
                body = response.json()
            except ValueError:
                body = {"detail": response.text[:2000]}
            detail = body.get("detail", body) if isinstance(body, dict) else body
            code = "http_error"
            message = f"DataCore 返回 HTTP {response.status_code}"
            action = ""
            action_url = ""
            retryable = response.status_code >= 500 or response.status_code == 429
            if isinstance(detail, dict):
                code = str(detail.get("code") or detail.get("error_code") or code)
                message = str(detail.get("message") or detail.get("detail") or message)
                action = str(detail.get("action") or "")
                action_url = str(detail.get("actionUrl") or detail.get("action_url") or "")
                retryable = bool(detail.get("retryable", retryable))
            elif detail:
                message = str(detail)
            if response.status_code == 401:
                action = "运行 datacore auth login 重新登录。"
                code = "authentication_required"
            elif action_url:
                if action_url.startswith("/"):
                    action_url = f"{self.base_url}{action_url}"
                if action_url not in action:
                    action = f"{action} {action_url}".strip()
            raise DataCoreCliError(
                message,
                code=code,
                status_code=response.status_code,
                details=detail,
                action=action,
                retryable=retryable,
            )
        if binary:
            return {
                "content": response.content,
                "contentType": response.headers.get("content-type"),
                "contentDisposition": response.headers.get("content-disposition"),
                "demoBasis": response.headers.get("x-demo-basis"),
            }
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise DataCoreCliError(
                "DataCore 返回了无法解析的响应",
                code="invalid_response",
                details=response.text[:2000],
            ) from exc

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)


def save_binary(result: dict[str, Any], output: str | Path) -> dict[str, Any]:
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(result["content"]))
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "contentType": result.get("contentType"),
        "demoBasis": result.get("demoBasis"),
    }


__all__ = ["DataCoreTransport", "save_binary"]
