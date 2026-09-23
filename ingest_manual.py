import os
import re
from pathlib import Path
import pymupdf as fitz  # PyMuPDF
import pymupdf4llm
import lancedb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

# Configuration Paths
DATA_DIR = Path("Data")
ASSET_DIR = Path("extracted_assets")
DB_PATH = "lancedb"
TABLE_NAME = "onboard_slm_chunks"

ASSET_DIR.mkdir(exist_ok=True)

def clean_pdf_noise(text: str) -> str:
    """Strips PDF margin noise and repetitive markdown header artifacts."""
    if not text:
        return ""
    text = re.sub(r'######\s*<[^>]+>', '', text)
    text = re.sub(r'######\s*\*\*\[[^\]]+\]\*\*', '', text)
    lines = text.split("\n")
    cleaned = [l for l in lines if len(l.strip()) > 2 or l.strip().startswith("#") or l.strip().startswith("|")]
    return "\n".join(cleaned)

def build_vector_database():
    pdf_files = list(DATA_DIR.glob("*.pdf"))
    print(f"[RAG BUILD] Found {len(pdf_files)} PDF manuals in '{DATA_DIR}'")

    processed_chunks = []
    chunk_counter = 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n"]
    )

    for pdf_path in pdf_files:
        doc_name = pdf_path.name
        print(f"[RAG BUILD] Processing: {doc_name}")
        
        doc = fitz.open(pdf_path)
        md_pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        
        for page_info in md_pages:
            page_num = page_info["metadata"]["page_number"]
            cleaned_text = clean_pdf_noise(page_info["text"])
            
            if len(cleaned_text.strip()) < 30:
                continue

            # Save Page Assets (Images)
            page_obj = doc[page_num - 1]
            page_images = page_obj.get_images(full=True)
            page_asset_paths = []
            
            for img_idx, img in enumerate(page_images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                img_filename = f"{pdf_path.stem}_p{page_num}_img{img_idx}.{base_image['ext']}"
                img_path = str(ASSET_DIR / img_filename)
                
                with open(img_path, "wb") as f:
                    f.write(base_image["image"])
                page_asset_paths.append(img_path)

            primary_asset = page_asset_paths[0] if page_asset_paths else ""

            # Split Text & Map Metadata
            splits = text_splitter.split_text(cleaned_text)
            for split in splits:
                is_table = "|" in split and split.count("|") > 4
                content_type = "TABLE" if is_table else "TEXT"

                processed_chunks.append({
                    "id": f"chunk_{chunk_counter}",
                    "text": split,
                    "type": content_type,
                    "page": page_num,
                    "source": doc_name,
                    "asset_path": primary_asset
                })
                chunk_counter += 1

    # Generate Embeddings & Store into LanceDB
    print(f"[RAG BUILD] Embedding {len(processed_chunks)} total chunks via nomic-embed-text...")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db_records = []

    for idx, chunk in enumerate(processed_chunks, 1):
        prefixed_text = f"search_document: {chunk['text']}"
        vector = embeddings.embed_query(prefixed_text)
        
        db_records.append({
            "id": chunk["id"],
            "text": chunk["text"],
            "vector": vector,
            "type": chunk["type"],
            "page": chunk["page"],
            "source": chunk["source"],
            "asset_path": chunk["asset_path"]
        })
        if idx % 200 == 0 or idx == len(processed_chunks):
            print(f" -> Embedded [{idx}/{len(processed_chunks)}] chunks...")

    db = lancedb.connect(DB_PATH)
    table = db.create_table(TABLE_NAME, data=db_records, mode="overwrite")
    print(f"\n[RAG BUILD] Database build complete! Stored into '{TABLE_NAME}'.\n")

if __name__ == "__main__":
    build_vector_database()
print("RAG build successfully")