from supabase import create_client
from pinecone import Pinecone
from openai import OpenAI

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .utils import (
    hash_url, clean_text, chunk_text, 
    upsert_chunks_to_pinecone,
    fetch_and_parse_html, check_url_exists
)

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
