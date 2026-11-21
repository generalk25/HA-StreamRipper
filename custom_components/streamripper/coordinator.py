"""The polling coordinator: one fetch cycle feeds every entity.

The three reads ride together so a card never mixes a fresh job
state with a stale fleet. The streamripper status read is the
heavy one on the far side (it can take seconds while a job's
preview is scanning the library), so the coordinator allows a
long timeout and simply keeps the last good data on a failure —
Home Assistant marks the entities unavailable only while the
coordinator itself is unreachable, which is the truth.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import StreamRipperApiError, StreamRipperClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class StreamRipperCoordinator(DataUpdateCoordinator[dict]):
    """Polls status + workers + jobs into one snapshot dict."""

    def __init__(self, hass: HomeAssistant, client: StreamRipperClient,
                 instance_id: str) -> None:
        # No timeout kwarg here: current Home Assistant's
        # DataUpdateCoordinator no longer accepts one (passing
        # it killed setup outright on HA 2026.11 — the entry
        # never got past __init__). The 30-second budget lives
        # around the fetch itself, in _async_update_data.
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.instance_id = instance_id

    async def _async_update_data(self) -> dict:
        try:
            async with asyncio.timeout(30):
                status = await self.client.async_get_status()
                workers = await self.client.async_get_workers()
                jobs = await self.client.async_get_jobs()
        except StreamRipperApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        except TimeoutError as exc:
            raise UpdateFailed(
                "status read timed out after 30 seconds") from exc
        return {"status": status, "workers": workers, "jobs": jobs}
