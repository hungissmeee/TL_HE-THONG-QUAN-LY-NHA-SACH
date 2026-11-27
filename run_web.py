"""Khởi động cả BookHub FastAPI Backend và React/Vite Frontend cùng lúc.

Chạy từ thư mục gốc dự án:
    python run_web.py

File này tự kiểm tra Node.js/npm, cài dependencies frontend nếu chưa có,
khởi động Backend + Frontend và dừng cả hai khi nhấn Ctrl+C.
"""

import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from dotenv import load_dotenv

from backend.config import ConfigurationError, ENV_FILE
from run_backend import load_server_options


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


@dataclass(frozen=True)
class FrontendOptions:
    host: str
    port: int


@dataclass(frozen=True)
class NpmRuntime:
    """Lệnh chạy npm bằng Node trực tiếp, không qua npm.cmd/cmd.exe."""

    command_prefix: tuple[str, ...]


@dataclass
class RunningProcess:
    name: str
    process: subprocess.Popen


def _read_port(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} phải là số nguyên.") from exc
    if not 1 <= port <= 65535:
        raise ConfigurationError(f"{name} phải nằm trong khoảng 1–65535.")
    return port


def load_frontend_options() -> FrontendOptions:
    """Đọc host/port của Vite từ file .env ở thư mục gốc."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)

    host = os.getenv("BOOKHUB_WEB_FRONTEND_HOST", "127.0.0.1").strip()
    if not host:
        raise ConfigurationError("BOOKHUB_WEB_FRONTEND_HOST không được để trống.")

    return FrontendOptions(
        host=host,
        port=_read_port("BOOKHUB_WEB_FRONTEND_PORT", 5173),
    )


def _find_npm() -> NpmRuntime:
    """Tìm Node.js và npm-cli.js; Windows không gọi npm.cmd qua cmd.exe."""
    node_path = shutil.which("node.exe" if os.name == "nt" else "node")
    if not node_path:
        node_path = shutil.which("node")
    if not node_path:
        raise SystemExit(
            "[BookHub] Không tìm thấy Node.js. Hãy cài Node.js bản LTS rồi mở Terminal mới."
        )

    if os.name != "nt":
        npm_path = shutil.which("npm")
        if not npm_path:
            raise SystemExit(
                "[BookHub] Không tìm thấy npm. Hãy kiểm tra lại cài đặt Node.js."
            )
        return NpmRuntime((npm_path,))

    npm_path = shutil.which("npm.cmd") or shutil.which("npm")
    search_directories = [Path(node_path).resolve().parent]
    if npm_path:
        search_directories.append(Path(npm_path).resolve().parent)

    # Bản cài Node.js chính thức đặt npm CLI trong node_modules/npm/bin.
    checked = set()
    for directory in search_directories:
        candidate = directory / "node_modules" / "npm" / "bin" / "npm-cli.js"
        normalized = str(candidate).casefold()
        if normalized in checked:
            continue
        checked.add(normalized)
        if candidate.is_file():
            return NpmRuntime((node_path, str(candidate)))

    raise SystemExit(
        "[BookHub] Tìm thấy Node.js nhưng không tìm thấy npm-cli.js. "
        "Hãy cài lại Node.js bản LTS từ nodejs.org (chọn cài kèm npm), "
        "sau đó mở Terminal mới."
    )


def _npm_command(npm_runtime: NpmRuntime, arguments: list[str]) -> list[str]:
    """Tạo argv chạy npm-cli.js bằng node.exe; an toàn với đường dẫn có dấu cách."""
    return [*npm_runtime.command_prefix, *arguments]


def _ensure_frontend_dependencies(npm_runtime: NpmRuntime) -> None:
    """Tự cài dependencies khi người dùng chưa chạy npm install."""
    package_file = FRONTEND_DIR / "package.json"
    vite_bins = (
        FRONTEND_DIR / "node_modules" / ".bin" / "vite",
        FRONTEND_DIR / "node_modules" / ".bin" / "vite.cmd",
    )
    if not package_file.is_file():
        raise SystemExit("[BookHub] Không tìm thấy frontend/package.json.")
    if any(path.is_file() for path in vite_bins):
        return

    print("[BookHub] Chưa có thư viện Frontend. Đang chạy npm install...", flush=True)
    result = subprocess.run(
        _npm_command(npm_runtime, ["install", "--no-audit", "--no-fund"]),
        cwd=FRONTEND_DIR,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "[BookHub] Cài dependencies frontend thất bại. "
            "Kiểm tra kết nối Internet và thử lại."
        )
    if not any(path.is_file() for path in vite_bins):
        raise SystemExit("[BookHub] Không tìm thấy Vite sau khi cài dependencies.")


def _start_process(
    name: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
) -> RunningProcess:
    """Khởi chạy tiến trình trong process group riêng để dễ dừng cả cây tiến trình."""
    kwargs = {
        "cwd": str(cwd),
        "env": env,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **kwargs)
    return RunningProcess(name=name, process=process)


def _stop_process(running: RunningProcess) -> None:
    """Dừng tiến trình và tiến trình con, kể cả Vite/Uvicorn reload worker."""
    process = running.process
    if process.poll() is not None:
        return

    print(f"[BookHub] Đang dừng {running.name}...", flush=True)
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass

    try:
        process.wait(timeout=6)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        print(f"[BookHub] Cảnh báo: chưa dừng được {running.name}.", flush=True)


def _check_python_dependencies() -> None:
    missing = [
        name for name in ("uvicorn", "fastapi", "pyodbc", "dotenv", "jwt")
        if find_spec(name) is None
    ]
    if missing:
        raise SystemExit(
            "[BookHub] Thiếu thư viện Python: "
            + ", ".join(missing)
            + ". Hãy cài một lần bằng: python -m pip install -r requirements.txt"
        )


def main() -> int:
    try:
        backend_options = load_server_options()
        frontend_options = load_frontend_options()
    except ConfigurationError as exc:
        print(f"[BookHub] Cấu hình .env không hợp lệ: {exc}", file=sys.stderr)
        return 2

    if not FRONTEND_DIR.is_dir():
        print("[BookHub] Không tìm thấy thư mục frontend.", file=sys.stderr)
        return 2
    if backend_options.port == frontend_options.port:
        print("[BookHub] Port Backend và Frontend không được trùng nhau.", file=sys.stderr)
        return 2

    try:
        _check_python_dependencies()
        npm_runtime = _find_npm()
        _ensure_frontend_dependencies(npm_runtime)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    backend_url_host = "127.0.0.1" if backend_options.host in {"0.0.0.0", "::"} else backend_options.host
    frontend_url_host = "127.0.0.1" if frontend_options.host in {"0.0.0.0", "::"} else frontend_options.host

    print()
    print("=" * 58)
    print(" BOOKHUB WEB")
    print("=" * 58)
    print(f" Frontend : http://{frontend_url_host}:{frontend_options.port}")
    print(f" Backend  : http://{backend_url_host}:{backend_options.port}")
    print(f" API docs : http://{backend_url_host}:{backend_options.port}/docs")
    print("=" * 58)
    print(" Nhấn Ctrl+C để dừng cả Frontend và Backend.")
    print()

    env = os.environ.copy()
    processes: list[RunningProcess] = []

    try:
        backend = _start_process(
            "Backend",
            [sys.executable, str(PROJECT_ROOT / "run_backend.py")],
            PROJECT_ROOT,
            env,
        )
        processes.append(backend)

        frontend = _start_process(
            "Frontend",
            _npm_command(
                npm_runtime,
                [
                    "run", "dev", "--",
                    "--host", frontend_options.host,
                    "--port", str(frontend_options.port),
                    "--strictPort",
                ],
            ),
            FRONTEND_DIR,
            env,
        )
        processes.append(frontend)

        while True:
            for running in processes:
                return_code = running.process.poll()
                if return_code is not None:
                    print(
                        f"[BookHub] {running.name} đã dừng (exit code {return_code}).",
                        file=sys.stderr,
                        flush=True,
                    )
                    return return_code or 0
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[BookHub] Nhận Ctrl+C.", flush=True)
        return 0
    except OSError as exc:
        print(f"[BookHub] Không thể khởi động dịch vụ: {exc}", file=sys.stderr)
        return 1
    finally:
        for running in reversed(processes):
            _stop_process(running)
        print("[BookHub] Đã kết thúc.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
