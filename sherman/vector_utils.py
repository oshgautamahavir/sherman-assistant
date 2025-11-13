"""
Utility functions for vector embeddings and Pinecone operations.
"""
import hashlib
import re
from typing import List, Dict
import openai
from pinecone import Pinecone, ServerlessSpec
from django.conf import settings


def hash_url(url: str) -> str:
    """
    Create a hash of the URL for de-duplication.
    
    Args:
        url: The URL to hash
        
    Returns:
        A SHA256 hash of the URL
    """
    return hashlib.sha256(url.encode()).hexdigest()


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap for better context preservation.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk (in characters)
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Get chunk
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind('\n', start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Get OpenAI embedding for text.
    
    Args:
        text: Text to embed
        model: OpenAI embedding model to use
        
    Returns:
        List of embedding values (vector)
    """
    if not settings.OPENAI_KEY:
        raise ValueError("OPENAI_KEY not configured in settings")
    
    client = openai.OpenAI(api_key=settings.OPENAI_KEY)
    
    # Clean and truncate text if needed (OpenAI has token limits)
    # text-embedding-3-small supports up to 8191 tokens
    text = text[:8000]  # Rough character limit to stay safe
    
    response = client.embeddings.create(
        model=model,
        input=text
    )
    
    return response.data[0].embedding


def init_pinecone() -> Pinecone:
    """
    Initialize and return Pinecone client.
    
    Returns:
        Pinecone client instance
    """
    if not settings.PINECONE_KEY:
        raise ValueError("PINECONE_KEY not configured in settings")
    
    pc = Pinecone(api_key=settings.PINECONE_KEY)
    return pc


def get_or_create_index(pc: Pinecone, index_name: str, dimension: int = 1536) -> None:
    """
    Get existing index or create a new one if it doesn't exist.
    
    Args:
        pc: Pinecone client
        index_name: Name of the index
        dimension: Dimension of vectors (1536 for text-embedding-3-small)
    """
    try:
        existing_indexes = [index.name for index in pc.list_indexes()]
    except Exception:
        existing_indexes = []
    
    if index_name not in existing_indexes:
        try:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=settings.PINECONE_ENVIRONMENT or 'us-east-1'
                )
            )
        except Exception as e:
            # Index might already exist, that's okay
            print(f"Note: Index creation: {e}")


def check_url_exists(pc: Pinecone, index_name: str, url_hash: str) -> bool:
    """
    Check if a URL hash already exists in Pinecone.
    
    Args:
        pc: Pinecone client
        index_name: Name of the index
        url_hash: Hash of the URL to check
        
    Returns:
        True if URL exists, False otherwise
    """
    try:
        index = pc.Index(index_name)
        # Fetch the vector by ID (using URL hash as ID)
        fetch_response = index.fetch(ids=[url_hash])
        return len(fetch_response['vectors']) > 0
    except Exception:
        # If fetch fails, assume it doesn't exist
        return False


def upsert_chunks_to_pinecone(
    pc: Pinecone,
    index_name: str,
    url: str,
    url_hash: str,
    chunks: List[str],
    metadata: Dict
) -> int:
    """
    Embed chunks and upsert them to Pinecone.
    
    Args:
        pc: Pinecone client
        index_name: Name of the index
        url: Original URL
        url_hash: Hash of the URL
        chunks: List of text chunks to embed and store
        metadata: Additional metadata to store with each chunk
        
    Returns:
        Number of chunks successfully upserted
    """
    index = pc.Index(index_name)
    
    vectors_to_upsert = []
    
    for i, chunk in enumerate(chunks):
        try:
            # Get embedding
            embedding = get_embedding(chunk)
            
            # Create vector ID: url_hash + chunk_index
            vector_id = f"{url_hash}_{i}"
            
            # Prepare metadata
            chunk_metadata = {
                **metadata,
                'chunk_index': i,
                'chunk_text': chunk[:500],  # Store first 500 chars for reference
                'total_chunks': len(chunks)
            }
            
            vectors_to_upsert.append({
                'id': vector_id,
                'values': embedding,
                'metadata': chunk_metadata
            })
        except Exception as e:
            print(f"Error embedding chunk {i}: {e}")
            continue
    
    # Upsert in batches (Pinecone recommends batches of 100)
    batch_size = 100
    upserted_count = 0
    
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        try:
            index.upsert(vectors=batch)
            upserted_count += len(batch)
        except Exception as e:
            print(f"Error upserting batch: {e}")
    
    return upserted_count

