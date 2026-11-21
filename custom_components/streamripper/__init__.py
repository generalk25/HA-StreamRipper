"""StreamRipper: the media conversion farm, in Home Assistant.

Discovers the streamripper coordinator on the LAN by mDNS
(_streamripper._tcp) or takes a manual address, then mirrors
its state as entities: the running job, the fleet, the review
queues, and the levers — the jobs pause and the three passive
jobs — as switches.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .api import StreamRipperApiError, StreamRipperClient
from .const import CONF_API_TOKEN
from .coordinator import StreamRipperCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    base_url = f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
    client = StreamRipperClient(
        aiohttp_client.async_get_clientsession(hass),
        base_url,
        entry.data[CONF_API_TOKEN],
    )
    try:
        status = await client.async_validate()
    except StreamRipperApiError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc
    instance_id = status.get("instance_id") or entry.unique_id or base_url
    coordinator = StreamRipperCoordinator(hass, client, instance_id)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
