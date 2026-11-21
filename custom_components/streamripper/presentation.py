"""Pure presentation helpers: coordinator payloads in,
Home Assistant attribute dicts out.

No Home Assistant imports live here on purpose — this is
the layer that decides what the entities show (David,
2026-11-21: "% done with current job, what job they're
working on, average GB/hr, passive / active state,
schedules... show all the things"), and keeping it free of
HA imports makes it unit-testable in the lightweight test
environment, the same lesson the coordinator's timeout
breakage taught. The entity classes stay thin glue.
"""

from __future__ import annotations

_GIB = 1_000_000_000.0


def mode_schedule_text(schedule) -> str | None:
    """A worker's mode schedule as one readable line:
    "weekdays active 07:00-19:00 · weekends active
    09:00-17:00", "off" when disabled, None when the worker
    has no schedule at all."""
    if not isinstance(schedule, dict):
        return None
    if not schedule.get("enabled"):
        return "off"
    parts = []
    for day, label in (("weekday", "weekdays"),
                       ("weekend", "weekends")):
        window = schedule.get(day) or {}
        start, until = window.get("active_from"), window.get("active_until")
        if start and until:
            parts.append(f"{label} active {start}-{until}")
    return " · ".join(parts) if parts else "on"


def _gb(value) -> float | None:
    if isinstance(value, (int, float)) and value > 0:
        return round(value / _GIB, 2)
    return None


def worker_attributes(worker: dict) -> dict:
    """Every field a workers-list entry carries, flattened
    into HA-safe attributes. Works for fleet entries and the
    coordinator's own local entry alike — missing fields
    simply land as None, never invented."""
    caps = worker.get("capabilities") or {}
    efficiency = worker.get("efficiency") or {}
    benched = worker.get("benched") or []
    schedule = worker.get("mode_schedule")
    return {
        "host": worker.get("host"),
        "local": bool(worker.get("local")),
        "fresh": worker.get("fresh"),
        "last_seen": worker.get("last_seen"),
        # The current job: what step, which file, how far.
        "step_label": worker.get("step_label"),
        "current_file": worker.get("current_file"),
        "current_step": worker.get("current_step"),
        "progress_pct": worker.get("progress_pct"),
        "from_codec": worker.get("from_codec"),
        "to_codec": worker.get("to_codec"),
        # Mode: passive / active, the pair behind it, and a
        # switch still being negotiated.
        "mode": worker.get("mode"),
        "mode_pending": worker.get("mode_pending"),
        "active_percent": worker.get("active_percent"),
        "passive_percent": worker.get("passive_percent"),
        "cpu_limit_percent_effective":
            worker.get("cpu_limit_percent_effective"),
        "cpu_limit_source": worker.get("cpu_limit_source"),
        "ffmpeg_cores": worker.get("ffmpeg_cores"),
        "ffmpeg_cores_total": worker.get("ffmpeg_cores_total"),
        # The machine and its curated efficiency estimate.
        "cpu_model": caps.get("cpu_model"),
        "cpu_threads": caps.get("cpu_threads"),
        "efficiency_index": efficiency.get("index"),
        "efficiency_grade": efficiency.get("grade"),
        "worker_class": worker.get("worker_class"),
        "stream_only": worker.get("stream_only"),
        # Holds and the reasons for them.
        "paused": worker.get("paused"),
        "pause_after": worker.get("pause_after"),
        "pause_reason": worker.get("pause_reason"),
        "idle_reason": worker.get("idle_reason"),
        # Host vitals, as the worker reported them.
        "cpu_pct": worker.get("cpu_pct"),
        "cpu_temp_c": worker.get("cpu_temp_c"),
        "mem_used_pct": worker.get("mem_used_pct"),
        "mem_total_mb": worker.get("mem_total_mb"),
        "load1": worker.get("load1"),
        "scratch_free_gb": _gb(worker.get("scratch_free_bytes")),
        "scratch_total_gb": _gb(worker.get("scratch_total_bytes")),
        "disk_scratch_free_gb": _gb(
            worker.get("disk_scratch_free_bytes")),
        # The record: all-time totals, the medal, the pace.
        "total_transcoded_bytes": worker.get("workload_bytes"),
        "total_transcoded_gb": _gb(worker.get("workload_bytes")),
        "medal_rank": worker.get("workload_rank"),
        "rate_gb_hr": worker.get("rate_gb_hr"),
        "rate_jobs_24h": worker.get("rate_jobs_24h"),
        "completed_claims": worker.get("completed"),
        "failed_claims": worker.get("failed"),
        "expired_claims": worker.get("expired"),
        # The bench: finished work held undelivered.
        "benched_count": len(benched),
        "benched_files": [
            {"file": b.get("file_name") or b.get("uuid"),
             "size": b.get("size")}
            for b in benched if isinstance(b, dict)
        ],
        # Schedules and console surface.
        "mode_schedule": schedule,
        "mode_schedule_text": mode_schedule_text(schedule),
        "tray_enabled": worker.get("tray_enabled"),
        "tray_controls": worker.get("tray_controls"),
        "wake_on_lan": worker.get("wol"),
    }


def schedule_rows(schedules) -> list[dict]:
    """The plan schedules, trimmed to what a card shows."""
    rows = []
    for entry in schedules or []:
        if not isinstance(entry, dict):
            continue
        rows.append({
            "job": entry.get("job"),
            "run_at": entry.get("run_at"),
            "status": entry.get("status"),
            "plan_id": entry.get("plan_id"),
        })
    return rows


def passive_states(jobs_doc: dict) -> dict:
    """The passive jobs' checkmarks and last activity, from
    the /jobs catalog's passive annotations."""
    out = {}
    for entry in (jobs_doc or {}).get("jobs") or []:
        info = entry.get("passive")
        if isinstance(info, dict) and entry.get("name"):
            out[entry["name"]] = {
                "enabled": bool(info.get("enabled")),
                "last_started": info.get("last_started"),
                "last_activity": info.get("last_activity"),
            }
    return out
