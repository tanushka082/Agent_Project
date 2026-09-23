import re
import lancedb
import ollama
from langchain_ollama import OllamaEmbeddings

DB_PATH = "lancedb"
TABLE_NAME = "onboard_slm_chunks"

def retrieve_manual_context(query: str, source_filter: str = None, top_k: int = 2):
    """
    Dynamically extracts DTC codes (P/C/B/Uxxxx) from ANY random query string.
    Applies exact metadata filtering + vector search + deduplication.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = lancedb.connect(DB_PATH)
    table = db.open_table(TABLE_NAME)
    
    # 1. Dynamic DTC Code Extraction
    dtc_match = re.search(r"\b[P|C|B|U]\d{4}\b", query, re.IGNORECASE)
    query_vector = embeddings.embed_query(f"search_query: {query}")
    
    # 2. Build LanceDB Search Builder
    search_builder = table.search(query_vector).metric("cosine")
    
    where_clauses = []
    if dtc_match:
        target_dtc = dtc_match.group(0).upper()
        where_clauses.append(f"text LIKE '%{target_dtc}%'")
        
    if source_filter:
        where_clauses.append(f"source LIKE '%{source_filter}%'")
        
    if where_clauses:
        filter_str = " AND ".join(where_clauses)
        search_builder = search_builder.where(filter_str)
        
    # Retrieve raw candidate pool (limit=10) for deduplication
    raw_results = search_builder.limit(2).to_list()
    
    # Fallback to pure vector search if targeted DTC keyword yields 0 hits
    if not raw_results and dtc_match:
        search_builder = table.search(query_vector).metric("cosine")
        if source_filter:
            search_builder = search_builder.where(f"source LIKE '%{source_filter}%'")
        raw_results = search_builder.limit(2).to_list()

    # 3. Deduplicate Chunks
    unique_results = []
    seen_texts = []

    for res in raw_results:
        res_text = res["text"].strip()
        is_duplicate = False
        
        for seen in seen_texts:
            if res_text[:100] == seen[:100]:
                is_duplicate = True
                break
                
        if not is_duplicate:
            seen_texts.append(res_text)
            unique_results.append(res)
            if len(unique_results) == top_k:
                break
                
    return unique_results

def run_diagnostic_search(user_query: str):
    print(f"\n==================================================")
    print(f"QUERY: '{user_query}'")
    print(f"==================================================")
    
    results = retrieve_manual_context(user_query, top_k=2)
    
    if not results:
        print("No matching manual chunks found.")
        return

    for idx, match in enumerate(results, 1):
        print(f"\n--- MATCH {idx} | Content Type: {match['type']} ---")
        print(f"Source Doc  : {match['source']} (Page {match['page']})")
        print(f"Chunk ID    : {match['id']}")
        print(f"Asset Path  : {match['asset_path'] if match['asset_path'] else 'None'}")
        print(f"Content snippet:\n{match['text'][:300]}...\n" + "-"*50)

if __name__ == "__main__":
    # Test with any random DTC query string:
    run_diagnostic_search("Fault code :P0335?")
    run_diagnostic_search("What causes DTC P0340 camshaft sensor failure?")