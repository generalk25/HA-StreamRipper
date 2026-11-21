"""The StreamRipper coordinator API client.

Talks to the streamripper daemon's HTTP API (the same surface
its dashboard uses): /agent/status for job state, /workers for
the fleet, /jobs for the catalog and passive checkmarks, and
the agent directive + passive posts for the switches.
"""

from __future__ import annotations

import aiohttp


class StreamRipperApiError(Exception):
    """The coordinator could not be reached or answered badly."""


class StreamRipperAuthError(StreamRipperApiError):
    """The API token was refused."""


class StreamRipperClient:
    """A thin async client for one streamripper coordinator."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str,
                 token: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._token = token

    @property
    def base_url(self) -> str:
        return self._base

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def _request(self, method: str, path: str,
                       payload: dict | None = None) -> dict:
        try:
            async with self._session.request(
                method, f"{self._base}{path}", json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status in (401, 403):
                    raise StreamRipperAuthError(
                        f"token refused ({resp.status})")
                if resp.status >= 400:
                    raise StreamRipperApiError(
                        f"{method} {path} answered {resp.status}")
                return await resp.json(content_type=None)
        except StreamRipperApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise StreamRipperApiError(str(exc)) from exc

    async def async_get_status(self) -> dict:
        return await self._request("GET", "/agent/status")

    async def async_get_workers(self) -> dict:
        return await self._request("GET", "/workers")

    async def async_get_jobs(self) -> dict:
        return await self._request("GET", "/jobs")

    async def async_get_schedules(self) -> dict:
        return await self._request("GET", "/schedules")

    async def async_validate(self) -> dict:
        """The status document doubles as the credential check."""
        return await self.async_get_status()

    async def async_directive(self, directive: str) -> dict:
        return await self._request(
            "POST", "/agent/directive", {"type": directive})

    async def async_set_passive(self, name: str, enabled: bool) -> dict:
        return await self._request(
            "POST", "/jobs/passive", {"name": name, "passive": enabled})
