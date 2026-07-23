"""Locate FixtureBench data (environments, cases, fixtures)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def _looks_like_root(path: Path) -> bool:
    return (path / "eval" / "cases.json").is_file() and (path / "portals").is_dir()


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
    return None


def discover_root(start: Path | None = None) -> Path:
    """Find a FixtureBench data root.

    Order:
    1. Walk parents of ``start`` (default: cwd)
    2. Source checkout adjacent to this package
    3. Packaged wheel bundle
    """
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if _looks_like_root(candidate):
            return candidate

    checked_out = checkout_root()
    if checked_out is not None:
        return checked_out

    bundled = package_bundle_root()
    if bundled is not None:
        return bundled

    raise FileNotFoundError(
        "Could not find FixtureBench data root. "
        "Run from a FixtureBench checkout, or install with environments: "
        "pip install 'fixturebench[envs]'."
    )


def default_root() -> Path:
    """Convenience alias used by the CLI and high-level API."""
    return discover_root()
