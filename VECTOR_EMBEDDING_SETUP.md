# Vector Embedding & Pinecone Setup Guide

## What This Does

When you call `/api/scrape/`, it performs a complete vector pipeline:

1. **FETCH** - Downloads the webpage HTML
2. **CLEAN** - Removes HTML tags, scripts, normalizes text
3. **CHUNK** - Splits text into ~1000 character pieces with 200 char overlap
4. **EMBED** - Converts each chunk to a vector using OpenAI's `text-embedding-3-small` model
5. **UPSERT** - Stores vectors in Pinecone with metadata
6. **DE-DUPE** - Checks URL hash to avoid storing duplicates

## What Are Vector Embeddings?

- **Vector embeddings** are numerical representations of text that capture meaning
- Similar content = similar vectors
- Enables semantic search (find content by meaning, not just keywords)
- Example: "cruise to Alaska" and "Alaskan cruise vacation" would have similar vectors

## What Is Pinecone?

- **Pinecone** is a vector database optimized for similarity search
- Stores millions of vectors and finds similar ones quickly
- Perfect for building AI assistants that need to search through scraped content

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Keys

You need three API keys:

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env`:
   ```
   OPENAI_KEY=sk-your-key-here
   ```

#### Pinecone API Key
1. Go to https://www.pinecone.io/
2. Sign up for free account
3. Create a new index (or use existing)
4. Get your API key from the dashboard
5. Add to `.env`:
   ```
   PINECONE_KEY=your-pinecone-key
   PINECONE_ENVIRONMENT=us-east-1  # or your region
   PINECONE_INDEX_NAME=sherman-assistant
   ```

### 3. Your `.env` file should look like:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_KEY=sk-your-openai-key
PINECONE_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=sherman-assistant
```

## How It Works

### URL Hashing (De-duplication)

Each URL is hashed using SHA256. The hash is used as:
- The vector ID prefix (`{url_hash}_{chunk_index}`)
- A check to see if URL was already scraped

If a URL already exists, it's skipped to avoid duplicates.

### Chunking Strategy

- **Chunk size**: 1000 characters
- **Overlap**: 200 characters
- **Why overlap?** Preserves context at boundaries
- **Smart splitting**: Tries to break at sentence boundaries

### Embedding Model

- **Model**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Cost**: Very cheap (~$0.02 per 1M tokens)
- **Speed**: Fast

### Metadata Stored

Each vector chunk includes:
- `url` - Original URL
- `url_hash` - SHA256 hash of URL
- `title` - Page title
- `chunk_index` - Position in document
- `chunk_text` - First 500 chars (for reference)
- `total_chunks` - Total chunks from this URL
- `source` - "sherman-travel"

## Usage

### Call the API

```bash
GET http://localhost:8000/api/scrape/
```

### Response Example

```json
{
  "status": "completed",
  "results": [
    {
      "url": "https://www.shermanstravel.com/...",
      "status": "success",
      "url_hash": "abc123...",
      "title": "Alaska Itineraries",
      "chunks_created": 15,
      "chunks_upserted": 15,
      "content_length": 14500
    }
  ],
  "total_urls": 4,
  "successful": 3,
  "skipped": 1,
  "errors": 0
}
```

## Next Steps

Once you have vectors in Pinecone, you can:

1. **Build a search endpoint** - Query Pinecone with a question
2. **Create an AI assistant** - Use retrieved chunks as context for GPT
3. **Semantic search** - Find relevant content by meaning, not keywords

## Troubleshooting

### "OPENAI_KEY not configured"
- Make sure your `.env` file has `OPENAI_KEY=...`
- Restart your Django server after adding to `.env`

### "PINECONE_KEY not configured"
- Add `PINECONE_KEY=...` to `.env`
- Also add `PINECONE_ENVIRONMENT=us-east-1` (or your region)

### "Failed to initialize Pinecone"
- Check your API key is correct
- Verify your Pinecone account is active
- Check the region matches your index

### URLs being skipped as duplicates
- This is expected! The de-dupe prevents re-scraping
- To re-scrape, you'd need to delete vectors from Pinecone first

