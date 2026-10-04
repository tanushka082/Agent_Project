# Reasoning_Agent.py
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field, AliasChoices
from call_local_slm import call_local_slm

class SingleHypothesis(BaseModel):
    cause_description: str = Field(validation_alias=AliasChoices('cause_description', 'cause', 'candidate_cause'))
    confidence_score: float = Field(ge=0.0, le=100.0, validation_alias=AliasChoices('confidence_score', 'confidenceScore'))
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)

class ReasoningAgentOutput(BaseModel):
    primary_root_cause: str = Field(validation_alias=AliasChoices('primary_root_cause', 'root_cause'))
    highest_confidence: float = Field(validation_alias=AliasChoices('highest_confidence', 'confidence_score', 'confidence'))
    evaluated_hypotheses: List[SingleHypothesis] = Field(default_factory=list)
    diagnostic_reasoning: str = Field(default="", validation_alias=AliasChoices('diagnostic_reasoning', 'reasoning_rationale', 'explanation'))

class ReasoningAgent:
    def run(self, dtc: str, manual_context: str, telemetry: Dict[str, Any], expected_ranges: Dict[str, str] = None, dtc_description: str = "") -> Dict[str, Any]:
        prompt = f"""
        You are an expert automotive diagnostic reasoning engine evaluating DTC {dtc} ({dtc_description}).
        
        OEM SERVICE MANUAL CONTEXT FOR DTC {dtc}:
        --------------------------------------------------
        {manual_context}
        --------------------------------------------------
        
        EXPECTED NOMINAL SENSOR RANGES:
        {json.dumps(expected_ranges or {}, indent=2)}
        
        OBSERVED LIVE SENSOR TELEMETRY:
        {json.dumps(telemetry, indent=2)}
        
        STRICT EVALUATION RULES:
        1. Extract EVERY physical cause listed under 'Possible cause' in the manual context for DTC {dtc}.
        2. DO NOT mention U-codes (U1000, U1010, U0101) or general condition text as primary root causes. Use physical components.
        3. DO NOT invent numerical sensor values! Use ONLY the values in OBSERVED LIVE SENSOR TELEMETRY.
        4. MISSING DATA RULE: If telemetry is "PID_NOT_AVAILABLE", reduce confidence for that cause BELOW 40.0%. Never assign >80% confidence when data is missing!
        5. Select the physical cause with the HIGHEST confidence score as 'primary_root_cause'.
        
        Output strictly valid JSON matching this schema:
        {{
            "evaluated_hypotheses": [
                {{
                    "cause_description": "Physical Cause extracted from manual",
                    "confidence_score": 85.0,
                    "supporting_evidence": ["Telemetry evidence supporting this cause"],
                    "contradicting_evidence": []
                }}
            ],
            "primary_root_cause": "Physical Cause extracted from manual",
            "highest_confidence": 85.0,
            "diagnostic_reasoning": "Comparative rationale explaining cause selection."
        }}
        """

        slm_raw = call_local_slm(prompt, temperature=0.0, num_predict=1024)

        try:
            raw_json = slm_raw
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_json)
            output = ReasoningAgentOutput(**parsed)
            return output.model_dump()
        except Exception as e:
            print(f" [WARNING] Reasoning agent fallback: {e}")
            has_missing_data = "PID_NOT_AVAILABLE" in str(telemetry)
            return {
                "primary_root_cause": f"System fault associated with DTC {dtc} ({dtc_description})",
                "highest_confidence": 35.0 if has_missing_data else 70.0,
                "evaluated_hypotheses": [],
                "diagnostic_reasoning": "Fallback evaluation triggered due to structure oscillation."
            }
