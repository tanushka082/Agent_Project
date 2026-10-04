# nodes/data_planning_node.py
from state import DiagnosticState
from Data_Planning_Agent import DataPlanningAgentRAG

data_agent = DataPlanningAgentRAG()

def data_planning_node(state: DiagnosticState) -> DiagnosticState:
    dtc = state.get("active_dtc") or state.get("primary_dtc")
    print(f"\n==================================================")
    print(f"Executing [NODE 1: DATA PLANNING AGENT] for DTC: {dtc}")
    print(f"==================================================")
    
    agent_result = data_agent.run(f"Diagnostic Trouble Code: {dtc}")
    
    state["dtc_description"] = agent_result.get("dtc_description", f"DTC {dtc}")
    state["is_safety_critical"] = agent_result.get("is_safety_critical", False)  # Written to state
    state["requested_pids"] = agent_result.get("requested_pids", [])
    state["expected_parameter_ranges"] = agent_result.get("expected_parameter_ranges", {})
    state["live_telemetry"] = agent_result.get("live_telemetry", {})
    
    print(f"[DATA PLANNING] DTC Description Extracted : {state['dtc_description']}")
    print(f"[DATA PLANNING] Safety Critical Flag     : {state['is_safety_critical']}")
    print(f"[DATA PLANNING] Extracted PIDs for {dtc}   : {state['requested_pids']}")
    print(f"[DATA PLANNING] Expected Ranges           : {state['expected_parameter_ranges']}")
    print(f"[DATA PLANNING] Live Telemetry Fetched    : {state['live_telemetry']}")
    
    return state
