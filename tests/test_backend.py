"""Kiểm thử Backend FastAPI và cấu hình SQL Server, không cần database thật."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.config import ConfigurationError, Settings, load_settings
from backend.database import (
    DatabaseUnavailableError,
    build_connection_string,
    create_connection,
)
from backend.dependencies import get_db_connection
from backend.main import create_app


def make_settings(**overrides):
    values = {
        "app_name": "BookHub Test API",
        "environment": "test",
        "api_prefix": "/api/v1",
        "allowed_origins": ("http://localhost:5173",),
        "docs_enabled": True,
        "sql_server": "localhost\\SQLEXPRESS",
        "sql_database": "CSDLTEST",
        "sql_driver": "ODBC Driver 18 for SQL Server",
        "sql_username": "bookhub_web",
        "sql_password": "not-a-real-password",
        "sql_encrypt": True,
        "sql_trust_server_certificate": False,
        "sql_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings(**values)


class FakeCursor:
    def __init__(self, row=(1,), error=None):
        self.row = row
        self.error = error
        self.closed = False
        self.executed = []

    def execute(self, sql, *params):
        self.executed.append((sql, params))
        if self.error:
            raise self.error
        return self

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor=None):
        self.fake_cursor = cursor or FakeCursor()
        self.closed = False
        self.rollback_called = False

    def cursor(self):
        return self.fake_cursor

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.closed = True


class BackendConfigurationTests(unittest.TestCase):
    def test_load_settings_uses_web_namespace_and_safe_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.api_prefix, "/api/v1")
        self.assertFalse(settings.sql_trust_server_certificate)
        self.assertFalse(settings.database_configured)

    def test_load_settings_rejects_invalid_environment(self):
        with patch.dict(os.environ, {"BOOKHUB_WEB_ENV": "prod"}, clear=True):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_load_settings_rejects_wildcard_origin_in_production(self):
        env = {
            "BOOKHUB_WEB_ENV": "production",
            "BOOKHUB_WEB_ALLOWED_ORIGINS": "*",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "wildcard"):
                load_settings()

    def test_load_settings_rejects_invalid_sql_timeout(self):
        env = {"BOOKHUB_WEB_SQL_TIMEOUT_SECONDS": "0"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_connection_string_requires_dedicated_web_account(self):
        settings = make_settings(sql_username="", sql_password="")
        with self.assertRaisesRegex(ConfigurationError, "riêng cho Backend"):
            build_connection_string(settings)

    def test_connection_string_escapes_odbc_values_and_enables_encryption(self):
        settings = make_settings(
            sql_server=r"SERVER\\INSTANCE",
            sql_username="web}service",
            sql_password="pass}word",
            sql_trust_server_certificate=False,
        )
        value = build_connection_string(settings)
        self.assertIn("SERVER={SERVER\\\\INSTANCE};", value)
        self.assertIn("UID={web}}service};", value)
        self.assertIn("PWD={pass}}word};", value)
        self.assertIn("Encrypt=yes;", value)
        self.assertIn("TrustServerCertificate=no;", value)

    def test_create_connection_uses_timeout_and_disables_autocommit(self):
        settings = make_settings()
        expected_connection = object()
        with patch("backend.database.pyodbc.connect", return_value=expected_connection) as connect:
            result = create_connection(settings)
        self.assertIs(result, expected_connection)
        self.assertEqual(connect.call_args.kwargs["timeout"], settings.sql_timeout_seconds)
        self.assertFalse(connect.call_args.kwargs["autocommit"])

    def test_create_connection_wraps_odbc_errors(self):
        import pyodbc

        with patch(
            "backend.database.pyodbc.connect",
            side_effect=pyodbc.Error("private connection detail"),
        ):
            with self.assertRaises(DatabaseUnavailableError):
                create_connection(make_settings())


class BackendHealthTests(unittest.TestCase):
    def test_liveness_does_not_require_sql_server(self):
        with patch.dict(os.environ, {}, clear=True):
            app = create_app()
            response = TestClient(app).get("/api/v1/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_queries_sql_server_and_closes_connection(self):
        app = create_app()
        connection = FakeConnection()

        def override_connection():
            yield connection

        app.dependency_overrides[get_db_connection] = override_connection
        try:
            response = TestClient(app).get("/api/v1/health/ready")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "database": "ok"})
        self.assertEqual(connection.fake_cursor.executed[0][0], "SELECT 1")
        self.assertTrue(connection.fake_cursor.closed)

    def test_database_dependency_rolls_back_and_closes_connection(self):
        env = {
            "BOOKHUB_WEB_SQL_SERVER": "localhost",
            "BOOKHUB_WEB_SQL_DATABASE": "CSDLTEST",
            "BOOKHUB_WEB_SQL_USERNAME": "bookhub_web",
            "BOOKHUB_WEB_SQL_PASSWORD": "test-secret",
        }
        connection = FakeConnection()
        with patch.dict(os.environ, env, clear=True):
            with patch("backend.dependencies.create_connection", return_value=connection):
                dependency = get_db_connection()
                yielded = next(dependency)
                self.assertIs(yielded, connection)
                with self.assertRaises(StopIteration):
                    next(dependency)

        self.assertTrue(connection.rollback_called)
        self.assertTrue(connection.closed)

    def test_cors_uses_configured_origins(self):
        with patch.dict(
            os.environ,
            {"BOOKHUB_WEB_ALLOWED_ORIGINS": "https://web.example.test"},
            clear=True,
        ):
            app = create_app()
        middleware = [
            item for item in app.user_middleware
            if item.cls.__name__ == "CORSMiddleware"
        ]
        self.assertEqual(len(middleware), 1)
        self.assertEqual(
            middleware[0].kwargs["allow_origins"],
            ["https://web.example.test"],
        )

    def test_readiness_returns_503_without_database_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            app = create_app()
            response = TestClient(app).get("/api/v1/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "Dịch vụ cơ sở dữ liệu hiện không khả dụng."},
        )

    def test_readiness_returns_503_when_database_query_fails(self):
        app = create_app()
        connection = FakeConnection(FakeCursor(error=RuntimeError("internal SQL detail")))

        def override_connection():
            yield connection

        app.dependency_overrides[get_db_connection] = override_connection
        try:
            response = TestClient(app).get("/api/v1/health/ready")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal SQL detail", response.text)
        self.assertTrue(connection.fake_cursor.closed)

    def test_security_headers_are_added(self):
        app = create_app()
        response = TestClient(app).get("/api/v1/health/live")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_docs_can_be_disabled(self):
        with patch.dict(
            os.environ,
            {"BOOKHUB_WEB_DOCS_ENABLED": "false"},
            clear=True,
        ):
            app = create_app()
        paths = app.openapi()["paths"]
        self.assertIn("/api/v1/health/live", paths)
        self.assertIsNone(app.docs_url)
        self.assertIsNone(app.redoc_url)


if __name__ == "__main__":
    unittest.main()
