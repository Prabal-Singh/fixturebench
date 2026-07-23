from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fixturebench.eval.models import EvalReport


def write_report(report: EvalReport, output_dir: Path) -> Path:
    """Persist a full eval report and a compact summary JSON."""
    run_dir = output_dir / report.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report_path = run_dir / "report.json"
    summary_path = run_dir / "summary.json"

    report_json = report.model_dump(mode="json")
    report_path.write_text(json.dumps(report_json, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "run_id": report_json["run_id"],
                "started_at": report_json["started_at"],
                "finished_at": report_json["finished_at"],
                "agent_name": report_json["agent_name"],
                "agent_metadata": report_json["agent_metadata"],
                "summary": report_json["summary"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path


def new_run_id(started_at: datetime) -> str:
    return started_at.strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
