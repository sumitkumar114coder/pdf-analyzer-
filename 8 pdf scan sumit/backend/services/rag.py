import os
import logging
import numpy as np
import faiss

from backend.services.embeddings import generate_embeddings_batch

logger = logging.getLogger(__name__)

# Constants for chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
VECTOR_DIMENSION = 768  # Dimension for models/text-embedding-004

def chunk_text(text: str, page_number: int) -> list[dict]:
    """
    Splits text into chunks of CHUNK_SIZE characters with CHUNK_OVERLAP overlap.
    Returns list of dicts: {"content": str, "page_number": int}
    """
    chunks = []
    text_length = len(text)
    
    if text_length == 0:
        return []

    # If text is shorter than chunk size, return it as a single chunk
    if text_length <= CHUNK_SIZE:
        return [{"content": text, "page_number": page_number}]

    start = 0
    while start < text_length:
        end = min(start + CHUNK_SIZE, text_length)
        chunk = text[start:end]
        chunks.append({
            "content": chunk,
            "page_number": page_number
        })
        # Move start pointer forward, respecting overlap
        start += (CHUNK_SIZE - CHUNK_OVERLAP)

    return chunks

def build_faiss_index(chunks: list[dict], index_path: str, api_key: str = None) -> bool:
    """
    Generates embeddings for chunks, builds a FAISS Flat Index with Inner Product (Cosine Similarity),
    and saves the index to disk.
    """
    if not chunks:
        logger.warning("No chunks provided to build FAISS index.")
        return False

    try:
        # Extract only content for embedding generation
        contents = [c["content"] for c in chunks]
        
        # Generate embeddings in batches of 32 to avoid rate/size limit issues
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(contents), batch_size):
            batch_texts = contents[i:i + batch_size]
            batch_embeds = generate_embeddings_batch(batch_texts, api_key=api_key)
            embeddings.extend(batch_embeds)

        embeddings_np = np.array(embeddings, dtype=np.float32)
        
        # L2 Normalization + IndexFlatIP yields exact Cosine Similarity
        faiss.normalize_L2(embeddings_np)
        
        # Create FAISS Index
        index = faiss.IndexFlatIP(VECTOR_DIMENSION)
        index.add(embeddings_np)
        
        # Write index file to disk
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(index, index_path)
        logger.info(f"FAISS index built and saved successfully to {index_path}.")
        return True
        
    except Exception as e:
        logger.error(f"Error building FAISS index: {e}")
        raise RuntimeError(f"FAISS building failed: {str(e)}")

def search_faiss_index(query_embedding: list[float], index_path: str, top_k: int = 5) -> list[int]:
    """
    Loads FAISS index from disk and searches for top_k similar vector indices.
    Returns a list of indices representing the matching chunks.
    """
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index file not found at: {index_path}")

    try:
        # Load the index
        index = faiss.read_index(index_path)
        
        # Convert query embedding to numpy array
        query_np = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_np)
        
        # Perform query
        # distances contain the similarity scores (since we used normalize_L2 and IndexFlatIP)
        # indices contain the index numbers of the matching database chunks
        scores, indices = index.search(query_np, min(top_k, index.ntotal))
        
        # Flatten and filter out invalid indices (-1 values)
        results = [int(idx) for idx in indices[0] if idx >= 0]
        return results
    except Exception as e:
        logger.error(f"Error searching FAISS index: {e}")
        return []
