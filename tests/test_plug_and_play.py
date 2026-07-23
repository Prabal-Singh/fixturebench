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


def test_discover_root_from_tmp(tmp_path: Path) -> None:
    # Even from an unrelated cwd, package checkout should resolve.
    root = discover_root(tmp_path)
    assert _looks_ok(root)


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
