#!/usr/bin/env python3
"""Memory injection script for AI assistant memory system."""

import argparse
import asyncio
import os
import sys
from typing import List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from supabase import create_client, Client
from app.config import config, parse_tags, validate_importance
from app.memory.utils import get_embedding


class MemoryInjector:
    """Handles memory injection with embedding generation."""

    def __init__(self) -> None:
        """Initialize OpenAI and Supabase clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)

    async def store_memory(self, memory_text: str, embedding: List[float],
                           memory_type: str = 'fact', tags: Optional[List[str]] = None,
                           source: str = 'manual', importance: int = 1, 
                           project_id: Optional[str] = None) -> dict:
        """Store memory with metadata in Supabase."""
        try:
            data = {
                "content": memory_text,
                "embedding": embedding,
                "type": memory_type,
                "source": source,
                "importance": importance
                # user_id will be automatically set by the database default (auth.uid())
            }

            if tags:
                data["tags"] = tags
                
            if project_id:
                data["project_id"] = project_id

            result = self.supabase.table(config.memory_table).insert(data).execute()

            if result.data:
                return result.data[0]
            else:
                raise RuntimeError("No data returned from insert operation")

        except Exception as e:
            raise RuntimeError(f"Failed to store memory: {e}")

    async def inject_memory(self, memory_text: str, memory_type: str = 'fact',
                           tags: Optional[List[str]] = None, source: str = 'manual',
                           importance: int = 1, project_id: Optional[str] = None) -> dict:
        """Complete memory injection pipeline with metadata."""
        if not memory_text.strip():
            raise ValueError("Memory text cannot be empty")

        print(f"Generating embedding for: {memory_text[:50]}...")
        embedding = await get_embedding(memory_text, self.openai_client)

        print("Storing memory in database...")
        result = await self.store_memory(memory_text, embedding, memory_type, tags, source, importance, project_id)

        print(f"✅ Memory stored successfully!")
        print(f"   ID: {result.get('id')}")
        print(f"   Type: {result.get('type')}")
        print(f"   Tags: {result.get('tags', [])}")
        print(f"   Source: {result.get('source')}")
        print(f"   Importance: {result.get('importance')}")
        if project_id:
            print(f"   Project: {result.get('project_id')}")
        return result


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Inject memory with metadata into AI memory system')
    parser.add_argument('content', help='Memory content to store')
    parser.add_argument('--type', default='fact',
                       help='Memory type (fact, identity, preference, log, etc.)')
    parser.add_argument('--tags', help='Comma-separated tags (e.g., "perkTracker,fiona")')
    parser.add_argument('--source', default='manual',
                       help='Memory source (manual, chat, blog, email, etc.)')
    parser.add_argument('--importance', type=int, default=1,
                       help='Importance level (1=low to 5=critical)')
    parser.add_argument('--project-id', help='Project identifier for memory partitioning (e.g., "personal", "work", "blog")')
    return parser.parse_args()


async def main() -> None:
    """Main function to handle command line input."""
    try:
        args = parse_arguments()

        # Validate importance
        importance = validate_importance(args.importance)

        # Parse tags
        tags = parse_tags(args.tags) if args.tags else None

        injector = MemoryInjector()
        await injector.inject_memory(
            memory_text=args.content,
            memory_type=args.type,
            tags=tags,
            source=args.source,
            importance=importance,
            project_id=args.project_id
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
