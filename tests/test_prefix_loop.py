import unittest

from tools.benchmark_prefix_loop import tool_schema


class PrefixLoopBenchmarkTests(unittest.TestCase):
    def test_rolling_schema_is_stable_and_unstable_variant_changes_key_order(self):
        stable = tool_schema(False)[0]["function"]
        unstable = tool_schema(True)[0]["function"]
        self.assertEqual(stable, unstable)
        self.assertNotEqual(list(stable.keys()), list(unstable.keys()))


if __name__ == "__main__":
    unittest.main()
