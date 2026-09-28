import json
import time
import subprocess
from pathlib import Path
from typing import List, Optional

import ollama
import psutil
import lancedb
from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field

# ============================================
# CONFIG
# ============================================

DATASET_PATH = Path("nissan_dtc_rag_eval_dataset.json")
# Where filled-in actual_output_fp16 / actual_output_int4 results get written.
# We never overwrite DATASET_PATH itself.
RESULTS_PATH = Path("nissan_dtc_rag_eval_results.json")

DB_PATH = "lancedb"          # <-- keep your existing value here
TABLE_NAME = "onboard_slm_chunks"    # <-- keep your existing value here

# If True, skip live RAG retrieval and use the "context" field already baked
# into each test case (pulled straight from the manual when the dataset was
# built). Useful for isolating pure generation-quality (fp16 vs INT4) from
# retrieval-quality, since fetch_rag_context() depends on your vector store.
USE_DATASET_CONTEXT = False

MODELS_TO_BENCHMARK = [
    "llama3.2:3b-instruct-fp16",   # fp16 (unquantized)
    "llama3.2:3b",                 # INT4 quantization (Q4_K_M)
]

# Maps a model name to the dataset field it should write its answer into.
QUANT_LABEL_MAP = {
    "llama3.2:3b-instruct-fp16": "actual_output_fp16",
    "llama3.2:3b": "actual_output_int4",
}

# Seconds to wait after unloading a model before starting the next one,
# so Ollama has time to actually free VRAM/RAM before the next model
# (and the embedding model) start making requests.
MODEL_SWITCH_COOLDOWN_SECONDS = 8

# How many times to retry a single embedding call if the Ollama server
# drops the connection (common right after a large model unload/load).
EMBED_RETRY_ATTEMPTS = 3
EMBED_RETRY_DELAY_SECONDS = 5


def unload_model(model_name: str):
    """Force Ollama to release this model from memory before switching models.
    Prevents fp16 weights still being resident when the next model starts,
    which can cause the server to drop in-flight requests (OOM/contention)."""
    try:
        subprocess.run(["ollama", "stop", model_name], check=False, timeout=30)
    except Exception as e:
        print(f"[WARN] Could not unload {model_name}: {e}")


# ============================================
# PYDANTIC OUTPUT SCHEMA
# ============================================

class DiagnosticBenchmarkOutput(BaseModel):
    dtc_code: str = Field(description="The fault code analyzed")
    extracted_causes: List[str] = Field(description="List of identified root causes")
    extracted_sensors: List[str] = Field(description="Sensors required for live telemetry verification")
    asil_rating: Optional[str] = Field(default=None, description="ISO 26262 ASIL classification if applicable")


# ============================================
# DATASET LOADER
# ============================================

def load_dataset(json_path: Path) -> list:
    """Safely loads test scenarios from nissan_dtc_rag_eval_dataset.json.

    That file is a wrapper dict: {"dataset_name": ..., "test_cases": [...]}.
    This also tolerates a plain top-level list, in case you point it at a
    differently-shaped file later.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"[ERROR] Could not find dataset file at: {json_path.resolve()}")

    if json_path.stat().st_size == 0:
        raise ValueError(f"[ERROR] '{json_path.name}' is empty. Please add valid JSON test cases.")

    with open(json_path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "test_cases" in raw:
        data = raw["test_cases"]
    elif isinstance(raw, list):
        data = raw
    else:
        raise ValueError(
            f"[ERROR] '{json_path.name}' is neither a list of test cases nor a dict with a "
            f"'test_cases' key. Got top-level type: {type(raw).__name__}"
        )

    print(f"[BENCHMARK] Loaded {len(data)} test scenarios from '{json_path.name}'\n")
    return data


# ============================================
# RETRIEVAL HELPER
# ============================================

def fetch_rag_context(query: str, top_k: int = 3) -> str:
    """Retrieves top context chunks from local LanceDB vector store.
    Retries the embedding call a few times if the Ollama server drops the
    connection (e.g. right after a large model was unloaded/loaded)."""
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = lancedb.connect(DB_PATH)

    try:
        table = db.open_table(TABLE_NAME)
    except Exception:
        print(f"[ERROR] Could not open table '{TABLE_NAME}'. Ensure ingest_manual.py has run.")
        return ""

    for attempt in range(1, EMBED_RETRY_ATTEMPTS + 1):
        try:
            query_vector = embeddings.embed_query(f"search_query: {query}")
            results = table.search(query_vector).metric("cosine").limit(top_k).to_list()
            return "\n".join([r["text"] for r in results])
        except Exception as e:
            print(f"[WARN] Embedding attempt {attempt}/{EMBED_RETRY_ATTEMPTS} failed: {e}")
            if attempt < EMBED_RETRY_ATTEMPTS:
                time.sleep(EMBED_RETRY_DELAY_SECONDS)
            else:
                print("[ERROR] Embedding failed after all retries; returning empty context for this query.")
                return ""


# ============================================
# ACCURACY / DRIFT HELPERS
# ============================================

def _keyword_match_rate(expected_list: List[str], found_list: List[str]) -> float:
    """Same flexible keyword-overlap scoring as before: for each expected
    phrase, count it as matched if any word (>2 chars) from it appears in
    any of the found strings. Returns a percentage."""
    if not expected_list:
        return 100.0

    matches = 0
    for expected in expected_list:
        expected_words = [w.lower() for w in expected.split() if len(w) > 2]
        if any(
            any(word in found.lower() for word in expected_words)
            for found in found_list
        ):
            matches += 1

    return (matches / len(expected_list)) * 100


def _terminology_drift_hits(extracted: List[str], forbidden_terms: List[str]) -> List[str]:
    """Flags any forbidden synonym terms (e.g. 'CKP sensor', 'mass flow
    sensor') that showed up in the model's output instead of the manual's
    own wording (e.g. 'Crankshaft position sensor (POS)', 'mass air flow
    sensor'). Returns the list of forbidden terms actually found."""
    if not forbidden_terms:
        return []

    joined = " ".join(extracted).lower()
    return [t for t in forbidden_terms if t.lower() in joined]


# ============================================
# BENCHMARK EXECUTION ENGINE
# ============================================

def run_quantization_benchmark():
    test_cases = load_dataset(DATASET_PATH)
    benchmark_results = {}

    for model_name in MODELS_TO_BENCHMARK:
        output_field = QUANT_LABEL_MAP.get(model_name, f"actual_output_{model_name.replace(':', '_').replace('.', '_')}")

        print("=" * 75)
        print(f" BENCHMARKING MODEL: {model_name}")
        print("=" * 75)

        total_latency = 0.0
        json_parse_successes = 0
        accuracy_scores = []          # cause accuracy, same metric as before
        sensor_accuracy_scores = []   # NEW: sensor accuracy vs groundtruth_sensor
        drift_flags = 0               # NEW: count of test cases with terminology drift

        def get_ollama_process_memory_mb() -> float:
            """Sums RSS across all running 'ollama' processes (the actual
            model host), not this Python script's own memory."""
            total = 0.0
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    if 'ollama' in (proc.info['name'] or '').lower():
                        total += proc.info['memory_info'].rss / (1024 * 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return total

        start_mem = get_ollama_process_memory_mb()

        for tc in test_cases:
            query = tc["query"]
            context = tc.get("context", "") if USE_DATASET_CONTEXT else fetch_rag_context(query)

            system_prompt = (
                "You are an automotive diagnostic evaluation agent.\n"
                "Extract diagnostic details using ONLY the provided manual context.\n"
                "Use the exact sensor names and terminology as they appear in the context "
                "(e.g. 'Crankshaft position sensor (POS)', not 'CKP sensor'; 'mass air flow "
                "sensor', not 'MAF sensor' or 'mass flow sensor').\n"
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
                        {"role": "user", "content": user_prompt},
                    ],
                )
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                total_latency += latency_ms

                # Parse JSON and validate against schema
                raw_json = response["message"]["content"]
                parsed_obj = DiagnosticBenchmarkOutput.model_validate_json(raw_json)
                json_parse_successes += 1

                # Cause accuracy vs the manual's verbatim "Possible cause" bullets
                cause_acc = _keyword_match_rate(tc["groundtruth_cause"], parsed_obj.extracted_causes)
                accuracy_scores.append(cause_acc)

                # Sensor accuracy vs the manual's verbatim sensor/component names
                sensor_acc = _keyword_match_rate(tc["groundtruth_sensor"], parsed_obj.extracted_sensors)
                sensor_accuracy_scores.append(sensor_acc)

                # Terminology drift check (synonyms the manual itself never uses)
                drift_hits = _terminology_drift_hits(
                    parsed_obj.extracted_causes + parsed_obj.extracted_sensors,
                    tc.get("forbidden_synonym_terms", []),
                )
                if drift_hits:
                    drift_flags += 1

                # Write the model's raw answer back into the dataset's placeholder field
                tc[output_field] = raw_json

                drift_note = f" | Drift: {drift_hits}" if drift_hits else ""
                print(
                    f" -> [{tc['id']} - {tc['dtc']}] Latency: {latency_ms:.1f}ms | JSON: OK | "
                    f"Cause Acc: {cause_acc:.1f}% | Sensor Acc: {sensor_acc:.1f}%{drift_note}"
                )

            except Exception as e:
                print(f" -> [{tc['id']} - {tc['dtc']}] FAILED: {e}")
                accuracy_scores.append(0.0)
                sensor_accuracy_scores.append(0.0)
                tc[output_field] = f"[ERROR] {e}"

        end_mem = get_ollama_process_memory_mb()

        num_cases = len(test_cases)
        benchmark_results[model_name] = {
            "avg_latency_ms": round(total_latency / num_cases, 2) if num_cases else 0,
            "parse_success_rate": round((json_parse_successes / num_cases) * 100, 2) if num_cases else 0,
            "avg_cause_accuracy": round(sum(accuracy_scores) / len(accuracy_scores), 2) if accuracy_scores else 0,
            "avg_sensor_accuracy": round(sum(sensor_accuracy_scores) / len(sensor_accuracy_scores), 2)
            if sensor_accuracy_scores else 0,
            "terminology_drift_rate": round((drift_flags / num_cases) * 100, 2) if num_cases else 0,
            "ram_usage_mb": round(end_mem - start_mem, 2),
        }

        # Free this model's memory before the next model starts, and give
        # Ollama time to actually release it (avoids the "Server disconnected
        # without sending a response" crash on the first call of the next model).
        print(f"\n[BENCHMARK] Unloading {model_name} and cooling down for "
              f"{MODEL_SWITCH_COOLDOWN_SECONDS}s before the next model...\n")
        unload_model(model_name)
        time.sleep(MODEL_SWITCH_COOLDOWN_SECONDS)

    # Save the dataset back out WITH the actual_output_* fields filled in.
    # This writes to RESULTS_PATH, never back to DATASET_PATH.
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"test_cases": test_cases}, f, indent=2, ensure_ascii=False)
    print(f"\n[BENCHMARK] Per-case model outputs saved to '{RESULTS_PATH.name}'")

    # Print Summary Report
    print("\n" + "=" * 100)
    print("QUANTIZATION BENCHMARK SUMMARY".center(100))
    print("=" * 100)
    print(
        f"{'Model':<30} | {'Latency (ms)':<12} | {'JSON Acc (%)':<12} | "
        f"{'Cause Acc (%)':<14} | {'Sensor Acc (%)':<15} | {'Drift (%)':<10}"
    )
    print("-" * 100)
    for model, metrics in benchmark_results.items():
        print(
            f"{model:<30} | {metrics['avg_latency_ms']:<12} | {metrics['parse_success_rate']:<12} | "
            f"{metrics['avg_cause_accuracy']:<14} | {metrics['avg_sensor_accuracy']:<15} | "
            f"{metrics['terminology_drift_rate']:<10}"
        )


if __name__ == "__main__":
    run_quantization_benchmark()
