# nodes/reasoning_node.py
from state import DiagnosticState
from reasoning_agent import ReasoningAgent
from vector_store import query_lancedb

reasoning_agent = ReasoningAgent()

def reasoning_node(state: DiagnosticState) -> DiagnosticState:
    dtc = state.get("active_dtc") or state.get("primary_dtc")
    dtc_desc = state.get("dtc_description", "")
    expected_ranges = state.get("expected_parameter_ranges", {})
    live_telemetry = state.get("live_telemetry", {})
    
    print(f"\n==================================================")
    print(f"Executing [NODE 2: REASONING AGENT] for DTC: {dtc}")
    print(f"Official Manual Description: {dtc_desc}")
    print(f"==================================================")
    
    cause_chunks = query_lancedb(f"DTC {dtc} candidate root causes possible cause diagnostic matrix", top_k=4, filter_dtc=dtc)
    cause_context_text = "\n\n".join([chunk["text"] for chunk in cause_chunks])
    
    print(f"[REASONING AGENT] RAG Query 2 Context Retrieved ({len(cause_context_text)} chars)")
    state["retrieved_cause_context"] = {dtc: cause_context_text}
    
    findings = reasoning_agent.run(
        dtc=dtc,
        manual_context=cause_context_text,
        telemetry=live_telemetry,
        expected_ranges=expected_ranges,
        dtc_description=dtc_desc
    )
    
    print(f"\n[MULTI-HYPOTHESIS EVALUATION SUMMARY]")
    for idx, hyp in enumerate(findings.get("evaluated_hypotheses", []), 1):
        print(f"  ├─ Candidate {idx}: {hyp['cause_description']} -> Confidence: {hyp['confidence_score']}%")
        
    print(f"\n[FINAL SELECTION]")
    print(f"  ├─ Isolated Root Cause : {findings['primary_root_cause']}")
    print(f"  ├─ Highest Confidence  : {findings['highest_confidence']}%")
    print(f"  └─ Comparative Rationale: {findings['diagnostic_reasoning']}")
    
    state["reasoning_findings"] = findings
    return state
