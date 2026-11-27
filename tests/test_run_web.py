"""Kiểm thử launcher chạy đồng thời Backend và Frontend."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import ConfigurationError
from run_web import NpmRuntime, _npm_command, load_frontend_options


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


    def test_npm_runtime_runs_node_directly_with_paths_containing_spaces(self):
        runtime = NpmRuntime((
            "C:\\Program Files\\nodejs\\node.exe",
            "C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
        ))
        command = _npm_command(runtime, ["install", "--no-audit", "--no-fund"])

        self.assertEqual(command[0], "C:\\Program Files\\nodejs\\node.exe")
        self.assertEqual(
            command[1],
            "C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
        )
        self.assertEqual(command[2:], ["install", "--no-audit", "--no-fund"])
        self.assertNotIn("cmd.exe", command[0].lower())
        self.assertNotIn("npm.cmd", command[0].lower())

    def test_npm_runtime_preserves_vite_arguments(self):
        runtime = NpmRuntime((
            "C:\\Program Files\\nodejs\\node.exe",
            "C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
        ))
        command = _npm_command(
            runtime,
            [
                "run", "dev", "--",
                "--host", "127.0.0.1",
                "--port", "5173",
                "--strictPort",
            ],
        )

        self.assertEqual(command[2:], [
            "run", "dev", "--",
            "--host", "127.0.0.1",
            "--port", "5173",
            "--strictPort",
        ])

    def test_npm_command_accepts_standard_npm_runtime_on_linux(self):
        runtime = NpmRuntime(("/usr/bin/npm",))
        command = _npm_command(runtime, ["install", "--no-audit"])
        self.assertEqual(command, ["/usr/bin/npm", "install", "--no-audit"])



if __name__ == "__main__":
    unittest.main()
