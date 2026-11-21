"""Unit tests for the presentation layer — the module that
decides what the entities show. It imports no Home
Assistant code, so these run in the lightweight test env
(the coordinator-timeout lesson: logic that can only be
exercised inside HA tends to ship untested).
"""

import importlib.util
import pathlib
import unittest

# Loaded by path, not through the package: the package's
# __init__ imports Home Assistant, and this module's whole
# point is that the presentation logic does not.
_PATH = (pathlib.Path(__file__).resolve().parents[1]
         / "custom_components" / "streamripper" / "presentation.py")
_spec = importlib.util.spec_from_file_location("presentation", _PATH)
presentation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(presentation)

FLEET_WORKER = {
    "name": "hastur", "host": "hastur", "state": "encoding",
    "fresh": True, "last_seen": "2026-11-21T08:00:00+00:00",
    "current_file": "/media/Movie (2020).mkv",
    "current_step": "abc123", "step_label": "Movie (2020)",
    "progress_pct": 42.5, "from_codec": "hevc", "to_codec": "av1",
    "mode": "active", "mode_pending": None,
    "active_percent": 80, "passive_percent": 20,
    "cpu_limit_percent_effective": 80,
    "cpu_limit_source": "active setting",
    "ffmpeg_cores": 9, "ffmpeg_cores_total": 12,
    "capabilities": {"cpu_model": "Intel i7-8850H", "cpu_threads": 12},
    "efficiency": {"index": 100, "grade": "B"},
    "worker_class": "full", "stream_only": True,
    "paused": False, "pause_after": True, "pause_reason": None,
    "idle_reason": None,
    "cpu_pct": 61.0, "cpu_temp_c": 78.0, "mem_used_pct": 55.0,
    "mem_total_mb": 15821, "load1": 7.5,
    "scratch_free_bytes": 40_000_000_000,
    "scratch_total_bytes": 250_000_000_000,
    "disk_scratch_free_bytes": None,
    "workload_bytes": 109_000_000_000, "workload_rank": 2,
    "rate_gb_hr": 3.25, "rate_jobs_24h": 4,
    "completed": 30, "failed": 1, "expired": 2,
    "benched": [{"file_name": "Held.mkv", "size": 5_000_000_000}],
    "mode_schedule": {
        "enabled": True,
        "weekday": {"active_from": "07:00", "active_until": "19:00"},
        "weekend": {"active_from": "09:00", "active_until": "17:00"},
    },
    "tray_enabled": True, "tray_controls": True, "wol": False,
}


class WorkerAttributesTests(unittest.TestCase):

    def test_the_full_spread(self):
        attrs = presentation.worker_attributes(FLEET_WORKER)
        self.assertEqual(attrs["step_label"], "Movie (2020)")
        self.assertEqual(attrs["progress_pct"], 42.5)
        self.assertEqual(attrs["from_codec"], "hevc")
        self.assertEqual(attrs["mode"], "active")
        self.assertEqual(attrs["active_percent"], 80)
        self.assertEqual(attrs["cpu_limit_percent_effective"], 80)
        self.assertEqual(attrs["ffmpeg_cores"], 9)
        self.assertEqual(attrs["efficiency_grade"], "B")
        self.assertEqual(attrs["worker_class"], "full")
        self.assertEqual(attrs["rate_gb_hr"], 3.25)
        self.assertEqual(attrs["total_transcoded_gb"], 109.0)
        self.assertEqual(attrs["medal_rank"], 2)
        self.assertEqual(attrs["benched_count"], 1)
        self.assertEqual(
            attrs["benched_files"],
            [{"file": "Held.mkv", "size": 5_000_000_000}])
        self.assertEqual(
            attrs["mode_schedule_text"],
            "weekdays active 07:00-19:00 · weekends active 09:00-17:00")
        self.assertEqual(attrs["scratch_free_gb"], 40.0)
        self.assertIsNone(attrs["disk_scratch_free_gb"])

    def test_sparse_local_entry_never_invents(self):
        attrs = presentation.worker_attributes(
            {"name": "cthulhu", "local": True, "state": "idle"})
        self.assertTrue(attrs["local"])
        self.assertIsNone(attrs["progress_pct"])
        self.assertIsNone(attrs["rate_gb_hr"])
        self.assertIsNone(attrs["efficiency_grade"])
        self.assertEqual(attrs["benched_count"], 0)
        self.assertIsNone(attrs["mode_schedule_text"])


class ModeScheduleTextTests(unittest.TestCase):

    def test_none_without_a_schedule(self):
        self.assertIsNone(presentation.mode_schedule_text(None))
        self.assertIsNone(presentation.mode_schedule_text("junk"))

    def test_off_when_disabled(self):
        self.assertEqual(
            presentation.mode_schedule_text({"enabled": False}), "off")


class ScheduleAndPassiveTests(unittest.TestCase):

    def test_rows_are_trimmed(self):
        rows = presentation.schedule_rows([
            {"job": "normalize", "run_at": "2026-11-22T03:00:00",
             "status": "pending", "plan_id": 3, "last_error": "x"},
            "junk",
        ])
        self.assertEqual(rows, [{
            "job": "normalize", "run_at": "2026-11-22T03:00:00",
            "status": "pending", "plan_id": 3}])

    def test_passive_states(self):
        states = presentation.passive_states({"jobs": [
            {"name": "analyze", "passive": {
                "enabled": True, "last_started": "t1",
                "last_activity": "t2"}},
            {"name": "normalize"},
        ]})
        self.assertEqual(states, {"analyze": {
            "enabled": True, "last_started": "t1",
            "last_activity": "t2"}})


if __name__ == "__main__":
    unittest.main()
