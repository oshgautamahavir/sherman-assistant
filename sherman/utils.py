
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
    
    content_elements = soup.select('article')
    all_texts = [elem.get_text(separator=' ', strip=True) for elem in content_elements]
    main_content = ' '.join(all_texts)
    
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
                'text': chunk
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


def search_similar_chunks(
    pinecone_index: Pinecone,
    question_embedding: List[float],
) -> List[Dict]:
        results = pinecone_index.query(
            vector=question_embedding,
            include_metadata=True,
            top_k=5
        )
        
        matched_chunks = []
        for match in results.matches:
            if match.score >= 0.1:
                matched_chunks.append({
                    'id': match.id,
                    'score': match.score,
                    'text': match.metadata.get('text', ''),
                    'url': match.metadata.get('url', ''),
                    'title': match.metadata.get('title', ''),
                    'chunk_index': match.metadata.get('chunk_index', 0),
                    'metadata': match.metadata
                })
        
        return matched_chunks


def build_context(similar_chunks: List[Dict]) -> str:
    chunks_by_url = {}
    for chunk in similar_chunks:
        chunk_text = chunk.get('text', '')
        url = chunk.get('url', '')
        title = chunk.get('title', '')

        if chunk_text:
            if url not in chunks_by_url:
                chunks_by_url[url] = {
                    'title': title,
                    'chunks': []
                }
            chunks_by_url[url]['chunks'].append(chunk_text)
    
    # Build context string grouped by URL
    context_parts = []
    for url, data in chunks_by_url.items():
        title = data['title']
        chunks = data['chunks']
        
        context_parts.append(f"Source: {title} ({url})")
        
        context_parts.extend(chunks)
        context_parts.append("")
    
    return '\n\n'.join(context_parts).strip()


def extract_source_urls(answer: str) -> Tuple[str, List[str]]:
    pattern = r'https?://[^\s\n]+'
    matches = re.findall(pattern, answer)

    urls = []
    for url in matches:
        url = url.strip()
        url = url.rstrip('.,;:!?)')
        if url:
            urls.append(url)
    
    # Remove URLs from the answer text
    stripped_answer = answer
    for url in urls:
        # Remove the URL and any surrounding whitespace/newlines
        # Handle URLs that might be on their own line or inline
        stripped_answer = re.sub(r'\s*' + re.escape(url) + r'\s*\n?', ' ', stripped_answer)
        stripped_answer = re.sub(r'\n?\s*' + re.escape(url) + r'\s*', ' ', stripped_answer)
    
    # Clean up extra whitespace and newlines
    stripped_answer = re.sub(r'\n\s*\n+', '\n\n', stripped_answer)  # Multiple newlines to double
    stripped_answer = re.sub(r'[ \t]+', ' ', stripped_answer)  # Multiple spaces to single
    stripped_answer = re.sub(r'\n ', '\n', stripped_answer)  # Remove space after newline
    stripped_answer = stripped_answer.strip()

    return stripped_answer, urls


def save_chat_exchange(
    question: str,
    answer: str,
    source_urls: List[str],
    supabase_client
) -> bool:
    data = {
        'question': question,
        'answer': answer,
        'source_urls': source_urls,
    }

    supabase_client.table("chat_exchanges").insert(data).execute()
