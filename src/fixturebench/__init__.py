"""FixtureBench — deterministic eval for procurement browser agents."""

from fixturebench.api import run
from fixturebench.adapters import AgentRunResult, BrowserAgent, EvalTask
from fixturebench.eval import EvalRunner

__version__ = "0.6.0"

__all__ = [
    "AgentRunResult",
    "BrowserAgent",
    "EvalRunner",
    "EvalTask",
    "run",
    "__version__",
]
