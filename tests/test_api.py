"""The API client, against a fake aiohttp session.

The client is the only part of the integration with real logic
of its own (auth header, error mapping, the passive and
directive posts), so it is the part that gets tests; the rest
is Home Assistant framework plumbing.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent
           / "custom_components" / "streamripper"))

from api import (  # noqa: E402
    StreamRipperApiError,
    StreamRipperAuthError,
    StreamRipperClient,
)


class _Resp:
    def __init__(self, status=200, body=None):
        self.status = status
        self._body = body or {}

    async def json(self, content_type=None):
        return self._body


class _Ctx:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _Session:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def request(self, method, url, json=None, headers=None):
        self.calls.append((method, url, json, headers))
        return _Ctx(self._resp)


def _client(session):
    return StreamRipperClient(session, "http://192.168.51.251:9595/", "tok")


def test_get_status_uses_bearer_and_trims_base():
    session = _Session(_Resp(200, {"service": "streamripper"}))
    out = asyncio.run(_client(session).async_get_status())
    assert out["service"] == "streamripper"
    method, url, _payload, headers = session.calls[0]
    assert method == "GET"
    assert url == "http://192.168.51.251:9595/agent/status"
    assert headers == {"Authorization": "Bearer tok"}


def test_auth_error_maps_from_401():
    session = _Session(_Resp(401))
    with pytest.raises(StreamRipperAuthError):
        asyncio.run(_client(session).async_get_status())


def test_server_error_maps_to_api_error():
    session = _Session(_Resp(500))
    with pytest.raises(StreamRipperApiError):
        asyncio.run(_client(session).async_get_jobs())


def test_directive_and_passive_posts():
    session = _Session(_Resp(200, {"ok": True}))
    client = _client(session)
    asyncio.run(client.async_directive("pause_jobs"))
    asyncio.run(client.async_set_passive("save_space", True))
    assert session.calls[0][1].endswith("/agent/directive")
    assert session.calls[0][2] == {"type": "pause_jobs"}
    assert session.calls[1][1].endswith("/jobs/passive")
    assert session.calls[1][2] == {"name": "save_space", "passive": True}
