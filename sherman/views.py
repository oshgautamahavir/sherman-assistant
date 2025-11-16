import json
from datetime import datetime
from typing import List, Dict

from supabase import create_client
from pinecone import Pinecone
from openai import OpenAI

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .utils import (
    hash_url, clean_text, chunk_text, 
    upsert_chunks_to_pinecone,
    fetch_and_parse_html, check_url_exists,
    search_similar_chunks, build_context,
    extract_source_urls, save_chat_exchange)

supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
pinecone_client = Pinecone(api_key=settings.PINECONE_KEY)
openai_client = OpenAI(api_key=settings.OPENAI_KEY, organization=settings.OPENAI_ORGANIZATION)

pinecone_index = pinecone_client.Index(settings.PINECONE_INDEX_NAME)


@csrf_exempt
def scrape_api(request):
    urls = [
        'https://www.shermanstravel.com/cruise-destinations/alaska-itineraries',
        'https://www.shermanstravel.com/cruise-destinations/caribbean-and-bahamas',
        'https://www.shermanstravel.com/cruise-destinations/hawaiian-islands',
        'https://www.shermanstravel.com/cruise-destinations/northern-europe'
    ]

    results = []
    
    for url in urls:
        try:
            title_text, main_content = fetch_and_parse_html(url)
            cleaned_text = clean_text(main_content)
            chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=200)
            url_hash = hash_url(url)

            if check_url_exists(pinecone_index, url_hash):
                results.append({
                    'url': url,
                    'status': 'skipped',
                    'message': 'URL already exists in Pinecone (de-duped)',
                    'url_hash': url_hash,
                })
                continue

            metadata = {
                'url': url,
                'url_hash': url_hash,
                'title': title_text,
                'source': 'sherman-travel'
            }

            upserted_count = upsert_chunks_to_pinecone(
                pinecone_index=pinecone_index,
                url_hash=url_hash,
                chunks=chunks,
                metadata=metadata,
                openai_client=openai_client
            )

            results.append({
                'url': url,
                'status': 'success',
                'url_hash': url_hash,
                'title': title_text,
                'chunks_created': len(chunks),
                'chunks_upserted': upserted_count,
                'content_length': len(cleaned_text)
            })

        except Exception as e:
            results.append({
                'url': url,
                'status': 'error',
                'message': f'Error processing: {str(e)}'
            })

    return JsonResponse({
        'status': 'completed',
        'results': results,
        'total_urls': len(urls),
        'successful': sum(1 for r in results if r.get('status') == 'success'),
        'skipped': sum(1 for r in results if r.get('status') == 'skipped'),
        'errors': sum(1 for r in results if r.get('status') == 'error')
    })


@csrf_exempt
def chat_api(request):
    try:
        question = request.POST.get('question')

        question_embedding = openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=question
        ).data[0].embedding

        similar_chunks = search_similar_chunks(
            pinecone_index=pinecone_index,
            question_embedding=question_embedding,
        )

        context = build_context(similar_chunks)

        system_prompt = """You are a helpful assistant from Sherman Travel that answers questions strictly based on the provided context. 
    If the answer cannot be found in the context, you must say so. Do not use any information outside of the provided context.
    Be concise and accurate in your responses. However, it is okay to have small talks with the user like replying to their messages like "Hello! How are you?" or "I'm doing great! How about you?"
    as long as you suggest where to go on a cruise or ask them about their preferences after the small talk.

    IMPORTANT: Always include source URLs in square brackets at the end of your answer. Format: [url1] [url2] [url3]
    Include one or more URLs depending on how many sources were used to answer the question. If multiple sources were used, include all relevant URLs."""
        
        user_prompt = f"""Context information:
    {context}

    Question: {question}

    Please answer the question based strictly on the context provided above. 

    CRITICAL FORMATTING REQUIREMENTS:
    1. Provide your answer first
    2. At the end of your answer, include all source URLs, separated by new lines
    3. Format: https://example.com/page1 \nhttps://example.com/page2
    4. Include one or more URLs depending on how many sources from the context were used

    Example format:
    Your answer text here. https://www.shermanstravel.com/cruise-destinations/alaska \nhttps://www.shermanstravel.com/cruise-destinations/caribbean
    """
        response = openai_client.chat.completions.create(
            model=settings.MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        answer = response.choices[0].message.content.strip()

        stripped_answer, source_urls = extract_source_urls(answer)
        
        save_chat_exchange(
            question=question,
            answer=stripped_answer,
            source_urls=source_urls,
            supabase_client=supabase_client
        )

        return JsonResponse({
            'status': 200,
            'answer': stripped_answer,
            'question': question,
            'source_urls': source_urls
        })

    except Exception as e:
        return JsonResponse({
            'status': 500,
            'message': str(e)
        })


@csrf_exempt
def history_api(request):
    try:
        history = (
            supabase_client.table("chat_exchanges")
            .select("*")
            .order("id", desc=True)
            .limit(50)
            .execute()
        )

        return JsonResponse({
            'status': 200,
            'history': history.data
        })

    except Exception as e:
        return JsonResponse({
            'status': 500,
            'message': str(e)
        })
