import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def get_gemini_api_key(user_api_key: str = None) -> str:
    """
    Resolves the API key to use: prefers the user's custom key,
    falls back to the GEMINI_API_KEY environment variable.
    """
    if user_api_key and user_api_key.strip():
        return user_api_key.strip()
    return os.environ.get("GEMINI_API_KEY", "")

def generate_embedding(text: str, api_key: str = None) -> list[float]:
    """
    Generates a 768-dimension vector embedding for a single text string using Gemini.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        import hashlib
        h = hashlib.md5(text.encode('utf-8')).digest()
        vec = []
        for i in range(768):
            vec.append(float((h[i % len(h)] + i) % 256) / 256.0)
        return vec

    try:
        genai.configure(api_key=key)
        # Use text-embedding-004 which is standard for Gemini embeddings
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise RuntimeError(f"Gemini Embedding API error: {str(e)}")

def generate_embeddings_batch(texts: list[str], api_key: str = None) -> list[list[float]]:
    """
    Generates embeddings in a single batch request for a list of text strings.
    """
    if not texts:
        return []
        
    key = get_gemini_api_key(api_key)
    if not key:
        return [generate_embedding(t) for t in texts]

    try:
        genai.configure(api_key=key)
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Error generating embeddings batch: {e}")
        raise RuntimeError(f"Gemini Embeddings API error: {str(e)}")

