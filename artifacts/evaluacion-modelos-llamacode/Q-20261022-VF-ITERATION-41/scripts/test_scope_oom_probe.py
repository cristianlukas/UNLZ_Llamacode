#!/usr/bin/env python3
"""CPU-only regressions for the Q41 scope OOM receipt parser."""
import unittest

from run_scope_oom_probe import normalize_cgroup, parse_events


class ScopeOomProbeParserTests(unittest.TestCase):
    def test_normalizes_procfs_cgroup_v2_record(self):
        self.assertEqual(
            normalize_cgroup("0::/background.slice/job.scope\n"),
            "/background.slice/job.scope",
        )

    def test_accepts_raw_cgroup_path_from_worker_receipt(self):
        self.assertEqual(
            normalize_cgroup("/background.slice/job.scope"),
            "/background.slice/job.scope",
        )

    def test_parses_memory_events_counters(self):
        self.assertEqual(
            parse_events("low 0\nhigh 1\nmax 2\noom 1\noom_kill 1\n"),
            {"low": 0, "high": 1, "max": 2, "oom": 1, "oom_kill": 1},
        )


if __name__ == "__main__":
    unittest.main()
