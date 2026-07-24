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
}

PORTAL_CHALLENGES: dict[PortalVersion, str] = {
    version: str(spec["challenge"]) for version, spec in PORTAL_SPECS.items()
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
