# state.py
from typing import TypedDict, List, Dict, Any, Optional

class DiagnosticState(TypedDict):
    primary_dtc: str
    active_dtc: str
    is_safety_critical: bool
    dtc_description: str
    requested_pids: List[str]
    planning_reasoning: str
    retrieved_manual_context: Dict[str, str]   # Map: DTC -> RAG text chunk
    live_telemetry: Dict[str, Any]             # Measured PID values
    reasoning_findings: Optional[Dict[str, Any]] # Output from Reasoning Node