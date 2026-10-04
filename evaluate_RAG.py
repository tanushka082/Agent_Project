from curses import raw
import os
import json
import re
from pathlib import Path
import lancedb
import ollama
from langchain_ollama import OllamaEmbeddings

# 1. Disable DeepEval's per-attempt execution timeout (for CPU/local SLM stability)
os.environ["DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE"] = "99999"

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRelevancyMetric
)
from deepeval.models import OllamaModel

# Configuration Paths
DATASET_PATH = Path("nissan_dtc_rag_eval_dataset.json")
DB_PATH = "lancedb"
TABLE_NAME = "onboard_slm_chunks"

# Initialize Local DeepEval Judge Model
eval_model = OllamaModel(
    model="llama3.2:3b-judge",
    base_url="http://localhost:11434",
    temperature=0.0,
)


# NOISE CLEANING

def clean_pdf_noise(text: str) -> str:
    """Strips PDF margin noise and table header artifacts before context logging."""
    if not text:
        return ""
    text = re.sub(r'######\s*<[^>]+>', '', text)
    text = re.sub(r'######\s*\*\*\[[^\]]+\]\*\*', '', text)
    lines = text.split("\n")
    cleaned = [l for l in lines if len(l.strip()) > 2 or l.strip().startswith("#") or l.strip().startswith("|")]
    return "\n".join(cleaned)


# RAG PIPELINE EXECUTION

def run_single_query(query: str):
    """Retrieves context from LanceDB and generates answer via Ollama INT4."""
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = lancedb.connect(DB_PATH)
    table = db.open_table(TABLE_NAME)
    
    # 1. Vector Search (Reduced top_k from 3 to 2 to minimize context noise)
    query_vector = embeddings.embed_query(f"search_query: {query}")
    results = table.search(query_vector).metric("cosine").limit(2).to_list()
    
    # 2. Clean PDF noise on retrieved chunks
    retrieved_chunks = [clean_pdf_noise(r.get("text", "")) for r in results]
    context_str = "\n---\n".join(retrieved_chunks)

    # 3. Strict ISO 26262 Grounding System Prompt
    system_prompt = (
        "You are an ISO 26262-compliant automotive diagnostic assistant.\n"
        "Answer the user query using ONLY the provided manual context.\n"
        "If the exact cause or parameter is not explicitly stated in context, "
        "state 'Information not available in context'. Do not infer or extrapolate."
    )

    prompt = f"CONTEXT:\n{context_str}\n\nQUERY: {query}"
    
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response["message"]["content"], retrieved_chunks


# BATCH EVALUATION BUILDER

def build_evaluation_batch():
    with open(DATASET_PATH, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    dataset= raw["test_cases"] if isinstance(raw , dict) and "test_cases" in raw else raw
    test_cases = []
    print(f"Executing RAG pipeline for {len(dataset)} scenarios in dataset.json...")

    for idx, case in enumerate(dataset, 1):
        query = case["query"]
        expected_output = f"DTC {case['dtc']} caused by: " + ", ".join(case["groundtruth_cause"])

        actual_output, retrieved_chunks = run_single_query(query)

        tc = LLMTestCase(
            input=query,
            actual_output=actual_output,
            expected_output=expected_output,
            retrieval_context=retrieved_chunks
        )
        test_cases.append(tc)
        print(f" -> Processed [{idx}/{len(dataset)}] DTC: {case['dtc']}")

    return test_cases


# MAIN EXECUTION

if __name__ == "__main__":
    all_test_cases = build_evaluation_batch()

    # Recalibrated Metric Configuration
    faithfulness = FaithfulnessMetric(threshold=0.50, model=eval_model, async_mode=False)
    answer_relevancy = AnswerRelevancyMetric(threshold=0.70, model=eval_model, async_mode=False)
    # Lowered threshold to 0.45 to account for OEM service manual table structures
    context_relevancy = ContextualRelevancyMetric(threshold=0.45, model=eval_model, async_mode=False)

    
    print("               RUNNING OPTIMIZED DEEPEVAL BENCHMARK                      ")
    
    
    evaluate(
        test_cases=all_test_cases,
        metrics=[faithfulness, answer_relevancy, context_relevancy],
        async_config=AsyncConfig(run_async=False)
    )
