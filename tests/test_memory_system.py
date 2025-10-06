#!/usr/bin/env python3
"""Test script to demonstrate the enhanced AI memory system."""

import asyncio
import sys
from inject_memory import MemoryInjector
from retrieve_similar import MemoryRetriever


async def test_memory_system():
    """Test the enhanced memory system with sample data."""
    print("🧪 Testing Enhanced AI Memory System")
    print("=" * 50)
    
    # Initialize components
    injector = MemoryInjector()
    retriever = MemoryRetriever()
    
    # Test data with different types and metadata
    test_memories = [
        {
            "content": "Emily prefers concise answers and hates verbose explanations",
            "type": "preference",
            "tags": ["emily", "communication"],
            "source": "chat",
            "importance": 4
        },
        {
            "content": "User prefers Supabase for database operations and OpenAI for embeddings",
            "type": "preference", 
            "tags": ["database", "ai", "tech-stack"],
            "source": "manual",
            "importance": 3
        },
        {
            "content": "The perkTracker project uses React and Node.js",
            "type": "fact",
            "tags": ["perkTracker", "tech-stack"],
            "source": "documentation",
            "importance": 2
        },
        {
            "content": "Fiona is the project manager for the mobile app initiative",
            "type": "identity",
            "tags": ["fiona", "team", "mobile"],
            "source": "email",
            "importance": 3
        }
    ]
    
    print("📝 Injecting test memories...")
    stored_memories = []
    
    for i, memory in enumerate(test_memories, 1):
        print(f"\n{i}. Storing: {memory['content'][:40]}...")
        try:
            result = await injector.inject_memory(
                memory_text=memory["content"],
                memory_type=memory["type"],
                tags=memory["tags"],
                source=memory["source"],
                importance=memory["importance"]
            )
            stored_memories.append(result)
            print(f"   ✅ Stored with ID: {result.get('id')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Successfully stored {len(stored_memories)} memories")
    
    # Test retrieval with different filters
    print("\n" + "=" * 50)
    print("🔍 Testing Memory Retrieval")
    
    test_queries = [
        {
            "query": "communication preferences",
            "filters": {"memory_type": "preference"},
            "description": "Search preferences about communication"
        },
        {
            "query": "team members",
            "filters": {"tags": ["team"]},
            "description": "Search by team tag"
        },
        {
            "query": "technology stack",
            "filters": {"importance_min": 3},
            "description": "Search high-importance tech info"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Query: '{test['query']}'")
        print(f"   Filters: {test['filters']}")
        print("-" * 40)
        
        try:
            await retriever.retrieve_similar(
                query=test["query"],
                limit=2,
                **test["filters"]
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n🎉 Test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_memory_system())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
