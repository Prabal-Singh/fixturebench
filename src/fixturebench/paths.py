"""Locate FixtureBench data (environments, cases, fixtures)."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path


def _looks_like_root(path: Path) -> bool:
    """True for a FixtureBench data root — not Scruffy or other portal checkouts."""
    if not (path / "eval" / "cases.json").is_file():
        return False
    if not (path / "portals").is_dir():
        return False
    # Prefer an explicit FixtureBench identity so sibling products (e.g. Scruffy)
    # that also ship portals/ + eval/ are not mistaken for this suite.
    if (path / "src" / "fixturebench").is_dir():
        return True
    if (path / "portals" / "_shared" / "templating.py").is_file():
        return True
    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            return False
        if 'name = "fixturebench"' in text or "name = 'fixturebench'" in text:
            return True
    return False


def checkout_root() -> Path | None:
    """Repo root when running from a source checkout / editable install."""
    pkg_dir = Path(__file__).resolve().parent
    for candidate in pkg_dir.parents:
        if _looks_like_root(candidate):
            return candidate
    return None


def package_bundle_root() -> Path | None:
    """Packaged wheel bundle (``fixturebench/bundle``), if present."""
    try:
        base = resources.files("fixturebench")
        bundle = Path(str(base.joinpath("bundle")))
    except (TypeError, FileNotFoundError, ModuleNotFoundError, AttributeError):
        return None
    if _looks_like_root(bundle):
        return bundle
    # Bundled trees may omit src/fixturebench; accept portals + cases alone.
    if (bundle / "eval" / "cases.json").is_file() and (bundle / "portals").is_dir():
        return bundle
    return None


def discover_root(start: Path | None = None) -> Path:
    """Find a FixtureBench data root.

    Order:
    1. ``FIXTUREBENCH_ROOT`` env (if set)
    2. Source checkout adjacent to this package
    3. Packaged wheel bundle
    4. Walk parents of ``start`` (default: cwd)
    """
    env = os.environ.get("FIXTUREBENCH_ROOT")
    if env:
        path = Path(env).expanduser().resolve()
        if _looks_like_root(path) or (
            (path / "eval" / "cases.json").is_file() and (path / "portals").is_dir()
        ):
            return path
        raise FileNotFoundError(
            f"FIXTUREBENCH_ROOT={env!r} does not look like a FixtureBench data root"
        )

    checked_out = checkout_root()
    if checked_out is not None:
        return checked_out

    bundled = package_bundle_root()
    if bundled is not None:
        return bundled

    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if _looks_like_root(candidate):
            return candidate

    raise FileNotFoundError(
        "Could not find FixtureBench data root. "
        "Run from a FixtureBench checkout, set FIXTUREBENCH_ROOT, or install with "
        "environments: pip install 'fixturebench[envs]'."
    )


def default_root() -> Path:
    """Convenience alias used by the CLI and high-level API."""
    return discover_root()
