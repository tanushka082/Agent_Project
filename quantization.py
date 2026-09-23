import json
import time
import psutil
from pathlib import Path
import lancedb
from pydantic import BaseModel, Field
from typing import List, Optional
import ollama
from langchain_ollama import OllamaEmbeddings

# ==========================================
# FILE PATH CONFIGURATION
# ==========================================
DATASET_PATH = Path("nissan dtc rag eval dataset.json")
DB_PATH = "lancedb"
TABLE_NAME = "onboard_slm_chunks"

# Correct Ollama tags for local models
MODELS_TO_BENCHMARK = [
    "llama3.2:3b-instruct-fp16",  # FP16 Precision
   # "llama3.2:3b-instruct-q8_0",   # INT8 Quantization
    "llama3.2:3b"                  # INT4 Quantization (Q4_K_M)
]

# ==========================================
# PYDANTIC OUTPUT SCHEMA
# ==========================================
class DiagnosticBenchmarkOutput(BaseModel):
    dtc_code: str = Field(description="The fault code analyzed")
    extracted_causes: List[str] = Field(description="List of identified root causes")
    extracted_sensors: List[str] = Field(description="Sensors required for live telemetry verification")
    asil_rating: Optional[str] = Field(description="ISO 26262 ASIL classification if applicable")

# ==========================================
# DATASET LOADER
# ==========================================
def load_dataset(json_path: Path) -> list:
    """Safely loads test scenarios from the specified dataset file path."""
    if not json_path.exists():
        raise FileNotFoundError(f"[ERROR] Could not find dataset file at: {json_path.resolve()}")
    
    if json_path.stat().st_size == 0:
        raise ValueError(f"[ERROR] '{json_path.name}' is empty. Please add valid JSON test cases.")
        
    with open(json_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    print(f"[BENCHMARK] Loaded {len(data)} test scenarios from '{json_path.name}'\n")
    return data

# ==========================================
# RETRIEVAL HELPER
# ==========================================
def fetch_rag_context(query: str, top_k: int = 3) -> str:
    """Retrieves top context chunks from local LanceDB vector store."""
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = lancedb.connect(DB_PATH)
    
    try:
        table = db.open_table(TABLE_NAME)
    except Exception:
        print(f"[ERROR] Could not open table '{TABLE_NAME}'. Ensure ingest_manual.py has run.")
        return ""

    query_vector = embeddings.embed_query(f"search_query: {query}")
    results = table.search(query_vector).metric("cosine").limit(top_k).to_list()
    
    context = "\n".join([r["text"] for r in results])
    return context

# ==========================================
# BENCHMARK EXECUTION ENGINE
# ==========================================
def run_quantization_benchmark():
    test_cases = load_dataset(DATASET_PATH)
    benchmark_results = {}

    for model_name in MODELS_TO_BENCHMARK:
        print("==================================================")
        print(f" BENCHMARKING MODEL: {model_name}")
        print("==================================================")

        total_latency = 0.0
        json_parse_successes = 0
        accuracy_scores = []
        
        process = psutil.Process()
        start_mem = process.memory_info().rss / (1024 * 1024)

        for tc in test_cases:
            query = tc["query"]
            context = fetch_rag_context(query)

            system_prompt = (
                "You are an automotive diagnostic evaluation agent.\n"
                "Extract diagnostic details using ONLY the provided manual context.\n"
                "Respond strictly in valid JSON matching the schema."
            )
            
            user_prompt = f"CONTEXT:\n{context}\n\nQUERY: {query}"

            start_time = time.time()
            try:
                response = ollama.chat(
                    model=model_name,
                    format=DiagnosticBenchmarkOutput.model_json_schema(),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                total_latency += latency_ms

                # Parse JSON and validate against schema
                raw_json = response["message"]["content"]
                parsed_obj = DiagnosticBenchmarkOutput.model_validate_json(raw_json)
                json_parse_successes += 1

                # Flexible keyword matching against Ground Truth
                matches = 0
                for expected in tc["ground_truth_causes"]:
                    expected_words = [w.lower() for w in expected.split() if len(w) > 2]
                    if any(
                        any(word in found.lower() for word in expected_words)
                        for found in parsed_obj.extracted_causes
                    ):
                        matches += 1

                acc = (matches / len(tc["ground_truth_causes"])) * 100 if tc["ground_truth_causes"] else 100
                accuracy_scores.append(acc)

                print(f" -> [{tc['id']} - {tc['dtc_code']}] Latency: {latency_ms:.1f}ms | JSON: OK | Accuracy: {acc:.1f}%")

            except Exception as e:
                print(f" -> [{tc['id']} - {tc['dtc_code']}] FAILED: {e}")
                accuracy_scores.append(0.0)

        end_mem = process.memory_info().rss / (1024 * 1024)
        
        num_cases = len(test_cases)
        benchmark_results[model_name] = {
            "avg_latency_ms": round(total_latency / num_cases, 2) if num_cases else 0,
            "parse_success_rate": round((json_parse_successes / num_cases) * 100, 2) if num_cases else 0,
            "avg_cause_accuracy": round(sum(accuracy_scores) / len(accuracy_scores), 2) if accuracy_scores else 0,
            "ram_usage_mb": round(end_mem - start_mem, 2)
        }

    # Print Summary Report
    print("\n=========================================================================")
    print("                    QUANTIZATION BENCHMARK SUMMARY                       ")
    print("=========================================================================")
    print(f"{'Model':<30} | {'Latency (ms)':<12} | {'JSON Acc (%)':<12} | {'Cause Acc (%)':<14}")
    print("-" * 75)
    for model, metrics in benchmark_results.items():
        print(f"{model:<30} | {metrics['avg_latency_ms']:<12} | {metrics['parse_success_rate']:<12} | {metrics['avg_cause_accuracy']:<14}")

if __name__ == "__main__":
    run_quantization_benchmark()
    