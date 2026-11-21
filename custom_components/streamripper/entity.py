"""Shared entity base: every entity hangs off the one
StreamRipper device (the coordinator), keyed by its stable
instance id so a change of address never orphans the device.
"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StreamRipperCoordinator


class StreamRipperEntity(CoordinatorEntity[StreamRipperCoordinator]):
    """Base for all StreamRipper entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: StreamRipperCoordinator,
                 key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.instance_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.instance_id)},
            name="StreamRipper",
            manufacturer="StreamRipper",
            model="Media conversion coordinator",
            configuration_url=coordinator.client.base_url,
        )

    @property
    def _status(self) -> dict:
        return (self.coordinator.data or {}).get("status") or {}

    @property
    def _workers_doc(self) -> dict:
        return (self.coordinator.data or {}).get("workers") or {}

    @property
    def _jobs_doc(self) -> dict:
        return (self.coordinator.data or {}).get("jobs") or {}
