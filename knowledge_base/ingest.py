import os
import glob
import hashlib
import chromadb
from sentence_transformers import SentenceTransformer

# Constants
CHROMA_STORE_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_sops")
COLLECTION_NAME = "sops"
MODEL_NAME = "all-MiniLM-L6-v2"

# Initialize singletons (these will download on first run, then run offline)
print(f"Loading embedding model '{MODEL_NAME}'... (this may download on first run)")
model = SentenceTransformer(MODEL_NAME)

print(f"Initializing local ChromaDB at '{CHROMA_STORE_DIR}'...")
client = chromadb.PersistentClient(path=CHROMA_STORE_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Splits text into overlapping word-based chunks.
    ~400 words each, ~50 word overlap between consecutive chunks.
    """
    words = text.split()
    chunks = []
    
    if not words:
        return chunks
        
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start += (chunk_size - overlap)
        
    return chunks

def ingest_document(
    file_path: str,
    *,
    document_id: str | None = None,
    chat_id: str | None = None,
    source_name: str | None = None,
    shared: bool = False,
) -> int:
    """
    Reads a single .txt file, chunks it, generates embeddings, 
    and stores them into ChromaDB.
    Returns the number of chunks stored.
    """
    filename = source_name or os.path.basename(file_path)
    print(f"  -> Ingesting {filename}...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    chunks = chunk_text(content)
    if not chunks:
        print(f"     [Warning] No content found in {filename}")
        return 0
        
    embeddings = model.encode(chunks).tolist()
    
    ids = []
    metadatas = []
    
    # Filename-based IDs caused one upload to overwrite another upload with
    # the same name.  A stable document ID makes re-indexing idempotent while
    # keeping independently uploaded files isolated.
    stable_id = document_id or hashlib.sha256(
        os.path.abspath(file_path).encode("utf-8")
    ).hexdigest()
    for i in range(len(chunks)):
        ids.append(f"{stable_id}_chunk_{i}")
        metadata = {
            "source": filename,
            "chunk_index": i,
            "document_id": stable_id,
            "shared": shared,
        }
        if chat_id:
            metadata["chat_id"] = chat_id
        metadatas.append(metadata)
        
    # Add to Chroma
    # We use upsert so re-running this script updates existing chunks instead of crashing
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )
    
    print(f"     [OK] Stored {len(chunks)} chunks.")
    return len(chunks)

def ingest_all() -> None:
    """
    Finds every .txt file under data/sample_sops/ and ingests each one.
    """
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found at {DATA_DIR}")
        return
        
    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    if not txt_files:
        print(f"No .txt files found in {DATA_DIR}")
        return
        
    print(f"\nStarting ingestion of {len(txt_files)} documents...")
    total_chunks = 0
    
    for file_path in txt_files:
        chunks_added = ingest_document(file_path, shared=True)
        total_chunks += chunks_added
        
    print(f"\n[SUCCESS] Ingestion complete! Total chunks stored in ChromaDB: {total_chunks}")

if __name__ == "__main__":
    ingest_all()
