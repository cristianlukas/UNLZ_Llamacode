#!/usr/bin/env python3
"""Offline policy tests for the Q100 loopback tool filter."""
import importlib.util
import unittest
from pathlib import Path

PROXY = Path(__file__).with_name("q100_tool_guard_proxy.py")
SPEC = importlib.util.spec_from_file_location("q100_tool_guard_proxy", PROXY)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def tool(name):
    return {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}


class Q100ToolGuardProxyTests(unittest.TestCase):
    def test_parent_surface_only_exposes_task(self):
        payload = {"messages": [{"role": "system", "content": "main agent"}],
                   "tools": [tool("task"), tool("run_shell"), tool("write_file")]}
        role, allowed = MODULE.filter_request_tools(payload)
        self.assertEqual(role, "parent")
        self.assertEqual(allowed, {"task"})
        self.assertEqual([MODULE.tool_name(x) for x in payload["tools"]], ["task"])

    def test_subagent_surface_only_exposes_read_file(self):
        payload = {"messages": [{"role": "system", "content":
                                  "Sos un sub-agente de coding autónomo en un git worktree"}],
                   "tools": [tool("read_file"), tool("run_shell"), tool("write_file"), tool("task")]}
        role, allowed = MODULE.filter_request_tools(payload)
        self.assertEqual(role, "subagent")
        self.assertEqual(allowed, {"read_file"})
        self.assertEqual([MODULE.tool_name(x) for x in payload["tools"]], ["read_file"])

    def test_missing_required_schema_fails_closed(self):
        payload = {"messages": [{"role": "system", "content": "main agent"}],
                   "tools": [tool("run_shell")]}
        with self.assertRaisesRegex(ValueError, "expected tool schema missing"):
            MODULE.filter_request_tools(payload)

    def test_sse_tool_names_are_reassembled_and_detected(self):
        body = b"""data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"function\":{\"name\":\"read_\"}}]}}]}\n
data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"function\":{\"name\":\"file\"}}]}}]}\n
data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":1,\"function\":{\"name\":\"run_shell\"}}]}}]}\n
data: [DONE]\n\n"""
        self.assertEqual(MODULE.extract_tool_names(body), ["read_file", "run_shell"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
