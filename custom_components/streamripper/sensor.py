"""Sensors: the job, the fleet, and the queues that want a human.

Per worker there are three entities: the state sensor
carrying every attribute the coordinator reports (the full
presentation.worker_attributes spread — current job, pace,
mode, schedules, vitals, the lot), plus dedicated numeric
Progress (%) and Throughput (GB/h) sensors so Home
Assistant can graph and automate on them. The coordinator
itself rides as a worker too, from the workers document's
local entry.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import presentation
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
        SchedulesSensor(coordinator),
    ]
    workers_doc = (coordinator.data or {}).get("workers", {})
    fleet = list(workers_doc.get("workers") or [])
    local = workers_doc.get("local") or {}
    if local.get("name"):
        fleet.append(local)
    for worker in fleet:
        name = worker.get("name")
        if not name:
            continue
        is_local = bool(worker.get("local"))
        entities.append(WorkerSensor(coordinator, name, is_local))
        entities.append(WorkerProgressSensor(coordinator, name, is_local))
        entities.append(WorkerThroughputSensor(coordinator, name, is_local))
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
            "running": self._jobs_doc.get("running"),
            "passive": presentation.passive_states(self._jobs_doc),
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
            "modes": {
                w.get("name"): w.get("mode")
                for w in self._fleet() if w.get("name")
            },
        }


class _WorkerEntity(StreamRipperEntity):
    """Resolves one worker entry — a fleet row, or the
    coordinator's own local entry — by name."""

    def __init__(self, coordinator: StreamRipperCoordinator,
                 key: str, worker_name: str, local: bool) -> None:
        super().__init__(coordinator, key)
        self._worker_name = worker_name
        self._local = local

    def _worker(self) -> dict:
        if self._local:
            return self._workers_doc.get("local") or {}
        for worker in self._workers_doc.get("workers") or []:
            if worker.get("name") == self._worker_name:
                return worker
        return {}


class WorkerSensor(_WorkerEntity, SensorEntity):
    """One worker's state, with everything the coordinator
    reports about it as attributes (presentation.py owns
    the spread)."""

    _attr_icon = "mdi:desktop-classic"

    def __init__(self, coordinator: StreamRipperCoordinator,
                 worker_name: str, local: bool = False) -> None:
        super().__init__(
            coordinator, f"worker_{worker_name}", worker_name, local)
        self._attr_name = f"Worker {worker_name}"

    @property
    def native_value(self) -> str | None:
        return self._worker().get("state")

    @property
    def extra_state_attributes(self) -> dict:
        return presentation.worker_attributes(self._worker())


class WorkerProgressSensor(_WorkerEntity, SensorEntity):
    """How far through its current job the worker is, as a
    graphable percentage."""

    _attr_icon = "mdi:progress-clock"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: StreamRipperCoordinator,
                 worker_name: str, local: bool = False) -> None:
        super().__init__(
            coordinator, f"worker_{worker_name}_progress",
            worker_name, local)
        self._attr_name = f"Worker {worker_name} Progress"

    @property
    def native_value(self) -> float | None:
        value = self._worker().get("progress_pct")
        return float(value) if isinstance(value, (int, float)) else None


class WorkerThroughputSensor(_WorkerEntity, SensorEntity):
    """The worker's recent pace: average GB/hr over the
    trailing 24 hours of completed work (None — shown
    unavailable — when it completed nothing measurable)."""

    _attr_icon = "mdi:speedometer"
    _attr_native_unit_of_measurement = "GB/h"

    def __init__(self, coordinator: StreamRipperCoordinator,
                 worker_name: str, local: bool = False) -> None:
        super().__init__(
            coordinator, f"worker_{worker_name}_throughput",
            worker_name, local)
        self._attr_name = f"Worker {worker_name} Throughput"

    @property
    def native_value(self) -> float | None:
        value = self._worker().get("rate_gb_hr")
        return float(value) if isinstance(value, (int, float)) else None


class SchedulesSensor(StreamRipperEntity, SensorEntity):
    """Plan runs scheduled for later: the count waiting,
    with the list as attributes."""

    _attr_name = "Schedules"
    _attr_icon = "mdi:calendar-clock-outline"

    def __init__(self, coordinator: StreamRipperCoordinator) -> None:
        super().__init__(coordinator, "schedules")

    def _pending(self) -> list[dict]:
        return [row for row in presentation.schedule_rows(self._schedules)
                if row.get("status") == "pending"]

    @property
    def native_value(self) -> int:
        return len(self._pending())

    @property
    def extra_state_attributes(self) -> dict:
        pending = self._pending()
        return {
            "next_run": pending[0]["run_at"] if pending else None,
            "next_job": pending[0]["job"] if pending else None,
            "schedules": presentation.schedule_rows(self._schedules),
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
