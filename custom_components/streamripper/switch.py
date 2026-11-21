"""Switches: the levers the dashboard has, mirrored.

The jobs-pause switch drives the agent directives (pause_jobs
cancels the running job and sets the brake; resume_jobs lifts
it). The three passive switches drive the per-job checkmarks —
a passive job starts itself when the runner is free and its
cadence is due, and never cancels another job to do so.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PASSIVE_JOBS
from .coordinator import StreamRipperCoordinator
from .entity import StreamRipperEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: StreamRipperCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = [JobsPausedSwitch(coordinator)]
    for name in PASSIVE_JOBS:
        entities.append(PassiveSwitch(coordinator, name))
    async_add_entities(entities)


class JobsPausedSwitch(StreamRipperEntity, SwitchEntity):
    """The jobs brake: on means paused."""

    _attr_name = "Pause Jobs"
    _attr_icon = "mdi:pause-octagon-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "pause_jobs")

    @property
    def is_on(self) -> bool:
        return bool(self._status.get("paused"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.async_directive("pause_jobs")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_directive("resume_jobs")
        await self.coordinator.async_request_refresh()


class PassiveSwitch(StreamRipperEntity, SwitchEntity):
    """One passive job's checkmark."""

    _attr_icon = "mdi:timer-play-outline"

    def __init__(self, coordinator: StreamRipperCoordinator,
                 job_name: str) -> None:
        super().__init__(coordinator, f"passive_{job_name}")
        self._job_name = job_name
        self._attr_name = f"Passive {job_name.replace('_', ' ').title()}"

    def _passive(self) -> dict:
        for job in self._jobs_doc.get("jobs") or []:
            if job.get("name") == self._job_name:
                return job.get("passive") or {}
        return {}

    @property
    def is_on(self) -> bool:
        return bool(self._passive().get("enabled"))

    @property
    def extra_state_attributes(self) -> dict:
        passive = self._passive()
        return {
            "last_started": passive.get("last_started"),
            "last_activity": passive.get("last_activity"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.async_set_passive(
            self._job_name, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_set_passive(
            self._job_name, False)
        await self.coordinator.async_request_refresh()
