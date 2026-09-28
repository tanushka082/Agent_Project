# eval/metrics.py
from typing import Dict, Any, List
from pydantic import BaseModel

class MetricResult(BaseModel):
    metric_name: str
    score: float  # 0.0 to 1.0
    passed: bool
    reason: str

class AgentEvaluator:
    @staticmethod
    def evaluate_argument_correctness(state: Dict[str, Any]) -> MetricResult:
        """
        Evaluates whether requested PIDs and telemetry fields were correctly 
        populated without empty lists or 'PID_NOT_AVAILABLE' fallbacks.
        """
        pids = state.get("requested_pids", [])
        telemetry = state.get("live_telemetry", {})
        
        if not pids:
            return MetricResult(
                metric_name="Argument Correctness",
                score=0.0,
                passed=False,
                reason="Requested PIDs list was empty."
            )
            
        unmapped_count = sum(1 for v in telemetry.values() if v == "PID_NOT_AVAILABLE")
        total_pids = len(telemetry)
        
        if total_pids == 0:
            score = 0.0
        else:
            score = round((total_pids - unmapped_count) / total_pids, 2)
            
        passed = score >= 0.75
        reason = f"{total_pids - unmapped_count}/{total_pids} PIDs successfully retrieved from telemetry source."
        
        return MetricResult(
            metric_name="Argument Correctness",
            score=score,
            passed=passed,
            reason=reason
        )

    @staticmethod
    def evaluate_step_efficiency(executed_steps: int, expected_steps: int = 2) -> MetricResult:
        """
        Evaluates graph trajectory efficiency. For a 2-node pipeline, 2 steps is optimal.
        """
        if executed_steps <= expected_steps:
            score = 1.0
            passed = True
            reason = f"Optimal step count achieved ({executed_steps}/{expected_steps})."
        else:
            score = max(0.0, round(expected_steps / executed_steps, 2))
            passed = False
            reason = f"Pipeline took {executed_steps} steps, expected {expected_steps}."
            
        return MetricResult(
            metric_name="Step Efficiency",
            score=score,
            passed=passed,
            reason=reason
        )

    @staticmethod
    def evaluate_task_completion(state: Dict[str, Any]) -> MetricResult:
        """
        Evaluates whether the graph reached a valid terminal diagnostic state.
        """
        findings = state.get("reasoning_findings")
        active_dtc = state.get("active_dtc")
        
        if not findings or not isinstance(findings, dict):
            return MetricResult(
                metric_name="Task Completion",
                score=0.0,
                passed=False,
                reason="Reasoning findings are missing or non-dictionary."
            )
            
        root_cause = (
            findings.get("primary_root_cause") or 
            findings.get("root_cause", {}).get("description")
        )
        confidence = (
            findings.get("highest_confidence") or 
            findings.get("confidence_score", 0)
        )
        
        if root_cause and confidence > 0:
            return MetricResult(
                metric_name="Task Completion",
                score=1.0,
                passed=True,
                reason=f"Successfully identified root cause '{root_cause}' for {active_dtc} with {confidence}% confidence."
            )
            
        return MetricResult(
            metric_name="Task Completion",
            score=0.0,
            passed=False,
            reason="Incomplete root cause evaluation or zero confidence score."
        )