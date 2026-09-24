import unittest

from tools.benchmark_image_history import has_image, png_data_uri, trim_stale_images


class ImageHistoryBenchmarkTests(unittest.TestCase):
    def test_png_data_uri_is_non_empty(self):
        uri = png_data_uri(255, 0, 0)
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        self.assertGreater(len(uri), 40)

    def test_trim_stale_images_preserves_only_latest_messages(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": [{"type": "text", "text": "one"},
                                               {"type": "image_url", "image_url": {"url": "data:1"}}]},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": [{"type": "text", "text": "two"},
                                               {"type": "image_url", "image_url": {"url": "data:2"}}]},
        ]
        trimmed = trim_stale_images(messages, 1)
        self.assertFalse(has_image(trimmed[1]))
        self.assertTrue(has_image(trimmed[3]))
        self.assertIn("omitida", trimmed[1]["content"][-1]["text"])


if __name__ == "__main__":
    unittest.main()
