"""Sensors: the job, the fleet, and the queues that want a human."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import StreamRipperCoordinator
from .entity import StreamRipperEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: StreamRipperCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        JobSensor(coordinator),
        WorkersOnlineSensor(coordinator),
        PendingStepsSensor(coordinator),
        FailureReviewSensor(coordinator),
        LanguageReviewSensor(coordinator),
        DeletionQueueSensor(coordinator),
    ]
    for worker in (coordinator.data or {}).get("workers", {}).get(
            "workers", []):
        name = worker.get("name")
        if name:
            entities.append(WorkerSensor(coordinator, name))
    async_add_entities(entities)


class JobSensor(StreamRipperEntity, SensorEntity):
    """The running job's name, or Idle."""

    _attr_name = "Job"
    _attr_icon = "mdi:cog-play-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "job")

    @property
    def native_value(self) -> str:
        job = self._status.get("job") or {}
        if job.get("state") == "running" and job.get("job"):
            return str(job["job"])
        return "Idle"

    @property
    def extra_state_attributes(self) -> dict:
        job = self._status.get("job") or {}
        return {
            "state": job.get("state"),
            "phase": job.get("phase"),
            "current": job.get("current"),
            "total": job.get("total"),
            "started_at": job.get("started_at"),
            "last_error": job.get("last_error"),
        }


class WorkersOnlineSensor(StreamRipperEntity, SensorEntity):
    """How many fleet workers are fresh, and what each is doing."""

    _attr_name = "Workers Online"
    _attr_icon = "mdi:server-network"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "workers_online")

    def _fleet(self) -> list[dict]:
        return self._workers_doc.get("workers") or []

    @property
    def native_value(self) -> int:
        return sum(1 for w in self._fleet() if w.get("fresh"))

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "workers": {
                w.get("name"): w.get("state")
                for w in self._fleet() if w.get("name")
            },
        }


class WorkerSensor(StreamRipperEntity, SensorEntity):
    """One fleet worker's state, with its current file."""

    _attr_icon = "mdi:desktop-classic"

    def __init__(self, coordinator: StreamRipperCoordinator,
                 worker_name: str) -> None:
        super().__init__(coordinator, f"worker_{worker_name}")
        self._worker_name = worker_name
        self._attr_name = f"Worker {worker_name}"

    def _worker(self) -> dict:
        for worker in self._workers_doc.get("workers") or []:
            if worker.get("name") == self._worker_name:
                return worker
        return {}

    @property
    def native_value(self) -> str | None:
        return self._worker().get("state")

    @property
    def extra_state_attributes(self) -> dict:
        worker = self._worker()
        return {
            "current_file": worker.get("current_file"),
            "progress_pct": worker.get("progress_pct"),
            "mode": worker.get("mode"),
            "paused": worker.get("paused"),
            "pause_reason": worker.get("pause_reason"),
            "fresh": worker.get("fresh"),
        }


class PendingStepsSensor(StreamRipperEntity, SensorEntity):
    """Plan steps waiting in the worker pool."""

    _attr_name = "Pending Steps"
    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "pending_steps")

    @property
    def native_value(self) -> int | None:
        queue = self._status.get("queue") or {}
        return queue.get("pending_steps")


class FailureReviewSensor(StreamRipperEntity, SensorEntity):
    """Genuine failures waiting for a dismiss/requeue call."""

    _attr_name = "Failure Review"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "failure_review")

    @property
    def native_value(self) -> int | None:
        queue = self._jobs_doc.get("failure_queue") or {}
        return queue.get("waiting")


class LanguageReviewSensor(StreamRipperEntity, SensorEntity):
    """Language verdicts waiting on review."""

    _attr_name = "Language Review"
    _attr_icon = "mdi:translate"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "language_review")

    @property
    def native_value(self) -> int | None:
        review = self._status.get("language_review") or {}
        return review.get("pending")


class DeletionQueueSensor(StreamRipperEntity, SensorEntity):
    """Foreign-language files inside their deletion fuse window."""

    _attr_name = "Deletion Queue"
    _attr_icon = "mdi:delete-clock-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "deletion_queue")

    @property
    def native_value(self) -> int | None:
        queue = self._status.get("deletion_queue") or {}
        return queue.get("waiting")
