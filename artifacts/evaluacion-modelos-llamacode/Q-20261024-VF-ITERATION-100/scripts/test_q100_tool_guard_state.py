#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from q100_tool_guard_state import clear_proxy_log, first_blocked_tool_call


class Q100ToolGuardStateTests(unittest.TestCase):
    def test_missing_or_clean_log_has_no_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxy.jsonl"
            self.assertIsNone(first_blocked_tool_call(path))
            path.write_text(json.dumps({"blockedToolCall": False}) + "\n")
            self.assertIsNone(first_blocked_tool_call(path))

    def test_detects_blocked_call_and_returns_only_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxy.jsonl"
            path.write_text(json.dumps({"blockedToolCall": True,
                                        "observedToolNames": ["read_file", "read_file"],
                                        "prompt": "do not return this"}) + "\n")
            self.assertEqual(first_blocked_tool_call(path), ["read_file", "read_file"])

    def test_ignores_partial_json_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxy.jsonl"
            path.write_text('{"blockedToolCall": true')
            self.assertIsNone(first_blocked_tool_call(path))

    def test_clear_starts_each_attempt_with_an_empty_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "proxy.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text('{"blockedToolCall": true}\n')
            clear_proxy_log(path)
            self.assertEqual(path.read_text(), "")
            self.assertIsNone(first_blocked_tool_call(path))


if __name__ == "__main__":
    unittest.main()
