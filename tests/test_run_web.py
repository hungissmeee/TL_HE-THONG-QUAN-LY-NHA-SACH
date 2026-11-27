"""Kiểm thử launcher chạy đồng thời Backend và Frontend."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import ConfigurationError
from run_web import load_frontend_options, load_web_options


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

    def test_combined_launcher_uses_distinct_default_ports(self):
        with patch.dict(os.environ, {}, clear=True):
            options = load_web_options()
        self.assertEqual(options.backend_port, 8000)
        self.assertEqual(options.frontend_port, 5173)

    def test_combined_launcher_rejects_duplicate_ports(self):
        env = {
            "BOOKHUB_WEB_PORT": "8000",
            "BOOKHUB_WEB_FRONTEND_PORT": "8000",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "khác nhau"):
                load_web_options()


if __name__ == "__main__":
    unittest.main()
