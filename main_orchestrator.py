# main_orchestrator.py
import json
import random
from langgraph.graph import StateGraph, END
from state import DiagnosticState
from data_planning_node import data_planning_node
from reasoning_node import reasoning_node

# Import HARDWARE_MODE and DTC database for display & random selection
from telemetry_adapter import HARDWARE_MODE
from Raspberry_Pi.ecu_database import ENGINE_DTC_DATABASE

# 1. Build LangGraph Workflow
workflow = StateGraph(DiagnosticState)

# 2. Add Nodes
workflow.add_node("DataPlanningNode", data_planning_node)
workflow.add_node("ReasoningNode", reasoning_node)

# 3. Define Sequential Edges
workflow.set_entry_point("DataPlanningNode")
workflow.add_edge("DataPlanningNode", "ReasoningNode")
workflow.add_edge("ReasoningNode", END)

# 4. Compile Graph
app = workflow.compile()

def run_pipeline(target_dtc: str = None):
    # Select random DTC from 19 Excel codes if none passed
    selected_dtc = target_dtc if target_dtc else random.choice(list(ENGINE_DTC_DATABASE.keys()))
    
    # Check execution mode flag
    execution_mode = "HARDWARE (Raspberry Pi SOVD API)" if HARDWARE_MODE else "LOCAL SIMULATION (ecu_database.py)"

    print(f"\n==================================================")
    print(f"STARTING LANGGRAPH PIPELINE")
    print(f"Target DTC : {selected_dtc}")
    print(f"Active Mode: {execution_mode}")
    print(f"==================================================")

    initial_state: DiagnosticState = {
        "primary_dtc": selected_dtc,
        "active_dtc": selected_dtc,
        "is_safety_critical": False,
        "dtc_description": "",
        "requested_pids": [],
        "planning_reasoning": "",
        "retrieved_manual_context": {},
        "live_telemetry": {},
        "reasoning_findings": None
    }

    final_state = app.invoke(initial_state)

    print(f"\n==================================================")
    print(f"LANGGRAPH EXECUTION COMPLETED")
    print(f"==================================================")
    print(json.dumps({
        "active_dtc": final_state["active_dtc"],
        "dtc_description": final_state["dtc_description"],
        "is_safety_critical": final_state["is_safety_critical"],
        "live_telemetry": final_state["live_telemetry"],
        "reasoning_findings": final_state["reasoning_findings"]
    }, indent=2))

if __name__ == "__main__":
    # Runs randomly by default
    run_pipeline()
