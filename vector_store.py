# vector_store.py
import os
import re
import lancedb
import ollama

# Fallback path handler matching project folder structure
DB_PATH = "lancdb"
TABLE_NAME = "onboard_slm_chunks"

db = lancedb.connect(DB_PATH)

def get_table():
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        tables = db.table_names()
        return db.open_table(tables[0]) if tables else None

table = get_table()

def get_embedding(text: str) -> list:
    response = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return response["embedding"]

def clean_manual_context(raw_text: str) -> str:
    """Strips secondary U-code cross-references and disclaimers."""
    cleaned = re.sub(r"If DTC .*? is displayed with DTC U\d+.*?\n", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"Refer to EC-\d+.*?\n", "", cleaned, flags=re.IGNORECASE)
    return cleaned

def query_lancedb(query_text: str, top_k: int = 4, filter_dtc: str = None) -> list:
    """Strict DTC-isolated vector retrieval preventing context bleeding."""
    if table is None:
        return []
        
    query_vector = get_embedding(query_text)
    results_df = table.search(query_vector).limit(30).to_pandas()
    
    # Strict Regex DTC Filter
    if filter_dtc and filter_dtc != "UNKNOWN" and "text" in results_df.columns:
        pattern = r'\b' + re.escape(filter_dtc) + r'\b'
        strict_df = results_df[results_df["text"].str.contains(pattern, case=False, na=False, regex=True)]
        if not strict_df.empty:
            results_df = strict_df

    results_df = results_df.head(top_k)
    
    chunks = []
    for _, row in results_df.iterrows():
        cleaned_text = clean_manual_context(row["text"])
        chunks.append({
            "text": cleaned_text,
            "page": row.get("page", 0),
            "source": row.get("source", "manual")
        })
    return chunks
