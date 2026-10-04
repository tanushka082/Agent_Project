# state.py
from typing import TypedDict, List, Dict, Any, Optional

class DiagnosticState(TypedDict):
    primary_dtc: str
    active_dtc: str
    is_safety_critical: bool
    dtc_description: str
    
    # --- Node 1 Outputs (RAG Query 1 + Telemetry Gateway) ---
    requested_pids: List[str]
    expected_parameter_ranges: Dict[str, str]  # PID -> Expected Nominal Bounds
    live_telemetry: Dict[str, Any]             # PID -> Live Measured Values (from ecu_database.py)
    
    # --- Node 2 Outputs (RAG Query 2 + Multi-Hypothesis Reasoning) ---
    retrieved_cause_context: Dict[str, str]    # DTC -> OEM Candidate Causes Matrix
    reasoning_findings: Optional[Dict[str, Any]] # Contains evaluated_hypotheses array + top selection
    
    # --- Phase 2 Future Scope ---
    safety_rating: Optional[Dict[str, Any]]      # Node 3 (ASIL Rating)
    action_plan: Optional[Dict[str, Any]]         # Node 4 (Physical Repair Steps)
