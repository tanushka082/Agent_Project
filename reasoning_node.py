# nodes/reasoning_node.py
from state import DiagnosticState
from reasoning_agent import ReasoningAgent

reasoning_agent_instance = ReasoningAgent()

def reasoning_node(state: DiagnosticState) -> DiagnosticState:
    active_dtc = state["active_dtc"]
    manual_context = state["retrieved_manual_context"].get(active_dtc, "")
    telemetry = state["live_telemetry"]

    print(f"\n==================================================")
    print(f"Executing [NODE 2: REASONING AGENT] for DTC: {active_dtc}")
    print(f"==================================================")

    findings = reasoning_agent_instance.run(active_dtc, manual_context, telemetry)
    state["reasoning_findings"] = findings

    # Safely extract values across different JSON structures
    root_cause = (
        findings.get('primary_root_cause') or 
        findings.get('root_cause', {}).get('description') or 
        "Root cause identified from manual"
    )
    
    confidence = (
        findings.get('highest_confidence') or 
        findings.get('confidence_score') or 
        0
    )
    
    rationale = (
        findings.get('diagnostic_reasoning') or 
        findings.get('rationale') or 
        "Evaluated using OEM manual context & telemetry"
    )

    print(f" ├─ Identified Root Cause : {root_cause}")
    print(f" ├─ Highest Confidence   : {confidence}%")
    print(f" └─ Rationale            : {rationale}")

    return state