#!/usr/bin/env python3
"""Memory retrieval script for AI assistant memory system."""

import argparse
import asyncio
import ast
import os
import sys
import time
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from openai import AsyncOpenAI
from supabase import create_client, Client
from app.config import config, parse_tags
from app.memory.utils import get_embedding


class MemoryRetriever:
    """Handles memory retrieval with similarity search and filtering."""

    def __init__(self) -> None:
        """Initialize OpenAI and Supabase clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)

    async def search_similar_memories(self, query_embedding: List[float], limit: int = 3,
                                      memory_type: Optional[str] = None,
                                      tags: Optional[List[str]] = None,
                                      importance_min: Optional[int] = None,
                                      project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar memories using vector similarity with filtering."""
        try:
            rpc_params = {
                'query_embedding': query_embedding,
                'match_count': limit,
            }
            
            query = self.supabase.rpc('match_memories', rpc_params)

            if memory_type:
                query = query.eq('type', memory_type)
            
            if importance_min:
                query = query.gte('importance', importance_min)

            if tags:
                for tag in tags:
                    query = query.contains('tags', [tag])
                    
            if project_id:
                query = query.eq('project_id', project_id)

            result = query.execute()

            if not result.data:
                return []

            return result.data

        except Exception as e:
            raise RuntimeError(f"Failed to search memories: {e}")

    async def retrieve_similar(self, query: str, limit: int = 3,
                              memory_type: Optional[str] = None,
                              tags: Optional[List[str]] = None,
                              importance_min: Optional[int] = None,
                              project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Complete memory retrieval pipeline with filtering."""
        if not query.strip():
            raise ValueError("Query cannot be empty")

        print(f"Searching for memories similar to: {query}")
        if memory_type:
            print(f"Filtering by type: {memory_type}")
        if tags:
            print(f"Filtering by tags: {', '.join(tags)}")
        if importance_min:
            print(f"Minimum importance: {importance_min}")
        if project_id:
            print(f"Project scope: {project_id}")

        # Generate embedding for query
        query_embedding = await get_embedding(query, self.openai_client)

        # Search for similar memories
        similar_memories = await self.search_similar_memories(
            query_embedding, limit, memory_type, tags, importance_min, project_id
        )

        if not similar_memories:
            print("No similar memories found.")
            return []

        print(f"\n🔍 Found {len(similar_memories)} similar memories:")
        print("=" * 80)

        for i, memory in enumerate(similar_memories, 1):
            similarity_score = memory.get('similarity', 'N/A')
            content = memory.get('content', 'No content')
            created_at = memory.get('created_at', 'Unknown date')
            memory_type_val = memory.get('type', 'Unknown')
            tags_val = memory.get('tags', [])
            source_val = memory.get('source', 'Unknown')
            importance_val = memory.get('importance', 'N/A')
            project_val = memory.get('project_id', 'N/A')

            print(f"{i}. Similarity: {similarity_score:.4f}")
            print(f"   Content: {content}")
            print(f"   Type: {memory_type_val} | Source: {source_val} | Importance: {importance_val}")
            print(f"   Tags: {tags_val} | Project: {project_val}")
            print(f"   Created: {created_at}")
            print("-" * 80)

        return similar_memories


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Retrieve similar memories with filtering options')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--type', help='Filter by memory type (fact, identity, preference, log, etc.)')
    parser.add_argument('--tags', help='Filter by comma-separated tags')
    parser.add_argument('--importance-min', type=int, help='Minimum importance level (1-5)')
    parser.add_argument('--limit', type=int, default=3, help='Maximum number of results (default: 3)')
    parser.add_argument('--project-id', help='Filter by project identifier (e.g., "personal", "work", "blog")')
    return parser.parse_args()


async def main() -> None:
    """Main function to handle command line input."""
    try:
        args = parse_arguments()

        # Parse tags if provided
        tags = parse_tags(args.tags) if args.tags else None

        retriever = MemoryRetriever()
        await retriever.retrieve_similar(
            query=args.query,
            limit=args.limit,
            memory_type=args.type,
            tags=tags,
            importance_min=args.importance_min,
            project_id=args.project_id
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
