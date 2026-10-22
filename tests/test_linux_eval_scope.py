import signal
import subprocess
import unittest
from unittest import mock

from tools.linux_eval_scope import main, run_scoped_command


class LinuxEvalScopeCliTests(unittest.TestCase):
    def test_run_scoped_command_returns_child_status_and_isolates_client_session(self):
        process = mock.Mock()
        process.wait.return_value = 23
        process.poll.return_value = 23
        scoped = mock.Mock(process=process)

        with mock.patch("tools.linux_eval_scope.popen_in_background_scope", return_value=scoped) as start:
            self.assertEqual(run_scoped_command(["/bin/true"]), 23)

        self.assertTrue(start.call_args.kwargs["start_new_session"])
        scoped.stop.assert_not_called()

    def test_sigterm_stops_scope_and_returns_shell_compatible_status(self):
        class FakeProcess:
            def __init__(self):
                self.returncode = None

            def wait(self, timeout=None):
                handler = signal.getsignal(signal.SIGTERM)
                handler(signal.SIGTERM, None)
                raise subprocess.TimeoutExpired("fake", timeout)

            def poll(self):
                return self.returncode

        process = FakeProcess()
        scoped = mock.Mock(process=process)

        def stop_scope():
            process.returncode = -signal.SIGTERM

        scoped.stop.side_effect = stop_scope
        with mock.patch("tools.linux_eval_scope.popen_in_background_scope", return_value=scoped):
            result = run_scoped_command(["/bin/sleep", "60"])

        self.assertEqual(result, 128 + signal.SIGTERM)
        scoped.stop.assert_called_once_with()

    def test_main_requires_explicit_command_separator(self):
        self.assertEqual(main(["--run", "/bin/true"]), 2)

    def test_main_fails_closed_when_scope_creation_fails(self):
        with mock.patch("tools.linux_eval_scope.run_scoped_command", side_effect=RuntimeError("oomd inactive")):
            self.assertEqual(main(["--run", "--", "/bin/true"]), 125)


if __name__ == "__main__":
    unittest.main()
