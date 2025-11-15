# Sherman Travel Assistant

A RAG (Retrieval Augmented Generation) application that answers questions about cruise destinations using OpenAI, Pinecone, and Supabase.

## Project Structure

```
sherman-assistant/
├── backend/          # Django backend API
├── frontend/         # Vue 3 frontend
├── sherman/          # Django app with API endpoints
└── requirements.txt  # Python dependencies
```

## Setup

### Backend Setup

1. Create a virtual environment (if not already created):
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your API keys:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_KEY=your_openai_key
OPENAI_ORGANIZATION=your_openai_org
PINECONE_KEY=your_pinecone_key
PINECONE_INDEX=your_pinecone_index_name
MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
```

5. Run database migrations:
```bash
python manage.py migrate
```

6. Start the Django development server:
```bash
python manage.py runserver
```

The backend API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

- `POST /api/chat/` - Send a chat message
- `GET /api/history/` - Get chat history
- `POST /api/scrape/` - Scrape and index URLs

## Development

### Running Both Servers

You'll need two terminal windows:

**Terminal 1 (Backend):**
```bash
python manage.py runserver
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## Technologies Used

- **Backend**: Django, OpenAI API, Pinecone, Supabase
- **Frontend**: Vue 3, Vite, Axios
- **Vector Database**: Pinecone
- **Database**: Supabase (PostgreSQL)

## License

MIT

