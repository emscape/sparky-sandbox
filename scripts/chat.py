#!/usr/bin/env python3
"""
Interactive chat interface with memory retrieval.
Your personal Sparky replacement that uses your ingested conversation history.
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any

from openai import AsyncOpenAI
from supabase import create_client, Client
from config import config
from utils import get_embedding


class MemoryChat:
    """Chat interface with memory-augmented responses."""

    def __init__(self):
        """Initialize clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
        self.conversation_history = []

    async def retrieve_relevant_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for context."""
        try:
            # Generate embedding for the query
            query_embedding = await get_embedding(query, self.openai_client)
            
            # Search using Supabase RPC function
            result = self.supabase.rpc('match_memories', {
                'query_embedding': query_embedding,
                'match_count': limit
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"⚠️  Memory retrieval error: {e}")
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

    async def chat(self, user_message: str, use_memory: bool = True) -> str:
        """Send a message and get a response with memory context."""
        
        # Retrieve relevant memories
        memories = []
        if use_memory:
            print("🔍 Searching memories...", end=" ", flush=True)
            memories = await self.retrieve_relevant_memories(user_message, limit=5)
            print(f"Found {len(memories)} relevant memories.")
        
        # Build the system prompt with memory context
        system_prompt = """You are Sparky, Emily's personal AI assistant. You have access to memories from all of Emily's past conversations with you.

Key facts about Emily:
- She's a teacher who runs a Girls Who Code club
- She works on various coding projects including DataScout
- She's interested in AI, agentic systems, and educational technology
- She values practical, actionable advice

Use the provided memories to give contextual, personalized responses. Reference past conversations when relevant."""

        if memories:
            memory_context = self.format_memories_for_context(memories)
            system_prompt += f"\n\n{memory_context}"
        
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build messages for API call
        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history
        ]
        
        # Get response from OpenAI
        try:
            print("💭 Thinking...", end=" ", flush=True)
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # or "gpt-4o-mini" for cheaper/faster
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            print("✓")
            return assistant_message
            
        except Exception as e:
            print(f"\n❌ Error getting response: {e}")
            return "Sorry, I encountered an error. Please try again."

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print("🗑️  Conversation history cleared.")


async def main():
    """Main interactive chat loop."""
    print("=" * 80)
    print("✨ SPARKY - Your Personal AI Assistant with Memory")
    print("=" * 80)
    print("\nCommands:")
    print("  /clear  - Clear conversation history")
    print("  /nomem  - Send next message without memory retrieval")
    print("  /exit   - Exit chat")
    print("\nType your message and press Enter to chat.")
    print("=" * 80)
    print()
    
    chat = MemoryChat()
    use_memory_next = True
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == '/exit':
                print("\n👋 Goodbye!")
                break
            elif user_input.lower() == '/clear':
                chat.clear_history()
                continue
            elif user_input.lower() == '/nomem':
                use_memory_next = False
                print("🔕 Next message will not use memory retrieval.")
                continue
            
            # Get response
            response = await chat.chat(user_input, use_memory=use_memory_next)
            
            # Reset memory flag
            use_memory_next = True
            
            # Print response
            print(f"\nSparky: {response}\n")
            print("-" * 80)
            print()
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

