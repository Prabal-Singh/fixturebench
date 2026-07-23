"""Built-in agents shipped with FixtureBench."""

from __future__ import annotations

from fixturebench.adapters.protocol import AgentRunResult, EvalTask


class StubAgent:
    """Fails every case with a helpful wiring message."""

    @property
    def name(self) -> str:
        return "stub"

    def run(self, task: EvalTask) -> AgentRunResult:
        return AgentRunResult(
            success=False,
            failure_reason=(
                "StubAgent is a placeholder. Implement BrowserAgent and pass "
                f"--agent your_module:YourAgent (got case {task.case_id} @ {task.url})."
            ),
        )
