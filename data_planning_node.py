# nodes/data_planning_node.py
from state import DiagnosticState
from Data_Planning_Agent import DataPlanningAgentRAG
from telemetry_adapter import fetch_telemetry

# Instantiate existing RAG agent
data_planning_agent = DataPlanningAgentRAG()

def data_planning_node(state: DiagnosticState) -> DiagnosticState:
    """
    LangGraph Node 1: Data Planning Agent Wrapper
    Reads active DTC, queries LanceDB, fetches telemetry, updates state.
    """
    active_dtc = state["active_dtc"]
    query = f"Vehicle powertrain fault alert: DTC {active_dtc} logged on ECM."

    print(f"\n==================================================")
    print(f"Executing [NODE 1: DATA PLANNING AGENT] for DTC: {active_dtc}")
    print(f"==================================================")

    # Call your existing Data Planning Agent logic
    payload = data_planning_agent.run(query)

    # Call your existing Telemetry Adapter
    telemetry = fetch_telemetry(payload["target_dtc"], payload["requested_pids"])

    # Update shared state
    state["dtc_description"] = payload["dtc_description"]
    state["is_safety_critical"] = payload["is_safety_critical"]
    state["requested_pids"] = payload["requested_pids"]
    state["planning_reasoning"] = payload["planning_reasoning"]
    
    if "retrieved_manual_context" not in state or state["retrieved_manual_context"] is None:
        state["retrieved_manual_context"] = {}
    state["retrieved_manual_context"][active_dtc] = payload["retrieved_context"]
    
    state["live_telemetry"] = telemetry

    return state