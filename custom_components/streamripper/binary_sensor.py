"""Binary sensors: is a job running, and is the brake on."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import StreamRipperCoordinator
from .entity import StreamRipperEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: StreamRipperCoordinator = entry.runtime_data
    async_add_entities([
        RunningBinarySensor(coordinator),
        PausedBinarySensor(coordinator),
    ])


class RunningBinarySensor(StreamRipperEntity, BinarySensorEntity):
    """On while any job runs on the coordinator."""

    _attr_name = "Running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "running")

    @property
    def is_on(self) -> bool:
        job = self._status.get("job") or {}
        return job.get("state") == "running"


class PausedBinarySensor(StreamRipperEntity, BinarySensorEntity):
    """On while the jobs brake (pause) is set."""

    _attr_name = "Jobs Paused"
    _attr_icon = "mdi:pause-circle-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "jobs_paused")

    @property
    def is_on(self) -> bool:
        return bool(self._status.get("paused"))
