"""Reference stub agent for wiring up FixtureBench.

Replace this with your own BrowserAgent implementation.
"""

from __future__ import annotations

from fixturebench.adapters.protocol import AgentRunResult, EvalTask


class StubAgent:
    """Fails every case with a helpful message."""

    @property
    def name(self) -> str:
        return "stub"

    def run(self, task: EvalTask) -> AgentRunResult:
        return AgentRunResult(
            success=False,
            failure_reason=(
                "StubAgent is a placeholder. Implement BrowserAgent and pass "
                f"--agent your_module:YourAgent to evaluate {task.case_id}."
            ),
        )
