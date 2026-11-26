from __future__ import annotations

import json

import httpx
import pytest

from datacore_cli.main import FEEDBACK_SCOPES, STANDARD_SCOPES, _auth_login


def setup_auth(monkeypatch, replies):
    calls = []
    saved = []
    original = httpx.Client

    def handler(request):
        calls.append(request)
        return replies.pop(0)

    monkeypatch.setattr(
        "datacore_cli.main.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    monkeypatch.setattr(
        "datacore_cli.main.save_token",
        lambda _base, token, **_kwargs: saved.append(token) or "keychain",
    )
    return calls, saved


def start_response():
    return httpx.Response(
        201,
        json={
            "deviceCode": "synthetic-device",
            "pendingToken": "synthetic-pending",
            "userCode": "EXAMPLE00",
            "verificationUri": "https://example.test/authorize",
            "expiresIn": 60,
        },
    )


def login():
    return _auth_login(
        "https://example.test", as_json=True, no_browser=True, allow_file_credential=False
    )


def test_legacy_unknown_feedback_scopes_retry_once_preserves_all_existing_scopes(
    monkeypatch, capsys
):
    calls, saved = setup_auth(
        monkeypatch,
        [
            httpx.Response(
                400,
                json={
                    "detail": {
                        "code": "invalid_scope",
                        "message": "不支持的授权范围：feedback:read, feedback:write",
                    }
                },
            ),
            start_response(),
            httpx.Response(200, json={"status": "authorized"}),
        ],
    )
    assert login() == 0
    starts = [json.loads(call.content) for call in calls if call.method == "POST"]
    assert len(starts) == 2
    assert starts[0]["scopes"] == STANDARD_SCOPES
    assert starts[1]["scopes"] == [s for s in STANDARD_SCOPES if s not in FEEDBACK_SCOPES]
    assert saved == ["synthetic-pending"]
    output = capsys.readouterr().out
    assert "synthetic-pending" not in output
    assert "重新申请反馈权限" in json.loads(output)["warnings"][0]


def test_feedback_capable_platform_requests_scopes_without_retry(monkeypatch, capsys):
    calls, _saved = setup_auth(
        monkeypatch,
        [
            start_response(),
            httpx.Response(200, json={"status": "authorized"}),
        ],
    )
    assert login() == 0
    assert len([c for c in calls if c.method == "POST"]) == 1
    assert json.loads(calls[0].content)["scopes"] == STANDARD_SCOPES
    assert json.loads(capsys.readouterr().out)["warnings"] == []


@pytest.mark.parametrize(
    "status,detail",
    [
        (400, {"code": "invalid_scope", "message": "不支持的授权范围：tools:read"}),
        (400, {"code": "invalid_scope", "message": "不支持的授权范围：feedback:read, tools:read"}),
        (400, {"code": "invalid_scope", "message": "至少需要一个授权范围"}),
        (403, {"code": "invalid_scope", "message": "不支持的授权范围：feedback:read"}),
        (422, {"code": "invalid_scope", "message": "不支持的授权范围：feedback:read"}),
    ],
)
def test_unrelated_authentication_errors_are_never_retried(monkeypatch, status, detail):
    calls, saved = setup_auth(monkeypatch, [httpx.Response(status, json={"detail": detail})])
    with pytest.raises(httpx.HTTPStatusError):
        login()
    assert len(calls) == 1
    assert not saved


def test_legacy_retry_is_bounded_even_if_second_request_rejects(monkeypatch):
    def response():
        return httpx.Response(
            400,
            json={
                "detail": {
                    "code": "invalid_scope",
                    "message": "不支持的授权范围：feedback:read, feedback:write",
                }
            },
        )

    calls, saved = setup_auth(monkeypatch, [response(), response()])
    with pytest.raises(httpx.HTTPStatusError):
        login()
    assert len(calls) == 2 and not saved
