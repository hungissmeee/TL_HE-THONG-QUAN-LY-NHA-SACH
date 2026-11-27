"""Kiểm thử Backend FastAPI và cấu hình SQL Server, không cần database thật."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import jwt
import pyodbc

from backend.config import ConfigurationError, Settings, load_settings
from backend.database import (
    AuthenticationRejectedError,
    DatabaseUnavailableError,
    build_connection_string,
    create_connection,
    create_employee_auth_connection,
)
from backend.authentication import authenticate_employee
from backend.security import CurrentUser, create_access_token, require_roles
from backend.dependencies import get_db_connection
from backend.main import create_app
from database.connection import Database

from run_backend import load_server_options


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
    def setUp(self):
        patcher = patch("backend.config.ENV_FILE", Path(".missing-test-env"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_settings_uses_web_namespace_and_safe_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.api_prefix, "/api/v1")
        self.assertFalse(settings.sql_trust_server_certificate)
        self.assertFalse(settings.database_configured)

    def test_load_settings_reads_root_dotenv_file_automatically(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "BOOKHUB_WEB_ENV=test\n"
                "BOOKHUB_WEB_SQL_SERVER=sql.example.local\n"
                "BOOKHUB_WEB_SQL_DATABASE=BOOKHUB_TEST\n"
                "BOOKHUB_WEB_SQL_USERNAME=web_user\n"
                "BOOKHUB_WEB_SQL_PASSWORD=local_secret\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch("backend.config.ENV_FILE", env_file):
                    settings = load_settings()

        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.sql_server, "sql.example.local")
        self.assertEqual(settings.sql_database, "BOOKHUB_TEST")
        self.assertEqual(settings.sql_username, "web_user")
        self.assertEqual(settings.sql_password, "local_secret")
        self.assertTrue(settings.database_configured)

    def test_existing_os_environment_values_override_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "BOOKHUB_WEB_ENV=development\\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"BOOKHUB_WEB_ENV": "production"}, clear=True
            ):
                with patch("backend.config.ENV_FILE", env_file):
                    settings = load_settings()

        self.assertEqual(settings.environment, "production")
        self.assertFalse(settings.docs_enabled)

    def test_desktop_database_reads_shared_root_dotenv_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "BOOKHUB_SQL_SERVER=desktop-sql\\INSTANCE\n"
                "BOOKHUB_SQL_DATABASE=BOOKHUB_DESKTOP\n"
                "BOOKHUB_SQL_DRIVER=ODBC Driver 18 for SQL Server\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch("database.connection.ENV_FILE", env_file):
                    database = Database()

        self.assertEqual(database.server, "desktop-sql\\INSTANCE")
        self.assertEqual(database.database, "BOOKHUB_DESKTOP")
        self.assertEqual(database.driver, "ODBC Driver 18 for SQL Server")

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
    def setUp(self):
        patcher = patch("backend.config.ENV_FILE", Path(".missing-test-env"))
        patcher.start()
        self.addCleanup(patcher.stop)

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



class BackendAuthenticationTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("backend.config.ENV_FILE", Path(".missing-auth-test-env"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.env = {
            "BOOKHUB_WEB_ENV": "test",
            "BOOKHUB_WEB_JWT_SECRET": "test-secret-that-is-long-enough-for-hs256",
        }

    def test_employee_authentication_reads_role_from_sql_server(self):
        # MANV, TENNV, VAITRO, SDT, admin, manager, cashier, warehouse, accounting
        row = ("NV001", "Nhân viên A", "Thu ngân", "0900000000", 0, 0, 1, 0, 0)
        connection = FakeConnection(FakeCursor(row=row))
        with patch(
            "backend.authentication.create_employee_auth_connection",
            return_value=connection,
        ):
            employee = authenticate_employee(
                make_settings(), "NV001", "employee-password"
            )

        self.assertEqual(employee.employee_code, "NV001")
        self.assertEqual(employee.role, "Thu ngân")
        self.assertEqual(employee.role_code, "rl_ThuNgan")
        self.assertTrue(connection.fake_cursor.closed)
        self.assertTrue(connection.rollback_called)
        self.assertTrue(connection.closed)

    def test_employee_authentication_rejects_employee_without_role(self):
        row = ("NV001", "Nhân viên A", "Thu ngân", "0900000000", 0, 0, 0, 0, 0)
        connection = FakeConnection(FakeCursor(row=row))
        with patch(
            "backend.authentication.create_employee_auth_connection",
            return_value=connection,
        ):
            with self.assertRaises(AuthenticationRejectedError):
                authenticate_employee(make_settings(), "NV001", "employee-password")
        self.assertTrue(connection.closed)

    def test_employee_authentication_rejects_missing_employee_profile(self):
        connection = FakeConnection(FakeCursor(row=None))
        with patch(
            "backend.authentication.create_employee_auth_connection",
            return_value=connection,
        ):
            with self.assertRaises(AuthenticationRejectedError):
                authenticate_employee(make_settings(), "unknown", "password")

    def test_employee_auth_connection_uses_submitted_credentials(self):
        settings = make_settings()
        expected = object()
        with patch(
            "backend.database.pyodbc.connect", return_value=expected
        ) as connect:
            result = create_employee_auth_connection(settings, "NV001", "employee-secret")
        self.assertIs(result, expected)
        connection_string = connect.call_args.args[0]
        self.assertIn("UID={NV001};", connection_string)
        self.assertIn("PWD={employee-secret};", connection_string)
        self.assertFalse(connect.call_args.kwargs["autocommit"])

    def test_employee_auth_connection_maps_sql_login_rejection(self):
        with patch(
            "backend.database.pyodbc.connect",
            side_effect=pyodbc.Error("28000", "Login failed (18456)"),
        ):
            with self.assertRaises(AuthenticationRejectedError):
                create_employee_auth_connection(make_settings(), "NV001", "wrong")

    def test_employee_auth_connection_maps_non_auth_odbc_errors_to_503_type(self):
        with patch(
            "backend.database.pyodbc.connect",
            side_effect=pyodbc.Error("08001", "SQL Server is unavailable"),
        ):
            with self.assertRaises(DatabaseUnavailableError):
                create_employee_auth_connection(make_settings(), "NV001", "password")

    def test_access_token_contains_employee_identity_and_expiration(self):
        user = CurrentUser(
            employee_code="NV001",
            full_name="Nhân viên A",
            role="Thu ngân",
            role_code="rl_ThuNgan",
        )
        with patch.dict(os.environ, self.env, clear=True):
            token, expires_in = create_access_token(user)
            payload = jwt.decode(
                token,
                self.env["BOOKHUB_WEB_JWT_SECRET"],
                algorithms=["HS256"],
                audience="bookhub-web",
                issuer="bookhub-api",
            )
        self.assertEqual(expires_in, 1800)
        self.assertEqual(payload["sub"], "NV001")
        self.assertEqual(payload["role_code"], "rl_ThuNgan")

    def test_login_returns_access_token_and_me_accepts_it(self):
        from backend.authentication import AuthenticatedEmployee

        employee = AuthenticatedEmployee(
            employee_code="NV001",
            full_name="Nhân viên A",
            role="Thu ngân",
            role_code="rl_ThuNgan",
            phone="0900000000",
        )
        app = create_app()
        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "backend.api.routes.auth.authenticate_employee",
                return_value=employee,
            ):
                client = TestClient(app)
                response = client.post(
                    "/api/v1/auth/login",
                    json={"username": "NV001", "password": "employee-password"},
                )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["user"]["employee_code"], "NV001")
            self.assertEqual(data["user"]["role_code"], "rl_ThuNgan")
            self.assertEqual(data["token_type"], "bearer")
            me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["employee_code"], "NV001")
        self.assertEqual(me.json()["role"], "Thu ngân")


    def test_role_dependency_allows_configured_role(self):
        checker = require_roles("rl_ThuNgan")
        user = CurrentUser(
            employee_code="NV001",
            full_name="Thu ngân A",
            role="Thu ngân",
            role_code="rl_ThuNgan",
        )
        self.assertIs(checker(user), user)

    def test_role_dependency_rejects_other_roles(self):
        from fastapi import HTTPException

        checker = require_roles("rl_QuanLy")
        user = CurrentUser(
            employee_code="NV001",
            full_name="Thu ngân A",
            role="Thu ngân",
            role_code="rl_ThuNgan",
        )
        with self.assertRaises(HTTPException) as context:
            checker(user)
        self.assertEqual(context.exception.status_code, 403)

    def test_admin_bypasses_role_specific_dependency(self):
        checker = require_roles("rl_ThuNgan")
        admin = CurrentUser(
            employee_code="admin",
            full_name="Quản trị viên",
            role="Quản trị hệ thống",
            role_code="admin",
        )
        self.assertIs(checker(admin), admin)

    def test_login_returns_401_for_rejected_credentials(self):
        app = create_app()
        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "backend.api.routes.auth.authenticate_employee",
                side_effect=AuthenticationRejectedError("private SQL detail"),
            ):
                response = TestClient(app).post(
                    "/api/v1/auth/login",
                    json={"username": "NV001", "password": "wrong"},
                )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("private SQL detail", response.text)

    def test_login_returns_503_when_jwt_secret_is_missing(self):
        from backend.authentication import AuthenticatedEmployee

        employee = AuthenticatedEmployee(
            employee_code="NV001",
            full_name="Nhân viên A",
            role="Thu ngân",
            role_code="rl_ThuNgan",
            phone=None,
        )
        app = create_app()
        with patch.dict(os.environ, {"BOOKHUB_WEB_ENV": "test"}, clear=True):
            with patch(
                "backend.api.routes.auth.authenticate_employee",
                return_value=employee,
            ):
                response = TestClient(app).post(
                    "/api/v1/auth/login",
                    json={"username": "NV001", "password": "correct"},
                )
        self.assertEqual(response.status_code, 503)

    def test_me_requires_bearer_token(self):
        with patch.dict(os.environ, self.env, clear=True):
            response = TestClient(create_app()).get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_rejects_invalid_token_signature(self):
        with patch.dict(os.environ, self.env, clear=True):
            response = TestClient(create_app()).get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer not.a.valid.jwt"},
            )
        self.assertEqual(response.status_code, 401)



class BackendLauncherTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("backend.config.ENV_FILE", Path(".missing-launcher-test-env"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_launcher_has_development_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            options = load_server_options()
        self.assertEqual(options.host, "127.0.0.1")
        self.assertEqual(options.port, 8000)
        self.assertTrue(options.reload)
        self.assertEqual(options.log_level, "info")

    def test_launcher_reads_host_port_reload_and_log_level(self):
        env = {
            "BOOKHUB_WEB_HOST": "0.0.0.0",
            "BOOKHUB_WEB_PORT": "9000",
            "BOOKHUB_WEB_RELOAD": "false",
            "BOOKHUB_WEB_LOG_LEVEL": "warning",
        }
        with patch.dict(os.environ, env, clear=True):
            options = load_server_options()
        self.assertEqual(options.host, "0.0.0.0")
        self.assertEqual(options.port, 9000)
        self.assertFalse(options.reload)
        self.assertEqual(options.log_level, "warning")

    def test_launcher_rejects_invalid_port(self):
        with patch.dict(os.environ, {"BOOKHUB_WEB_PORT": "70000"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "1–65535"):
                load_server_options()

    def test_launcher_rejects_empty_host(self):
        with patch.dict(os.environ, {"BOOKHUB_WEB_HOST": " "}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "không được để trống"):
                load_server_options()

    def test_launcher_rejects_reload_in_production(self):
        env = {
            "BOOKHUB_WEB_ENV": "production",
            "BOOKHUB_WEB_RELOAD": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "production"):
                load_server_options()

    def test_launcher_rejects_invalid_log_level(self):
        with patch.dict(os.environ, {"BOOKHUB_WEB_LOG_LEVEL": "verbose"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "LOG_LEVEL"):
                load_server_options()



if __name__ == "__main__":
    unittest.main()
