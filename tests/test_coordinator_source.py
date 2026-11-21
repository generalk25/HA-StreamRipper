"""Source guards for the polling coordinator.

The coordinator module imports Home Assistant itself, so it
cannot be imported in this lightweight test environment —
which is exactly how the HA 2026.11 breakage shipped: no
test ever constructed the coordinator, and a removed
DataUpdateCoordinator kwarg killed config-entry setup on
every attempt. These guards pin the two facts that matter:

- super().__init__() is never handed a ``timeout`` kwarg
  (current HA rejects it with TypeError before any entity
  exists);
- the 30-second budget lives around the fetch instead,
  as an asyncio.timeout in the update method, with a
  timeout surfacing as UpdateFailed so the coordinator
  keeps its last good data.
"""

import pathlib
import re
import unittest

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components" / "streamripper" / "coordinator.py"
).read_text(encoding="utf-8")


class CoordinatorTimeoutGuardTests(unittest.TestCase):

    def test_no_timeout_kwarg_to_super_init(self):
        init_block = SOURCE.split("super().__init__(", 1)[1].split(")", 1)[0]
        self.assertNotIn("timeout", init_block)

    def test_fetch_is_wrapped_in_a_timeout(self):
        self.assertIn("asyncio.timeout(30)", SOURCE)

    def test_timeout_becomes_update_failed(self):
        self.assertRegex(
            SOURCE, re.compile(
                r"except TimeoutError.*?:\s*\n\s*raise UpdateFailed",
                re.DOTALL))


if __name__ == "__main__":
    unittest.main()
