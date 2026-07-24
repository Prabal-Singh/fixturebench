from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fixturebench.eval.models import PortalVersion

PORTAL_SPECS: dict[PortalVersion, dict[str, object]] = {
    "v1": {
        "server": "portals/v1/server.py",
        "default_port": 8000,
        "challenge": "baseline",
    },
    "v2": {
        "server": "portals/v2/server.py",
        "default_port": 8001,
        "challenge": "messy-headers",
    },
    "v3": {
        "server": "portals/v3/server.py",
        "default_port": 8002,
        "challenge": "pagination",
    },
    "v4": {
        "server": "portals/v4/server.py",
        "default_port": 8003,
        "challenge": "csv-export",
    },
    "v5": {
        "server": "portals/v5/server.py",
        "default_port": 8004,
        "challenge": "tab-navigation",
    },
    "v6": {
        "server": "portals/v6/server.py",
        "default_port": 8005,
        "challenge": "accordion-lines",
    },
    "v7": {
        "server": "portals/v7/server.py",
        "default_port": 8006,
        "challenge": "session-expiry",
    },
    "v8": {
        "server": "portals/v8/server.py",
        "default_port": 8007,
        "challenge": "modal-detail",
    },
    "v9": {
        "server": "portals/v9/server.py",
        "default_port": 8008,
        "challenge": "messy-dom",
    },
    "v10": {
        "server": "portals/v10/server.py",
        "default_port": 8009,
        "challenge": "search-filter",
    },
    "v11": {
        "server": "portals/v11/server.py",
        "default_port": 8010,
        "challenge": "iframe-detail",
    },
    "v12": {
        "server": "portals/v12/server.py",
        "default_port": 8011,
        "challenge": "delayed-load",
    },
    "v13": {
        "server": "portals/v13/server.py",
        "default_port": 8012,
        "challenge": "empty-orders",
    },
    "v14": {
        "server": "portals/v14/server.py",
        "default_port": 8013,
        "challenge": "lazy-accordion",
    },
    "v15": {
        "server": "portals/v15/server.py",
        "default_port": 8014,
        "challenge": "unlabeled-fields",
    },
    "v16": {
        "server": "portals/v16/server.py",
        "default_port": 8015,
        "challenge": "nested-export-menu",
    },
    "v17": {
        "server": "portals/v17/server.py",
        "default_port": 8016,
        "challenge": "decoy-rows",
    },
    "v18": {
        "server": "portals/v18/server.py",
        "default_port": 8017,
        "challenge": "antibot-interstitial",
    },
    "v19": {
        "server": "portals/v19/server.py",
        "default_port": 8018,
        "challenge": "acknowledge-writeback",
    },
    "v20": {
        "server": "portals/v20/server.py",
        "default_port": 8019,
        "challenge": "mfa-handoff",
    },
    "v21": {
        "server": "portals/v21/server.py",
        "default_port": 8020,
        "challenge": "virtualized-grid",
    },
    "v22": {
        "server": "portals/v22/server.py",
        "default_port": 8021,
        "challenge": "multi-buyer-ambiguity",
    },
    "v23": {
        "server": "portals/v23/server.py",
        "default_port": 8022,
        "challenge": "stale-cache",
    },
}

PORTAL_CHALLENGES: dict[PortalVersion, str] = {
    version: str(spec["challenge"]) for version, spec in PORTAL_SPECS.items()
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(
    url: str,
    timeout: float = 30.0,
    *,
    proc: Optional[subprocess.Popen] = None,
    stderr_path: Optional[Path] = None,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            detail = _read_stderr(stderr_path)
            raise RuntimeError(
                f"Portal process exited with code {proc.returncode} before becoming ready at {url}."
                f"{detail}"
            )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(0.1)
    detail = _read_stderr(stderr_path)
    raise RuntimeError(f"Portal server did not start at {url}.{detail}")


def _read_stderr(stderr_path: Optional[Path]) -> str:
    if stderr_path is None or not stderr_path.is_file():
        return ""
    text = stderr_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""
    # Keep failure messages readable in CI logs.
    clipped = text[-2000:]
    return f"\n--- portal stderr ---\n{clipped}\n--- end stderr ---"


@dataclass
class ManagedPortal:
    """Lifecycle wrapper for local fake buyer portal servers."""

    version: PortalVersion
    root: Path
    port: Optional[int] = None

    _proc: Optional[subprocess.Popen] = None
    _url: Optional[str] = None
    _stderr_path: Optional[Path] = None

    @property
    def url(self) -> str:
        if self._url is None:
            raise RuntimeError("Portal has not been started")
        return self._url

    def start(self) -> str:
        if self._proc is not None:
            return self.url

        spec = PORTAL_SPECS[self.version]
        port = self.port or free_port()
        base = f"http://127.0.0.1:{port}"
        server_path = self.root / str(spec["server"])
        if not server_path.is_file():
            raise FileNotFoundError(f"Portal server not found: {server_path}")

        stderr_file = tempfile.NamedTemporaryFile(
            prefix=f"fixturebench-{self.version}-",
            suffix=".stderr",
            delete=False,
        )
        self._stderr_path = Path(stderr_file.name)

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._proc = subprocess.Popen(
            [
                sys.executable,
                str(server_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            cwd=str(self.root),
            env=env,
        )
        stderr_file.close()
        try:
            wait_for_server(
                f"{base}/login",
                timeout=30.0,
                proc=self._proc,
                stderr_path=self._stderr_path,
            )
        except Exception:
            self.stop()
            raise
        self._url = base
        return self.url

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)
            self._proc = None
        self._url = None
        if self._stderr_path is not None:
            try:
                self._stderr_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._stderr_path = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
