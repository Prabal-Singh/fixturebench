"""High-level plug-and-play API."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from fixturebench.adapters.protocol import BrowserAgent
from fixturebench.eval.models import EvalReport
from fixturebench.eval.runner import EvalRunner
from fixturebench.paths import default_root


def run(
    agent: BrowserAgent,
    *,
    root: Optional[Path] = None,
    case_ids: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
    headless: bool = True,
    write_results: bool = True,
    output_dir: Optional[Path] = None,
) -> EvalReport:
    """Evaluate ``agent`` against the default environment pack.

    Example::

        from fixturebench import run
        from my_agent import MyAgent

        report = run(MyAgent(), tags=["smoke"])
        print(report.summary.pass_rate)
    """
    data_root = root or default_root()
    runner = EvalRunner(
        agent,
        root=data_root,
        output_dir=output_dir or (Path.cwd() / "eval-results"),
    )
    return runner.run(
        case_ids=case_ids,
        tags=tags,
        headless=headless,
        write_results=write_results,
    )
