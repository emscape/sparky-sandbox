"""Memory management utilities for Sparky AI Assistant."""

import asyncio
import tiktoken
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from supabase import create_client
from aiohttp import web

from config import config


async def get_embedding(text: str, client: AsyncOpenAI, model: str = "text-embedding-3-small") -> List[float]:
    """Get embedding for text using OpenAI API."""
    try:
        # Clean the text
        text = text.replace("\n", " ").strip()
        if not text:
            return []
            
        response = await client.embeddings.create(
            input=text,
            model=model
        )
        
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return []


class MemoryManager:
    """Manage memory operations for Sparky."""
    
    def __init__(self):
        self.supabase = create_client(config.supabase_url, config.supabase_key)
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    
    async def handle_search(self, request):
        """Search memories directly."""
        try:
            data = await request.json()
            query = data.get('query', '').strip()
            limit = data.get('limit', 5)

            if not query:
                return web.json_response({'error': 'Query is required'}, status=400)

            memories = await self.retrieve_memories(query, limit)

            return web.json_response({
                'memories': memories,
                'count': len(memories)
            })

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def retrieve_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for a query."""
        try:
            query_embedding = await get_embedding(query, self.openai_client)
            
            result = self.supabase.rpc('match_memories', {
                'query_embedding': query_embedding,
                'match_count': limit
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Memory retrieval error: {e}")
            return []