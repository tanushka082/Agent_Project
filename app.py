import pymupdf4llm 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
import lancedb
from dotenv import load_dotenv

load_dotenv()

md_text = pymupdf4llm.to_markdown("Data/Nissan Car Fault Codes DTC.pdf", preserve_tables=True)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "]
)
raw_splits = text_splitter.split_text(md_text)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

document_texts = [f"search_document: {chunk}" for chunk in raw_splits]
document_vectors = embeddings.embed_documents(document_texts)

data = []
for i, (chunk, vector) in enumerate(zip(raw_splits, document_vectors)):
    data.append({
        "id": i,
        "text": chunk,  
        "vector": vector,
        "source": "Nissan Car Fault Codes DTC.pdf"
    })

# 4. STORE IN LANCEDB 
db = lancedb.connect("lancedb")
table = db.create_table("diagnostic_chunks", data=data, mode="overwrite")
print(f"Stored {len(data)} structured chunks in LanceDB")
query = "What are the possible causes of P0300?"
query_vector = embeddings.embed_query(f"search_query: {query}")

results = (
    table.search(query_vector)
    .metric("cosine")
    .limit(3)
    .to_list()
)

# Display Results
for i, result in enumerate(results, 1):
    print(f"\n-------------------")
    print(f"Result: {i}")
    print(f"Distance: {result.get('_distance')}")
    print(f"Text:\n{result.get('text')}")