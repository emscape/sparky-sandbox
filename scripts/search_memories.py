#!/usr/bin/env python3
"""Simple memory search script for querying your Sparky conversations."""

import argparse
import asyncio
import sys
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from supabase import create_client, Client
from config import config
from utils import get_embedding


class MemorySearcher:
    """Simple memory search interface."""

    def __init__(self):
        """Initialize clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for memories similar to the query."""
        print(f"🔍 Searching for: '{query}'")
        print(f"   Generating embedding...")
        
        # Generate embedding for the query
        query_embedding = await get_embedding(query, self.openai_client)
        
        print(f"   Searching database...")
        
        # Search using Supabase RPC function
        try:
            result = self.supabase.rpc('match_memories', {
                'query_embedding': query_embedding,
                'match_count': limit
            }).execute()
            
            if not result.data:
                print("\n❌ No results found.")
                return []
            
            print(f"\n✅ Found {len(result.data)} results:\n")
            print("=" * 100)
            
            for i, memory in enumerate(result.data, 1):
                similarity = memory.get('similarity', 0)
                content = memory.get('content', '')
                metadata = memory.get('metadata', {})
                tags = memory.get('tags', [])
                importance = memory.get('importance', 0)
                created = memory.get('created_at', '')
                
                # Extract conversation info from metadata
                conv_title = metadata.get('conversation_title', 'Unknown')
                role = metadata.get('role', 'unknown')
                
                print(f"\n{i}. 📊 Similarity: {similarity:.4f} | ⭐ Importance: {importance}/5")
                print(f"   💬 From: '{conv_title}'")
                print(f"   👤 Role: {role}")
                if tags:
                    print(f"   🏷️  Tags: {', '.join(tags)}")
                print(f"   📅 Date: {created[:10] if created else 'Unknown'}")
                print(f"\n   📝 Content:")
                # Show first 300 chars
                content_preview = content[:300] + "..." if len(content) > 300 else content
                print(f"   {content_preview}")
                print("-" * 100)
            
            return result.data
            
        except Exception as e:
            print(f"\n❌ Search error: {e}")
            return []


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Search your Sparky conversation memories',
        epilog='Examples:\n'
               '  python search_memories.py "python coding"\n'
               '  python search_memories.py "Girls Who Code" --limit 10\n'
               '  python search_memories.py "AI projects"',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('query', help='What to search for')
    parser.add_argument('--limit', type=int, default=5, 
                       help='Number of results (default: 5)')
    
    args = parser.parse_args()
    
    try:
        searcher = MemorySearcher()
        await searcher.search(args.query, args.limit)
    except KeyboardInterrupt:
        print("\n\n⏹️  Search cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

