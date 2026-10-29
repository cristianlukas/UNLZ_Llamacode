#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_q180 import is_inference_process


class InferenceProcessFilterTests(unittest.TestCase):
    def test_shell_grep_text_is_not_a_server(self):
        argv = ["/bin/bash", "-c", "ps -eo args | grep llama-server"]
        self.assertFalse(is_inference_process("bash", argv))

    def test_real_llama_server_is_detected_from_comm(self):
        self.assertTrue(is_inference_process("llama-server", ["llama-server", "--port", "8033"]))

    def test_real_server_is_detected_from_executable(self):
        argv = ["/opt/llama.cpp/bin/llama-server", "--model", "model.gguf"]
        self.assertTrue(is_inference_process("llama-server", argv))

    def test_python_vllm_module_is_detected(self):
        argv = ["/usr/bin/python3", "-m", "vllm.entrypoints.openai.api_server"]
        self.assertTrue(is_inference_process("python3", argv))

    def test_unrelated_python_text_is_not_a_server(self):
        argv = ["/usr/bin/python3", "-c", "print('llama-server')"]
        self.assertFalse(is_inference_process("python3", argv))

    def test_unrelated_electron_process_is_not_a_server(self):
        argv = ["/usr/bin/electron", "--app", "/tmp/browser"]
        self.assertFalse(is_inference_process("electron", argv))


if __name__ == "__main__":
    unittest.main()
