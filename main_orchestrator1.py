# main_orchestrator1.py
import sys
import os
from langgraph.graph import StateGraph, END
from state import DiagnosticState
from data_planning_node import data_planning_node
from reasoning_node import reasoning_node

# --- 1. BUILD THE LANGGRAPH WORKFLOW ---
def build_diagnostic_graph():
    workflow = StateGraph(DiagnosticState)
    
    # Add Nodes
    workflow.add_node("data_planning", data_planning_node)
    workflow.add_node("reasoning", reasoning_node)
    
    # Define Flow: Entry -> Data Planning -> Reasoning -> End
    workflow.set_entry_point("data_planning")
    workflow.add_edge("data_planning", "reasoning")
    workflow.add_edge("reasoning", END)
    
    return workflow.compile()

# --- 2. EXPOSE THE ENTRYPOINT FUNCTION FOR UI & CLI ---
def run_pipeline(target_dtc: str) -> dict:
    """
    Executes Node 1 and Node 2.
    Returns the final state dictionary to Streamlit UI or Terminal.
    """
    app = build_diagnostic_graph()
    
    initial_state = {
        "active_dtc": target_dtc,
        "primary_dtc": target_dtc,
        "dtc_description": "",
        "is_safety_critical": False,
        "requested_pids": [],
        "expected_parameter_ranges": {},
        "live_telemetry": {},
        "reasoning_findings": {}
    }
    
    # Executes nodes and prints terminal outputs as normal
    final_state = app.invoke(initial_state)
    
    return final_state if final_state is not None else initial_state

# --- 3. DIRECT TERMINAL EXECUTION TEST ---
if __name__ == "__main__":
    dtc_code = sys.argv[1].upper() if len(sys.argv) > 1 else "P0300"
    print(f"\n==================================================")
    print(f"STARTING LANGGRAPH PIPELINE FOR DTC: {dtc_code}")
    print(f"==================================================")
    
    result = run_pipeline(dtc_code)
    
    print(f"\n==================================================")
    print(f"EXECUTION COMPLETE FOR {dtc_code}")
    print(f"==================================================")
