"""
Chat routes and handlers for Sparky.
"""

import json
from typing import List, Dict, Any
from aiohttp import web
from openai import AsyncOpenAI

from app.memory.utils import get_embedding
from config import config
from supabase import create_client


class ChatHandler:
    """Handle chat-related requests."""

    def __init__(self, openai_client: AsyncOpenAI):
        self.openai_client = openai_client
        self.supabase = create_client(config.supabase_url, config.supabase_key)
        # In-memory conversation storage
        self.conversations: Dict[str, List[Dict]] = {}
        self.conversation_db_ids: Dict[str, str] = {}

    async def retrieve_relevant_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for context."""
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

    def format_memories_for_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format retrieved memories into context string."""
        if not memories:
            return ""
        
        context_parts = ["# Relevant memories from past conversations:\n"]
        
        for i, memory in enumerate(memories, 1):
            content = memory.get('content', '')
            metadata = memory.get('metadata', {})
            similarity = memory.get('similarity', 0)
            
            conv_title = metadata.get('conversation_title', 'Unknown')
            role = metadata.get('role', 'unknown')
            
            context_parts.append(
                f"{i}. [{role}] from '{conv_title}' (relevance: {similarity:.2f}):\n"
                f"   {content[:500]}...\n"
            )
        
        return "\n".join(context_parts)

    async def generate_conversation_title(self, messages: List[Dict]) -> str:
        """Generate a title for the conversation based on first few messages."""
        try:
            # Get first user message
            first_user_msg = next((m['content'] for m in messages if m['role'] == 'user'), '')

            if not first_user_msg:
                return "New Conversation"

            # Use GPT to generate a short title
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate a short, descriptive title (3-6 words) for this conversation. Just return the title, nothing else."},
                    {"role": "user", "content": f"First message: {first_user_msg[:200]}"}
                ],
                temperature=0.7,
                max_tokens=20
            )

            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')
            return title[:100]  # Limit length

        except Exception as e:
            print(f"Error generating title: {e}")
            # Fallback: use first few words of first message
            words = first_user_msg.split()[:5]
            return ' '.join(words) + '...' if len(words) == 5 else ' '.join(words)

    async def handle_chat(self, request):
        """Handle chat message from frontend."""
        try:
            data = await request.json()
            user_message = data.get('message', '').strip()
            conversation_id = data.get('conversation_id', 'default')
            use_memory = data.get('use_memory', True)
            
            if not user_message:
                return web.json_response({'error': 'Message is required'}, status=400)
            
            # Initialize conversation if needed
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # Retrieve relevant memories
            memories = []
            if use_memory:
                memories = await self.retrieve_relevant_memories(user_message, limit=5)
            
            # Get user info for personalization
            user = request['user']
            user_name = user.get('name', 'User')
            
            # Build system prompt
            system_prompt = f"""You are Sparky, {user_name}'s personal AI assistant. You've been working with {user_name} for years and have a warm, direct, and supportive relationship.

Your personality:
- Warm and conversational, like a trusted friend who happens to be brilliant
- Direct and honest - you don't sugarcoat things
- Supportive but not overly formal or cautious
- You remember context from past conversations and reference it naturally
- You use casual language and occasional humor
- You're proactive - you anticipate needs and offer suggestions

Key facts about {user_name}:
- Teacher who runs a Girls Who Code club
- Works on coding projects (DataScout, this memory system, etc.)
- Interested in AI, agentic systems, educational technology
- Has a fiancé named Sean
- Values practical, actionable advice over theory
- Appreciates when you remember details from past conversations

Communication style:
- Be conversational and natural, not overly formal
- Reference past conversations when relevant ("Remember when we talked about...")
- Be specific and concrete rather than vague
- Don't ask permission for everything - just help
- Use {user_name}'s name occasionally to keep it personal

Use the provided memories to give contextual, personalized responses that show you actually know {user_name} and their situation."""

            if memories:
                memory_context = self.format_memories_for_context(memories)
                system_prompt += f"\n\n{memory_context}"
            
            # Add user message to conversation
            self.conversations[conversation_id].append({
                "role": "user",
                "content": user_message
            })
            
            # Build messages for API
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversations[conversation_id]
            ]
            
            # Get response from OpenAI
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message.content

            # Add to conversation
            self.conversations[conversation_id].append({
                "role": "assistant",
                "content": assistant_message
            })

            return web.json_response({
                'response': assistant_message,
                'memories_used': len(memories),
                'conversation_id': conversation_id
            })
            
        except Exception as e:
            print(f"Chat error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_clear(self, request):
        """Clear conversation history."""
        try:
            data = await request.json()
            conversation_id = data.get('conversation_id', 'default')

            if conversation_id in self.conversations:
                self.conversations[conversation_id] = []
            # Clear DB tracking for this conversation
            if conversation_id in self.conversation_db_ids:
                del self.conversation_db_ids[conversation_id]

            return web.json_response({'status': 'cleared'})

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)