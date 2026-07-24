from __future__ import annotations

from pathlib import Path

from fixturebench.adapters.protocol import AgentRunResult, EvalTask
from fixturebench.models.po import RawPurchaseOrder
from fixturebench.paths import checkout_root, default_root, discover_root


def test_default_root_finds_checkout() -> None:
    root = default_root()
    assert (root / "eval" / "cases.json").is_file()
    assert (root / "portals" / "v1" / "server.py").is_file()


def test_checkout_root_from_package() -> None:
    root = checkout_root()
    assert root is not None
    assert _looks_ok(root)


def test_discover_root_ignores_scruffy_like_layout(tmp_path: Path) -> None:
    """A checkout with portals/ + eval/ but no FixtureBench identity must not win."""
    decoy = tmp_path / "scruffy-like"
    (decoy / "eval").mkdir(parents=True)
    (decoy / "portals").mkdir()
    (decoy / "eval" / "cases.json").write_text("{}", encoding="utf-8")
    (decoy / "pyproject.toml").write_text('name = "scruffy"\n', encoding="utf-8")

    root = discover_root(decoy)
    assert root != decoy
    assert (root / "src" / "fixturebench").is_dir() or (
        root / "portals" / "_shared" / "templating.py"
    ).is_file()


def test_fixturebench_root_env_override(tmp_path: Path, monkeypatch) -> None:
    import os

    real = checkout_root()
    assert real is not None
    monkeypatch.setenv("FIXTUREBENCH_ROOT", str(real))
    assert discover_root(tmp_path) == real.resolve()
    monkeypatch.delenv("FIXTUREBENCH_ROOT", raising=False)
    os.environ.pop("FIXTUREBENCH_ROOT", None)


def test_eval_task_aliases() -> None:
    task = EvalTask(
        case_id="x",
        portal_url="http://127.0.0.1:8000",
        goal="do the thing",
        po_number="PO-1042",
        email="a@b.c",
        password="pw",
    )
    assert task.url == "http://127.0.0.1:8000"
    assert task.target_id == "PO-1042"


def test_agent_result_payload_alias() -> None:
    po = RawPurchaseOrder(po_number="PO-1042", lines=[])
    result = AgentRunResult(success=True, payload=po)
    assert result.po is not None
    assert result.po.po_number == "PO-1042"
    assert result.payload is not None


def test_cli_list_smoke() -> None:
    from fixturebench.cli import main

    assert main(["list"]) == 0


def _looks_ok(root: Path) -> bool:
    return (root / "eval" / "cases.json").is_file() and (root / "portals").is_dir()
