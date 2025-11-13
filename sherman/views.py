from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from supabase import create_client
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from django.conf import settings
from .vector_utils import (
    hash_url, clean_text, chunk_text, 
    init_pinecone, get_or_create_index,
    check_url_exists, upsert_chunks_to_pinecone
)

supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@csrf_exempt
def scrape_website(request):
    """
    Scrape a website and return structured data.

    - GET: /api/scrape/?url=https://example.com
    """
    # Get URL from request
    url = request.GET.get('url')
    
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid URL format. Please include http:// or https://'
        }, status=400)
    
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract structured data
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else None
        
        # Try to find main content (common patterns)
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
        
        # If no main content found, get body text
        if not main_content:
            body = soup.find('body')
            if body:
                # Remove script and style elements
                for script in body(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                main_content = body.get_text(separator=' ', strip=True)
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content') if meta_desc else None
        
        # Extract all links
        links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            if href:
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)
                links.append({
                    'text': text[:100] if text else '',  # Limit text length
                    'url': absolute_url
                })
        
        # Extract images
        images = []
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            alt = img.get('alt', '')
            if src:
                absolute_url = urljoin(url, src)
                images.append({
                    'alt': alt,
                    'url': absolute_url
                })
        
        # Extract headings
        headings = {}
        for level in range(1, 7):
            h_tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [h.get_text(strip=True) for h in h_tags if h.get_text(strip=True)]
        
        return JsonResponse({
            'status': 'success',
            'url': url,
            'data': {
                'title': title_text,
                'description': description,
                'content_preview': main_content[:1000] if main_content else None,  # First 1000 chars
                'content_length': len(main_content) if main_content else 0,
                'headings': headings,
                'links_count': len(links),
                'images_count': len(images),
                'links': links[:20],  # Limit to first 20 links
                'images': images[:10],  # Limit to first 10 images
            }
        })
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to fetch URL: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error scraping website: {str(e)}'
        }, status=500)


@csrf_exempt
def scrape_api(request):
    """
    Scrape Sherman Travel pages with full vector pipeline:
    1. Fetch - Get the webpage
    2. Clean - Remove HTML, scripts, normalize text
    3. Chunk - Split into smaller pieces
    4. Embed - Convert to vectors using OpenAI
    5. Upsert to Pinecone - Store vectors (de-dupe by URL hash)
    """
    urls = [
        'https://www.shermanstravel.com/cruise-destinations/alaska-itineraries',
        'https://www.shermanstravel.com/cruise-destinations/caribbean-and-bahamas',
        'https://www.shermanstravel.com/cruise-destinations/hawaiian-islands',
        'https://www.shermanstravel.com/cruise-destinations/northern-europe'
    ]
    
    # Initialize Pinecone
    try:
        pc = init_pinecone()
        index_name = settings.PINECONE_INDEX_NAME
        get_or_create_index(pc, index_name, dimension=1536)  # text-embedding-3-small = 1536 dims
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to initialize Pinecone: {str(e)}'
        }, status=500)
    
    results = []
    
    for url in urls:
        try:
            # Step 1: FETCH - Get the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Step 2: Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract title and main content
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "No Title"
            
            # Find main content
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
            
            if not main_content:
                results.append({
                    'url': url,
                    'status': 'skipped',
                    'message': 'No content found'
                })
                continue
            
            # Step 2: CLEAN - Clean the text
            cleaned_text = clean_text(main_content)
            
            if not cleaned_text or len(cleaned_text) < 100:
                results.append({
                    'url': url,
                    'status': 'skipped',
                    'message': 'Content too short after cleaning'
                })
                continue
            
            # Step 3: CHUNK - Split into chunks
            chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=200)
            
            if not chunks:
                results.append({
                    'url': url,
                    'status': 'skipped',
                    'message': 'No chunks created'
                })
                continue
            
            # Step 4 & 5: Check for duplicates and upsert
            url_hash = hash_url(url)
            
            # Check if URL already exists (de-dupe)
            if check_url_exists(pc, index_name, url_hash):
                results.append({
                    'url': url,
                    'status': 'skipped',
                    'message': 'URL already exists in Pinecone (de-duped)',
                    'url_hash': url_hash,
                    'chunks_count': len(chunks)
                })
                continue
            
            # Prepare metadata
            metadata = {
                'url': url,
                'url_hash': url_hash,
                'title': title_text,
                'source': 'sherman-travel'
            }
            
            # Step 4 & 5: EMBED & UPSERT to Pinecone
            upserted_count = upsert_chunks_to_pinecone(
                pc=pc,
                index_name=index_name,
                url=url,
                url_hash=url_hash,
                chunks=chunks,
                metadata=metadata
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
            
        except requests.exceptions.RequestException as e:
            results.append({
                'url': url,
                'status': 'error',
                'message': f'Failed to fetch: {str(e)}'
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
