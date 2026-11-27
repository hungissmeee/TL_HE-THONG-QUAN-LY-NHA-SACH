"""Kiểm thử launcher chạy đồng thời Backend và Frontend."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import ConfigurationError
from run_web import _npm_command, load_frontend_options


class WebLauncherTests(unittest.TestCase):
    def setUp(self):
        self.backend_env = patch(
            "backend.config.ENV_FILE", Path(".missing-run-web-test-env")
        )
        self.frontend_env = patch(
            "run_web.ENV_FILE", Path(".missing-run-web-test-env")
        )
        self.backend_env.start()
        self.frontend_env.start()
        self.addCleanup(self.backend_env.stop)
        self.addCleanup(self.frontend_env.stop)

    def test_frontend_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            options = load_frontend_options()
        self.assertEqual(options.host, "127.0.0.1")
        self.assertEqual(options.port, 5173)

    def test_frontend_reads_host_and_port(self):
        env = {
            "BOOKHUB_WEB_FRONTEND_HOST": "0.0.0.0",
            "BOOKHUB_WEB_FRONTEND_PORT": "5174",
        }
        with patch.dict(os.environ, env, clear=True):
            options = load_frontend_options()
        self.assertEqual(options.host, "0.0.0.0")
        self.assertEqual(options.port, 5174)

    def test_frontend_rejects_invalid_port(self):
        with patch.dict(
            os.environ, {"BOOKHUB_WEB_FRONTEND_PORT": "70000"}, clear=True
        ):
            with self.assertRaisesRegex(ConfigurationError, "1–65535"):
                load_frontend_options()

    def test_frontend_rejects_empty_host(self):
        with patch.dict(
            os.environ, {"BOOKHUB_WEB_FRONTEND_HOST": " "}, clear=True
        ):
            with self.assertRaisesRegex(ConfigurationError, "không được để trống"):
                load_frontend_options()


    def test_windows_npm_command_quotes_program_files_path(self):
        npm_path = r"C:\Program Files\nodejs\npm.cmd"
        with patch("run_web.os.name", "nt"):
            with patch.dict(
                os.environ,
                {"COMSPEC": r"C:\Windows\System32\\cmd.exe"},
            ):
                command = _npm_command(
                    npm_path,
                    ["install", "--no-audit", "--no-fund"],
                )

        self.assertEqual(command[0], r"C:\Windows\System32\\cmd.exe")
        self.assertEqual(command[1:4], ["/d", "/s", "/c"])
        self.assertTrue(command[4].startswith('call "C:\\Program Files\nodejs\npm.cmd"'))
        self.assertIn("install --no-audit --no-fund", command[4])

    def test_windows_npm_command_preserves_dev_server_arguments(self):
        with patch("run_web.os.name", "nt"):
            command = _npm_command(
                r"C:\Program Files\nodejs\npm.cmd",
                [
                    "run", "dev", "--",
                    "--host", "127.0.0.1",
                    "--port", "5173",
                    "--strictPort",
                ],
            )

        self.assertIn('call "C:\\Program Files\nodejs\npm.cmd"', command[4])
        self.assertIn("run dev -- --host 127.0.0.1 --port 5173 --strictPort", command[4])

    def test_non_windows_npm_command_does_not_use_cmd_shell(self):
        args = ["install", "--no-audit"]
        with patch("run_web.os.name", "posix"):
            command = _npm_command("/usr/bin/npm", args)
        self.assertEqual(command, ["/usr/bin/npm", *args])


if __name__ == "__main__":
    unittest.main()
