from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fixturebench.eval.models import PortalVersion

PORTAL_SPECS: dict[PortalVersion, dict[str, object]] = {
    "v1": {"server": "portals/v1/server.py", "default_port": 8000},
    "v2": {"server": "portals/v2/server.py", "default_port": 8001},
    "v3": {"server": "portals/v3/server.py", "default_port": 8002},
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError(f"Portal server did not start at {url}")


@dataclass
class ManagedPortal:
    """Lifecycle wrapper for local fake buyer portal servers."""

    version: PortalVersion
    root: Path
    port: Optional[int] = None

    _proc: Optional[subprocess.Popen] = None
    _url: Optional[str] = None

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

        self._proc = subprocess.Popen(
            [sys.executable, str(server_path), "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(self.root),
        )
        wait_for_server(f"{base}/login")
        self._url = base
        return self.url

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        self._proc.wait(timeout=5)
        self._proc = None
        self._url = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
