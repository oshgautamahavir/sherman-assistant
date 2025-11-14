
import hashlib
import re
import requests

from typing import List, Dict, Tuple, Optional
from pinecone import Pinecone
from openai import OpenAI
from bs4 import BeautifulSoup


def fetch_and_parse_html(url: str) -> Tuple[Optional[str], Optional[str]]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    title = soup.find('title')
    title_text = title.get_text(strip=True) if title else "No Title"
    
    main_content = None
    content_selectors = [
        'main', 'article', '[role="main"]', 
        '.content', '.main-content', '#content',
        '.post-content', '.entry-content'
    ]
    
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            main_content = content.get_text(separator=' ', strip=True)
            break
    
    if not main_content:
        body = soup.find('body')
        if body:
            for script in body(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            main_content = body.get_text(separator=' ', strip=True)
    
    return title_text, main_content


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
    text = text.strip()
    
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
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


def get_embedding(text: str, openai_client: OpenAI) -> List[float]:
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )

    return response.data[0].embedding


def check_url_exists(pinecone_index: Pinecone, url_hash: str) -> bool:
    try:
        fetch_response = pinecone_index.fetch(ids=[url_hash])
        return len(fetch_response['vectors']) > 0
    except Exception:
        # If fetch fails, assume it doesn't exist
        return False


def upsert_chunks_to_pinecone(
    pinecone_index: Pinecone,
    url_hash: str,
    chunks: List[str],
    metadata: Dict,
    openai_client: OpenAI
) -> int:

    vectors_to_upsert = []
    
    for i, chunk in enumerate(chunks):
        try:
            embedding = get_embedding(chunk, openai_client)
            
            vector_id = f"{url_hash}_{i}"
            
            chunk_metadata = {
                **metadata,
                'chunk_index': i,
            }
            
            vectors_to_upsert.append({
                'id': vector_id,
                'values': embedding,
                'metadata': chunk_metadata
            })
        except Exception as e:
            print(f"Error embedding chunk {i}: {e}")
            continue
    
    batch_size = 100
    upserted_count = 0
    
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        try:
            pinecone_index.upsert(vectors=batch)
            upserted_count += len(batch)
        except Exception as e:
            print(f"Error upserting batch: {e}")
    
    return upserted_count
