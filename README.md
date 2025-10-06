# Sparky AI Assistant - Secure Web Interface

A secure, web-based AI assistant with personalized memory powered by Google OAuth authentication, Supabase database, and OpenAI embeddings.

### 4. Database Setup

Run the Supabase migrations to set up the database:

```bash
cd supabase
supabase db reset
```

### 5. Import Your ChatGPT Data (Optional)

If you downloaded your ChatGPT export data:

```bash
# Import with summarization (recommended for cost & noise control)
python scripts/load_memory_batch.py path/to/conversations.json --source chatgpt --tags "imported,chatgpt" --summarize --project-id "personal"

# Import other text files with project scoping
python scripts/load_memory_batch.py your_notes.txt --tags "personal,notes" --project-id "personal"
```

### 6. Pre-flight Check

Run deployment checks before starting:

```bash
# Verify environment, database, and embeddings
python scripts/deploy.py --check

# Quick embedding dimensions test (text-embedding-3-small = 1536 dims)
python -c "from app.config import config; print(f'Embedding model: {config.embedding_model}, dims: {config.embedding_dimensions}')"
```

### 7. Run the Application

```bash
python app/main.py
```

Visit `http://localhost:8080` and sign in with Google!

## Features

A secure, web-based AI assistant with personalized memory powered by Google OAuth authentication, Supabase database, and OpenAI embeddings.

- **🔐 Secure Authentication**: Google OAuth 2.0 with JWT session management
- **🧠 Personalized Memory**: AI assistant remembers your conversations and preferences
- **💬 Web Chat Interface**: Clean, responsive web interface for natural conversations
- **📱 Mobile Ready**: Deployable to Vercel for mobile access anywhere
- **🔍 Semantic Search**: Vector similarity search using OpenAI embeddings for context-aware responses
- **📊 Memory Management**: Structured storage with metadata, importance levels, and tagging
- **⚡ Async Operations**: High-performance async/await architecture
- **🛡️ Security First**: No hardcoded secrets, secure session management, RLS database policies

## Quick Start

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd sparky-sandbox
pip install -r requirements.txt
```

### 2. Download Your ChatGPT Memory Data

To make Sparky truly personalized, you can import your existing ChatGPT conversation history:

1. **Export from ChatGPT**:
   - Go to [ChatGPT Settings](https://chatgpt.com/settings) 
   - Navigate to "Data controls" → "Export data"
   - Request your data export (may take some time)
   - Download the ZIP file when ready

2. **Extract conversations**:
   - Unzip the downloaded file
   - Look for `conversations.json` in the export
   - This contains all your ChatGPT conversation history

3. **Import to Sparky** (after setup):
   ```bash
   # Use the batch loading script to import your conversations
   python scripts/load_memory_batch.py path/to/conversations.json --source chatgpt
   ```

### 3. Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Fill in your credentials in `.env`:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL  
- `SUPABASE_KEY`: Your Supabase **anon** key (safe for browser use)
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key (server-side only, DO NOT expose to browser)
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `JWT_SECRET`: Random secret for session tokens

**🚨 CRITICAL SECURITY**: 
- **Anon key**: Safe for browser/frontend use (limited by RLS policies)
- **Service role key**: Server-side only, bypasses RLS - NEVER expose to client
- Always use anon key in browser code, service role only in secure server contexts



## Deployment

### Recommended Platforms for Python Apps

**Render, Railway, or Fly.io** (Recommended for long-running Python apps):
```bash
# Render: Connect your GitHub repo at render.com
# Railway: railway login && railway new
# Fly.io: fly deploy
```

**Vercel with FastAPI** (Alternative - requires refactoring to serverless functions):
```bash
# Would need to restructure app/main.py as FastAPI serverless functions
npm install -g vercel
vercel
```

**Note**: Current `app/main.py` is designed as a long-running aiohttp server, not serverless functions.

## Project Structure

```
sparky-sandbox/
├── app/                     # Main application
│   ├── main.py             # Web server and routes
│   ├── config.py           # Configuration management
│   ├── auth/               # Authentication system
│   │   └── google.py       # Google OAuth handler
│   ├── chat/               # Chat functionality
│   │   └── routes.py       # Chat API endpoints
│   └── memory/             # Memory system
│       └── utils.py        # Memory utilities
├── templates/              # HTML templates
│   ├── login.html         # Login page
│   └── chat.html          # Chat interface
├── static/                # Static assets
│   └── images/
├── scripts/               # Utility scripts
│   ├── inject_memory.py   # Manual memory injection
│   ├── retrieve_similar.py # Memory search
│   ├── load_memory_batch.py # Batch importing
│   └── ...                # Other utilities
├── tests/                 # Test files
├── docs/                  # Documentation
├── supabase/             # Database configuration
│   └── migrations/       # Database migrations
├── requirements.txt      # Python dependencies
├── vercel.json          # Deployment config
└── .env.example         # Environment template
```

## How It Works

### Authentication Flow
1. **Login**: User clicks "Sign in with Google"
2. **OAuth**: Google OAuth 2.0 handles authentication
3. **Session**: JWT token created and stored in encrypted cookie
4. **Security**: All API calls require valid authentication

### Chat Experience
1. **Personalized Responses**: AI remembers your conversation history and preferences
2. **Context Awareness**: Previous memories enhance response quality
3. **Memory Creation**: Important information automatically stored for future reference
4. **Smart Retrieval**: Semantic search finds relevant memories based on conversation context

### Memory System
- **Automatic**: Conversations automatically create memories
- **Structured**: Memories include type, importance, tags, and metadata
- **Searchable**: Vector embeddings enable semantic similarity search
- **Personal**: Row-level security ensures private, user-specific memories

## API Endpoints

### Authentication
- `GET /` - Login page (redirects to chat if authenticated)
- `GET /api/auth/google` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - OAuth callback handler
- `POST /api/auth/logout` - Sign out and clear session

### Chat
- `GET /chat` - Chat interface (requires authentication)
- `POST /api/chat` - Send message and get AI response
- `GET /api/memories/similar` - Search memories (with query parameter)

## Memory Import Options

Sparky can import memories from various sources to personalize your experience:

### ChatGPT Export Data
```bash
# Import with summarization (recommended - reduces cost & noise)
python scripts/load_memory_batch.py conversations.json --source chatgpt --tags "chatgpt,conversations" --summarize --project-id "personal"

# Full import (expensive, high-volume)
python scripts/load_memory_batch.py conversations.json --source chatgpt --tags "chatgpt,conversations" --project-id "personal"
```

### Text Files
```bash
# Import personal notes, documents, or any text content with project scoping
python scripts/load_memory_batch.py my_notes.txt --tags "personal,notes" --importance 4 --project-id "personal"
```

### Manual Memory Injection
```bash
# Add specific memories with project scoping
python scripts/inject_memory.py "User prefers dark mode interfaces" --type preference --importance 3 --project-id "personal"
python scripts/inject_memory.py "Lives in San Francisco, works in tech" --type biographical --tags "location,work" --project-id "personal"
```

### Supported Import Formats
- **JSON**: ChatGPT exports, structured conversation data
- **TXT**: Plain text files, notes, documents  
- **MD**: Markdown files with preserved formatting

## Utility Scripts

The `scripts/` directory contains utilities for advanced memory management:

```bash
# Pre-flight deployment checks
python scripts/deploy.py --check

# Manually inject memories with project scoping
python scripts/inject_memory.py "User prefers dark mode" --type preference --project-id "personal"

# Search existing memories within project
python scripts/retrieve_similar.py "interface preferences" --project-id "personal"

# Batch import with summarization and project scoping
python scripts/load_memory_batch.py notes.txt --tags "important" --summarize --project-id "work"

# Check system status
python scripts/test_connectivity.py
```

## Connectors

### MCP Store Message Tool

For selective memory capture from other chat interfaces:

```bash
# Store specific chat snippets in memory-drops/ for later processing
# Use the store_message MCP tool to push selected conversations
# Files in memory-drops/ can then be batch imported:
python scripts/load_memory_batch.py memory-drops/selected_chat.md --tags "mcp,selected" --project-id "personal"
```

**Benefits**: Opt-in memory capture, no auto-siphoning, maintains conversation context.

## Security Features

- ✅ **Google OAuth 2.0**: Industry-standard authentication
- ✅ **JWT Sessions**: Secure, stateless session management  
- ✅ **Encrypted Cookies**: Session data protected with encryption
- ✅ **Environment Variables**: No hardcoded secrets
- ✅ **Row Level Security**: Database policies isolate user data
- ✅ **HTTPS Ready**: Secure deployment configuration
- ✅ **Input Validation**: All user inputs validated and sanitized

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
cd supabase && supabase db reset

# Start development server
python app/main.py
```

### Testing
```bash
# Run test suite
python -m pytest tests/

# Test specific components
python tests/test_connectivity.py
python tests/test_memory_system.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for personal use. See documentation for deployment guidelines.

---

**🚀 Ready to deploy!** This project is optimized for Render/Railway/Fly.io deployment with proper security, scalability, and mobile support. Vercel deployment possible with FastAPI refactoring.
