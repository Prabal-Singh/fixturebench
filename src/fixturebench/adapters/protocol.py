from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fixturebench.models.po import RawPurchaseOrder


class EvalTask(BaseModel):
    """Inputs passed to a browser agent for one eval case."""

    case_id: str
    portal_url: str
    goal: str
    po_number: str
    max_steps: int = 12
    headless: bool = True
    email: str
    password: str
    screenshot_dir: Optional[Path] = None
    trace_dir: Optional[Path] = None


class AgentRunResult(BaseModel):
    """Minimal terminal outcome any browser agent should return."""

    success: bool
    po: Optional[RawPurchaseOrder] = None
    failure_reason: Optional[str] = None
    total_duration_ms: Optional[float] = None
    step_count: int = 0
    llm_duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BrowserAgent(Protocol):
    """Plug-in interface for any browser agent implementation."""

    @property
    def name(self) -> str:
        ...

    def run(self, task: EvalTask) -> AgentRunResult:
        ...
