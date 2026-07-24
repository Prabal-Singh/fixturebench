from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

PortalVersion = Literal[
    "v1",
    "v2",
    "v3",
    "v4",
    "v5",
    "v6",
    "v7",
    "v8",
    "v9",
    "v10",
    "v11",
    "v12",
    "v13",
    "v14",
    "v15",
    "v16",
    "v17",
    "v18",
    "v19",
    "v20",
    "v21",
]
CaseOutcome = Literal["extract_po", "confirm_empty", "acknowledge_po"]


class EvalDefaults(BaseModel):
    """Shared settings applied to eval cases unless overridden."""

    max_steps: int = 12
    headless: bool = True
    email: str = "vendor@fixturebench.test"
    password: str = "fixturebench123"
    goal_template: str = (
        "Log into the buyer portal using email {email} and password {password}. "
        "Open purchase order {po_number} and finish when the PO line items are visible."
    )


class EvalCase(BaseModel):
    """One agent eval scenario."""

    id: str
    portal: PortalVersion
    po_number: str = ""
    outcome: CaseOutcome = "extract_po"
    expected_fixture: str = ""
    expected_state: str = ""
    tags: List[str] = Field(default_factory=list)
    portal_url: Optional[str] = None
    manage_portal: bool = True
    goal: Optional[str] = None
    max_steps: Optional[int] = None
    headless: Optional[bool] = None
    email: Optional[str] = None
    password: Optional[str] = None


class EvalSuite(BaseModel):
    """Registry of eval cases loaded from disk."""

    version: int = 1
    defaults: EvalDefaults = Field(default_factory=EvalDefaults)
    cases: List[EvalCase]


class POComparison(BaseModel):
    """Field-level comparison between extracted and expected PO."""

    passed: bool
    mismatches: List[str] = Field(default_factory=list)


class StateComparison(BaseModel):
    """Comparison between portal server state and expected write-back state."""

    passed: bool
    mismatches: List[str] = Field(default_factory=list)
    actual: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalCaseMetrics(BaseModel):
    """Timing and efficiency metrics for a single case run."""

    step_count: int
    total_duration_ms: float
    llm_duration_ms: float
    avg_step_duration_ms: float
    avg_llm_duration_ms: float


class EvalCaseResult(BaseModel):
    """Outcome of running one eval case."""

    case_id: str
    portal: PortalVersion
    portal_url: str
    po_number: str
    agent_success: bool
    extraction_pass: bool
    state_pass: Optional[bool] = None
    passed: bool
    metrics: EvalCaseMetrics
    failure_reason: Optional[str] = None
    po_comparison: Optional[POComparison] = None
    state_comparison: Optional[StateComparison] = None
    agent_metadata: dict[str, Any] = Field(default_factory=dict)


class EvalSummary(BaseModel):
    """Aggregate metrics across a full eval run."""

    total: int
    passed: int
    failed: int
    agent_success_rate: float
    extraction_accuracy: float
    pass_rate: float
    avg_steps: float
    avg_total_duration_ms: float
    avg_llm_duration_ms: float


class EvalReport(BaseModel):
    """Persisted output of an eval run."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    agent_name: str
    agent_metadata: dict[str, Any] = Field(default_factory=dict)
    cases: List[EvalCaseResult]
    summary: EvalSummary
