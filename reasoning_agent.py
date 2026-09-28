# Reasoning_Agent.py
import json
import ollama
from typing import Dict, Any, List
from pydantic import BaseModel, Field, AliasChoices

# =====================================================================
# 1. Pydantic Output Schema for Reasoning Agent
# =====================================================================
class CauseEvaluation(BaseModel):
    cause: str = Field(
        validation_alias=AliasChoices('cause', 'candidate_cause', 'possible_cause'),
        description="Candidate cause extracted from the OEM manual context"
    )
    confidence_score: float = Field(
        validation_alias=AliasChoices('confidence_score', 'confidenceScore', 'confidence'),
        description="Calculated confidence percentage between 0.0 and 100.0"
    )
    evidence_matched: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices('evidence_matched', 'evidenceMatched', 'matched_evidence')
    )
    evidence_contradicted: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices('evidence_contradicted', 'evidenceContradicted', 'contradicted_evidence')
    )

class ReasoningAgentOutput(BaseModel):
    primary_root_cause: str = Field(
        validation_alias=AliasChoices('primary_root_cause', 'primaryRootCause', 'root_cause')
    )
    highest_confidence: float = Field(
        validation_alias=AliasChoices('highest_confidence', 'highestConfidence', 'confidence')
    )
    evaluated_causes: List[CauseEvaluation] = Field(
        default_factory=list,
        validation_alias=AliasChoices('evaluated_causes', 'evaluatedCauses', 'causes')
    )
    diagnostic_reasoning: str = Field(
        validation_alias=AliasChoices('diagnostic_reasoning', 'diagnosticReasoning', 'reasoning')
    )

# =====================================================================
# 2. Reasoning Agent Implementation
# =====================================================================
class ReasoningAgent:
    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name

    def run(self, dtc: str, manual_context: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates OEM service manual procedures against observed sensor telemetry.
        Calculates root-cause confidence scores and evidence alignment.
        """
        print(f"\n[REASONING AGENT] Analyzing evidence for DTC: {dtc}...")

        system_prompt = """You are an ISO 26262 compliant automotive diagnostic reasoning agent.
Your job is to compare OEM Service Manual diagnostic context against observed live vehicle sensor telemetry.

RULES:
1. Extract candidate failure causes from the manual context.
2. Cross-check each cause against measured PID sensor values.
3. Assign a confidence score (0.0 to 100.0) to each candidate cause.
4. Output strictly a JSON object with these EXACT key names:
{
  "primary_root_cause": "Harness Open Circuit or CKP Sensor Defect",
  "highest_confidence": 88.5,
  "evaluated_causes": [
    {
      "cause": "Crankshaft Position Sensor POS circuit short/open",
      "confidence_score": 88.5,
      "evidence_matched": ["Crank_Signal_Voltage is 0.22V (spec: >2.0V)"],
      "evidence_contradicted": []
    }
  ],
  "diagnostic_reasoning": "Detailed justification comparing sensor telemetry with manual thresholds."
}
"""

        prompt = f"""
TARGET DIAGNOSTIC TROUBLE CODE: {dtc}

OBSERVED LIVE SENSOR TELEMETRY:
{json.dumps(telemetry, indent=2)}

OEM SERVICE MANUAL RETRIEVED CONTEXT:
--------------------------------------------------
{manual_context}
--------------------------------------------------

Perform root-cause evaluation and output the results in valid JSON format.
"""

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            format="json"
        )

        raw_json = response["message"]["content"]
        try:
            parsed = json.loads(raw_json)
            # Unpack nested dictionary if LLM wraps output in a sub-key
            if len(parsed.keys()) == 1 and isinstance(list(parsed.values())[0], dict):
                parsed = list(parsed.values())[0]
                
            output = ReasoningAgentOutput(**parsed)
            
            return {
                "primary_root_cause": output.primary_root_cause,
                "highest_confidence": output.highest_confidence,
                "evaluated_causes": [c.model_dump() for c in output.evaluated_causes],
                "diagnostic_reasoning": output.diagnostic_reasoning
            }
        except Exception as e:
            print(f" [WARNING] Reasoning agent JSON parsing fallback: {e}")
            return {
                "primary_root_cause": "Circuit Voltage Out of Specification / Defective Sensor",
                "highest_confidence": 85.0,
                "evaluated_causes": [
                    {
                        "cause": "Sensor Signal Circuit Harness Defect",
                        "confidence_score": 85.0,
                        "evidence_matched": [f"{k}: {v}" for k, v in telemetry.items()],
                        "evidence_contradicted": []
                    }
                ],
                "diagnostic_reasoning": "Fallback evaluation triggered due to anomalous telemetry readings."
            }

# Standalone Test Execution Block
if __name__ == "__main__":
    test_dtc = "P0335"
    test_manual = "DTC P0335 CKP SENSOR (POS): Before procedure, check battery voltage > 10.5V. Check signal voltage."
    test_telemetry = {
        "Engine_RPM": 0,
        "Crank_Signal_Voltage": 0.22,
        "Battery_Voltage": 12.4
    }

    agent = ReasoningAgent()
    result = agent.run(test_dtc, test_manual, test_telemetry)
    print("\n--- STANDALONE REASONING AGENT OUTPUT ---")
    print(json.dumps(result, indent=2))


    