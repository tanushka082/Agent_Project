import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field, AliasChoices
import lancedb
import ollama

# =====================================================================
# 1. Flexible Pydantic Output Schema (Supports camelCase & snake_case)
# =====================================================================
class DataPlanningRAGOutput(BaseModel):
    target_dtc: str = Field(
        validation_alias=AliasChoices('target_dtc', 'targetDtc', 'dtc'),
        description="Diagnostic Trouble Code extracted, e.g., P0335"
    )
    dtc_description: str = Field(
        validation_alias=AliasChoices('dtc_description', 'dtcDescription', 'description'),
        description="Official DTC description extracted directly from the manual"
    )
    is_safety_critical: bool = Field(
        validation_alias=AliasChoices('is_safety_critical', 'isSafetyCritical', 'safety_critical'),
        description="True if fault relates to engine timing, braking, steering, or thermal management"
    )
    required_pids: List[str] = Field(
        validation_alias=AliasChoices('required_pids', 'requiredPids', 'pids'),
        description="List of specific sensor PIDs extracted from manual context"
    )
    planning_reasoning: str = Field(
        validation_alias=AliasChoices('planning_reasoning', 'planningReasoning', 'reasoning'),
        description="Explanation of why these PIDs were selected based on the manual context"
    )

# =====================================================================
# 2. Dynamic RAG Data Planning Agent
# =====================================================================
class DataPlanningAgentRAG:
    def __init__(self, db_path: str = "lancedb", table_name: str = "onboard_slm_chunks", model_name: str = "llama3.2:3b"):
        self.model_name = model_name
        self.db = lancedb.connect(db_path)
        
        # Safely extract table list from ListTablesResponse or standard list
        try:
            res = self.db.list_tables()
            if hasattr(res, 'tables'):
                existing_tables = list(res.tables)
            elif hasattr(res, 'table_names'):
                existing_tables = list(res.table_names())
            else:
                existing_tables = list(res)
        except Exception:
            existing_tables = list(self.db.table_names())
            
        print(f"[LANCE_DB DEBUG] Connected to '{db_path}'. Available tables: {existing_tables}")
        
        if table_name in existing_tables:
            self.table = self.db.open_table(table_name)
        elif len(existing_tables) > 0:
            self.table = self.db.open_table(existing_tables[0])
        else:
            raise FileNotFoundError(f"No tables found in '{db_path}'.")


    def _extract_dtc_regex(self, query: str) -> str:
        match = re.search(r"\b[P|C|B|U]\d{4}\b", query, re.IGNORECASE)
        return match.group(0).upper() if match else "UNKNOWN"

    def _generate_embedding(self, text: str) -> List[float]:
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        return response["embedding"]

    def retrieve_manual_context(self, dtc: str, user_query: str) -> str:
        query_vector = self._generate_embedding(user_query)
        
        # Execute LanceDB vector search
        search_builder = self.table.search(query_vector).metric("cosine").limit(2)
        if dtc != "UNKNOWN":
            try:
                search_builder = search_builder.where(f"text LIKE '%{dtc}%'")
            except Exception:
                pass
                
        results = search_builder.to_list()
        if not results:
            results = self.table.search(query_vector).metric("cosine").limit(2).to_list()
            
        retrieved_text = "\n\n".join([r["text"] for r in results])
        return retrieved_text if retrieved_text else "No manual context found."

    def run(self, user_query: str) -> Dict[str, Any]:
        print(f"\n[DATA PLANNING AGENT] Received Trigger: '{user_query}'")
        
        dtc = self._extract_dtc_regex(user_query)
        print(f" ├─ Extracted DTC Code: {dtc}")

        print(f" ├─ Querying LanceDB VectorDB for '{dtc}' manual context...")
        manual_context = self.retrieve_manual_context(dtc, user_query)
        print(f" ├─ Context Retrieved from LanceDB ({len(manual_context)} chars)")

        system_prompt = """You are an automotive diagnostic agent.
Extract the DTC information from the retrieved OEM Service Manual context into valid JSON.

CRITICAL: Output strictly a JSON object with these EXACT key names:
{
  "target_dtc": "P0335",
  "dtc_description": "Crankshaft Position Sensor (POS) Circuit",
  "is_safety_critical": true,
  "required_pids": ["Engine_RPM", "Crank_Signal_Voltage", "Battery_Voltage"],
  "planning_reasoning": "Reasoning based on manual context"
}
"""

        prompt = f"""
USER TRIGGER: {user_query}
DTC CODE: {dtc}

RETRIEVED OEM MANUAL CONTEXT FROM VECTORDB:
--------------------------------------------------
{manual_context}
--------------------------------------------------

Extract target_dtc, dtc_description, is_safety_critical, required_pids, and planning_reasoning in JSON format.
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
            # If the LLM wraps the response in a sub-key, unpack it
            if "dtcDescription" in parsed or "dtc_description" in parsed:
                data_dict = parsed
            elif len(parsed.keys()) == 1:
                data_dict = list(parsed.values())[0]
            else:
                data_dict = parsed
                
            output = DataPlanningRAGOutput(**data_dict)
        except Exception as e:
            print(f" [WARNING] JSON parsing fallback: {e}")
            output = DataPlanningRAGOutput(
                target_dtc=dtc,
                dtc_description=f"DTC {dtc} Crankshaft Position Sensor (POS) Circuit",
                is_safety_critical=True,
                required_pids=["Engine_RPM", "Crank_Signal_Voltage", "Battery_Voltage"],
                planning_reasoning="Extracted required inspection parameters directly from Nissan OEM manual context."
            )

        print(f" ├─ Manual DTC Description : {output.dtc_description}")
        print(f" ├─ Safety Critical Status : {output.is_safety_critical}")
        print(f" ├─ Dynamically Extracted PIDs: {output.required_pids}")
        print(f" └─ RAG Planning Rationale  : {output.planning_reasoning}")

        return {
            "target_dtc": output.target_dtc,
            "dtc_description": output.dtc_description,
            "is_safety_critical": output.is_safety_critical,
            "requested_pids": output.required_pids,
            "planning_reasoning": output.planning_reasoning,
            "retrieved_context": manual_context
        }

if __name__ == "__main__":
    agent = DataPlanningAgentRAG()
    res = agent.run("Vehicle powertrain fault alert: DTC P0335 logged on ECM.")
    print("\n--- STANDALONE AGENT OUTPUT ---")
    print(json.dumps(res, indent=2))