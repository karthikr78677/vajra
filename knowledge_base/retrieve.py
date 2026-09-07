import os
import chromadb
from sentence_transformers import SentenceTransformer

# Constants
CHROMA_STORE_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
COLLECTION_NAME = "sops"
MODEL_NAME = "all-MiniLM-L6-v2"

# We must initialize lazily or handle cases where chroma store doesn't exist yet
# but for the retrieval, we expect it to exist.
try:
    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=CHROMA_STORE_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)
except Exception as e:
    # If the collection doesn't exist, this will throw an error. We handle it gracefully.
    collection = None
    print(f"Warning: Could not connect to ChromaDB collection. Ensure you run ingest.py first. Error: {e}")

def search_knowledge_base(
    query: str,
    k: int = 3,
    document_ids: list[str] | None = None,
    shared_only: bool = False,
) -> list[dict]:
    """
    Embeds the query, searches ChromaDB for the top-k closest chunks,
    and returns a list of dictionaries with search results.
    """
    if collection is None:
        return []
        

    query_embedding = model.encode([query]).tolist()

    # Build optional ChromaDB where filter
    where: dict | None = None
    conditions = []
    if document_ids:
        if len(document_ids) == 1:
            conditions.append({"document_id": {"$eq": document_ids[0]}})
        else:
            conditions.append({"document_id": {"$in": document_ids}})
    if shared_only:
        conditions.append({"shared": {"$eq": True}})

    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        where=where,
    )

    parsed_results = []

    # Chroma returns lists of lists (one list per query). Since we send 1 query, we take index [0]
    if not results['ids'] or not results['ids'][0]:
        return parsed_results

    for i in range(len(results['ids'][0])):
        parsed_results.append({
            "text": results['documents'][0][i],
            "source": results['metadatas'][0][i].get('source', 'unknown'),
            "document_id": results['metadatas'][0][i].get('document_id', ''),
            "chunk_index": results['metadatas'][0][i].get('chunk_index', i),
            "distance": results['distances'][0][i]
        })

    return parsed_results

def format_for_prompt(results: list[dict]) -> str:
    """
    Formats the search results into a clean string block to paste into an LLM prompt.
    """
    if not results:
        return "(no relevant company documents found)"
        
    formatted_chunks = []
    for r in results:
        formatted_chunks.append(f"[Source: {r['source']}]\n{r['text']}")
        
    return "\n\n".join(formatted_chunks)

if __name__ == "__main__":
    print("Testing Retrieval Module...\n")
    test_query = "What is the acceptable vibration level during a compressor restart?"
    print(f"Query: '{test_query}'\n")
    
    results = search_knowledge_base(test_query, k=3)
    
    if not results:
        print("No results found. Did you run ingest.py first?")
    else:
        for i, res in enumerate(results, 1):
            print(f"--- Result #{i} (Distance: {res['distance']:.4f}) ---")
            print(f"Source: {res['source']} (Chunk {res['chunk_index']})")
            print(f"Text snippet: {res['text'][:150]}...\n")
            
        print("\n--- Formatted Prompt Block ---")
        print(format_for_prompt(results))
