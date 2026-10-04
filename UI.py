
# UI.py
import streamlit as st
from Raspberry_Pi.ecu_database import ENGINE_DTC_DATABASE
from telemetry_adapter1 import set_hardware_mode, fetch_active_dtc_from_rpi
from main_orchestrator1 import run_pipeline

st.set_page_config(page_title="Diagnostic System", layout="wide")
st.title("Automotive Multi-Agent Diagnostic Dashboard")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header(" Fault Acquisition Options")

selection_method = st.sidebar.radio(
    "Choose DTC Source:",
    [
        "Select from ECU Database", 
        "Manual DTC Entry", 
        "Fetch Active DTC from Raspberry Pi (SOVD)"
    ]
)

selected_dtc = ""

if selection_method == "Select from ECU Database":
    set_hardware_mode(False)
    available_dtcs = list(ENGINE_DTC_DATABASE.keys())
    selected_dtc = st.sidebar.selectbox("Choose DTC:", available_dtcs)

elif selection_method == "Manual DTC Entry":
    set_hardware_mode(False)
    selected_dtc = st.sidebar.text_input("Enter Custom DTC:", value="P0300").strip().upper()

elif selection_method == "Fetch Active DTC from Raspberry Pi (SOVD)":
    set_hardware_mode(True)
    st.sidebar.info(" Hardware Mode Enabled: Communication active with Raspberry Pi.")
    
    if st.sidebar.button(" Read DTC from Raspberry Pi"):
        with st.sidebar.spinner("Querying Raspberry Pi SOVD Gateway..."):
            rpi_dtc = fetch_telemetry()
            if rpi_dtc != "NONE":
                st.session_state["rpi_detected_dtc"] = rpi_dtc
                st.sidebar.success(f"Detected DTC: {rpi_dtc}")
            else:
                st.sidebar.error("Failed to read active DTC from Raspberry Pi. Verify connection.")

    selected_dtc = st.session_state.get("rpi_detected_dtc", "")
    if selected_dtc:
        st.sidebar.text_input("Active Hardware DTC:", value=selected_dtc, disabled=True)

run_button = st.sidebar.button("Run Diagnostic Pipeline", type="primary")

# --- MAIN DISPLAY PANEL ---
if run_button:
    if not selected_dtc:
        st.warning("Please select or scan a valid DTC code first.")
    else:
        st.subheader(f"Pipeline Execution Results for DTC: {selected_dtc}")
        
        with st.spinner("Executing LangGraph Pipeline..."):
            # Call orchestrator safely
            final_state = run_pipeline(selected_dtc)

        # Safeguard against NoneType
        if not final_state or not isinstance(final_state, dict):
            st.error("Pipeline execution failed or returned invalid output. Check terminal for details.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("###  Node 1: Data Planning Agent")
                st.text_input("DTC Description:", value=final_state.get("dtc_description", ""), disabled=True)
                
                is_safe = final_state.get("is_safety_critical", False)
                st.text_input("Safety Critical Flag:", value="TRUE (High Priority Fault)" if is_safe else "FALSE (Standard Fault)", disabled=True)
                
                st.markdown("**Requested Sensor PIDs:**")
                st.json(final_state.get("requested_pids", []))
                
                st.markdown("**Expected Operating Ranges:**")
                st.json(final_state.get("expected_parameter_ranges", {}))
                
                st.markdown("**Fetched Telemetry Readings:**")
                st.json(final_state.get("live_telemetry", {}))

            with col2:
                st.markdown("###  Node 2: Reasoning Agent")
                findings = final_state.get("reasoning_findings", {})
                if isinstance(findings, dict):
                    root_cause = findings.get("primary_root_cause", "")
                    confidence = findings.get("highest_confidence") or findings.get("confidence_score") or 0.0
                    rationale = findings.get("diagnostic_reasoning") or findings.get("reasoning_rationale") or ""
                    
                    st.text_input("Isolated Primary Root Cause:", value=root_cause, disabled=True)
                    st.text_input("Confidence Score:", value=f"{confidence}%", disabled=True)
                    
                    st.markdown("**LLM Diagnostic Rationale:**")
                    st.text_area("Reasoning Analysis:", value=rationale, height=140, disabled=True)
                    
                    st.markdown("**Evaluated Candidate Hypotheses:**")
                    hypotheses = findings.get("evaluated_hypotheses", [])
                    if hypotheses:
                        st.dataframe(hypotheses, use_container_width=True)
