# data_planning_agent.py
import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field, AliasChoices
from vector_store import query_lancedb
from telemetry_adapter import fetch_telemetry
from call_local_slm import call_local_slm
from Raspberry_Pi.ecu_database import ENGINE_DTC_DATABASE

class DataPlanningRAGOutput(BaseModel):
    target_dtc: str = Field(validation_alias=AliasChoices('target_dtc', 'targetDtc', 'dtc'))
    dtc_description: str = Field(default="", validation_alias=AliasChoices('dtc_description', 'dtcDescription', 'description'))
    is_safety_critical: bool = Field(default=False, validation_alias=AliasChoices('is_safety_critical', 'isSafetyCritical', 'safety_critical'))
    required_pids: List[str] = Field(default_factory=list, validation_alias=AliasChoices('required_pids', 'requiredPids', 'pids'))
    expected_parameter_ranges: Dict[str, str] = Field(default_factory=dict, validation_alias=AliasChoices('expected_parameter_ranges', 'expectedRanges'))

class DataPlanningAgentRAG:
    def _extract_dtc_regex(self, query: str) -> str:
        match = re.search(r"\b[P|C|B|U]\d{4}\b", query, re.IGNORECASE)
        return match.group(0).upper() if match else "UNKNOWN"

    def run(self, user_query: str) -> Dict[str, Any]:
        dtc = self._extract_dtc_regex(user_query)
        
        # 1. Fetch ground-truth entry directly from ecu_database
        db_entry = ENGINE_DTC_DATABASE.get(dtc, {})
        db_telemetry_keys = list(db_entry.get("telemetry", {}).keys())
        db_description = db_entry.get("description", f"DTC {dtc} System Fault")
        
        # Ground-truth safety critical flag from ECU database
        db_safety_critical = db_entry.get("is_safety_critical", False)
        
        param_chunks = query_lancedb(f"DTC {dtc} trouble diagnosis name sensor input signal specification nominal ranges", top_k=4, filter_dtc=dtc)
        manual_context = "\n\n".join([chunk["text"] for chunk in param_chunks])

        prompt = f"""
        You are an OEM automotive diagnostic planning engine evaluating DTC {dtc}.
        
        OEM MANUAL CONTEXT FOR DTC {dtc}:
        --------------------------------------------------
        {manual_context}
        --------------------------------------------------
        
        AVAILABLE SENSOR PIDs IN ECU FOR DTC {dtc}:
        {json.dumps(db_telemetry_keys)}
        
        INSTRUCTIONS:
        1. Extract official 'dtc_description' directly from manual text context.
        2. Select required sensor PIDs to diagnose DTC {dtc} prioritizing the AVAILABLE SENSOR PIDs list.
        3. Determine 'is_safety_critical' (true if code relates to engine stalling, misfire, internal ECM failure, brake/steering, or overheating).
        4. Provide expected nominal operating ranges for each selected PID.
        
        Output strictly valid JSON:
        {{
            "target_dtc": "{dtc}",
            "dtc_description": "{db_description}",
            "is_safety_critical": {json.dumps(db_safety_critical)},
            "required_pids": {json.dumps(db_telemetry_keys)},
            "expected_parameter_ranges": {{
                "PID_NAME": "nominal range"
            }}
        }}
        """

        slm_raw = call_local_slm(prompt, temperature=0.0, num_predict=512)

        try:
            raw_json = slm_raw
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_json)
            output = DataPlanningRAGOutput(**parsed)
            
            dtc_desc = output.dtc_description or db_description
            requested_pids = output.required_pids if output.required_pids else db_telemetry_keys
            expected_ranges = output.expected_parameter_ranges
            # Prioritize database ground-truth flag
            is_safety_critical = db_entry.get("is_safety_critical", output.is_safety_critical)
        except Exception as e:
            print(f" [WARNING] Fallback in Data Planning Agent: {e}")
            dtc_desc = db_description
            requested_pids = db_telemetry_keys
            expected_ranges = {k: "Nominal range per OEM specification" for k in db_telemetry_keys}
            is_safety_critical = db_safety_critical

        live_telemetry = fetch_telemetry(dtc, requested_pids)

        return {
            "dtc_description": dtc_desc,
            "is_safety_critical": is_safety_critical,  # Returns True for P0605
            "requested_pids": requested_pids,
            "expected_parameter_ranges": expected_ranges,
            "live_telemetry": live_telemetry
        }
