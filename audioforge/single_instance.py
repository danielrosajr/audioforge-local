"""Linux single-instance launcher with a loopback-only control channel.

Lock is per user, not per terminal or port. A second click NEVER starts another
Gradio server: it verifies a random local control token and opens the existing
interface instead. This module uses only the Python standard library.
"""
from __future__ import annotations

import fcntl
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "audioforge-local"
LOCK_FILE = CACHE_DIR / "instance.lock"
INFO_FILE = CACHE_DIR / "instance.json"


def app_port() -> int:
    try:
        port = int(os.environ.get("AUDIOFORGE_PORT", "7860"))
        if not 1 <= port <= 65535:
            raise ValueError()
        return port
    except ValueError as exc:
        raise RuntimeError("AUDIOFORGE_PORT precisa ser uma porta válida (1–65535).") from exc


def _url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def _notify_problem(message: str) -> None:
    print("AudioForge: " + message, file=sys.stderr, flush=True)
    # Ao abrir pelo menu, o log pode estar escondido. Mostrar uma notificação.
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            subprocess.Popen(["notify-send", "AudioForge Local", message],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def _write_info(info: dict) -> None:
    CACHE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = INFO_FILE.with_name(f"{INFO_FILE.name}.{os.getpid()}.tmp")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(info, file, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, INFO_FILE)
    finally:
        tmp.unlink(missing_ok=True)


def _read_info() -> dict | None:
    try:
        return json.loads(INFO_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _status(info: dict) -> dict | None:
    """Do not trust a stale port number: require the per-process secret."""
    try:
        port = int(info["control_port"])
        token = str(info["token"])
        with urllib.request.urlopen(
            f"{_url(port)}/status?{urllib.parse.urlencode({'token': token})}",
            timeout=0.65,
        ) as response:
            if response.status != 200:
                return None
            state = json.loads(response.read(2048))
            if state.get("token") == token and state.get("pid") == info.get("pid"):
                return state
    except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
        pass
    return None


def _wait_for_running_instance(timeout: float = 75.0) -> str | None:
    """Handles two launcher clicks while the first is still loading Gradio."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = _read_info()
        if info:
            status = _status(info)
            if status and status.get("ready") and status.get("url") == info.get("url"):
                return str(status["url"])
        time.sleep(0.35)
    return None


def _port_is_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


class _ControlServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, token: str, url: str, ready: threading.Event):
        self.token = token
        self.target_url = url
        self.ready = ready
        super().__init__(("127.0.0.1", 0), _ControlHandler)


class _ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        control: _ControlServer = self.server  # type: ignore[assignment]
        parsed = urllib.parse.urlsplit(self.path)
        token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
        if parsed.path != "/status" or not secrets.compare_digest(token, control.token):
            self.send_error(404)
            return
        body = json.dumps({"token": control.token, "pid": os.getpid(),
                           "ready": control.ready.is_set(), "url": control.target_url}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


def _open_existing(url: str) -> None:
    print(f"AudioForge já está aberto. Reutilizando {url}", flush=True)
    try:
        if not webbrowser.open(url, new=2):
            _notify_problem(f"O app já está aberto: acesse {url} no navegador.")
    except Exception:
        _notify_problem(f"O app já está aberto: acesse {url} no navegador.")


def run_single_instance(start: Callable[[Callable[[], None]], None]) -> int:
    """Call start(mark_ready) in the one elected process; subsequent starts reopen it.

    start should launch Gradio with prevent_thread_lock=True and then return.
    The launcher holds the lock until shutdown, even though Gradio uses threads.
    """
    CACHE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    with LOCK_FILE.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            url = _wait_for_running_instance()
            if url:
                _open_existing(url)
                return 0
            _notify_problem("Existe outra inicialização em andamento, mas não respondeu. Verifique o log em ~/.cache/audioforge-local/launcher.log")
            return 2

        port = app_port()
        url = _url(port)
        if not _port_is_free(port):
            _notify_problem(f"A porta {port} está ocupada por outra execução (possivelmente v0.2.0). Encerre-a e tente novamente. Comando: ss -ltnp | grep ':{port}'")
            return 3

        token = secrets.token_urlsafe(32)
        ready = threading.Event()
        control = _ControlServer(token, url, ready)
        control_thread = threading.Thread(target=control.serve_forever, daemon=True)
        control_thread.start()
        info = {"pid": os.getpid(), "url": url, "control_port": control.server_port, "token": token}
        _write_info(info)
        previous_sigterm = signal.getsignal(signal.SIGTERM)

        def sigterm_handler(_signum, _frame) -> None:
            raise SystemExit(0)

        # The 'Encerrar' button sends SIGTERM; ensure finally can remove status.
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, sigterm_handler)
        try:
            start(ready.set)
            # Prevent closing the main Python process when Gradio launch returns.
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0
        finally:
            ready.clear()
            control.shutdown()
            control.server_close()
            control_thread.join(timeout=2)
            if _read_info() == info:
                INFO_FILE.unlink(missing_ok=True)
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM, previous_sigterm)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
