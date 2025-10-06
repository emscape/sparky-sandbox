#!/usr/bin/env python3
"""Simple connectivity test for AI Memory System."""

import asyncio
import sys
from config import config
from helpers import get_embedding
from supabase import create_client, Client
from openai import AsyncOpenAI


async def test_openai_connectivity():
    """Test OpenAI API connectivity."""
    print("Testing OpenAI API connectivity...")
    
    try:
        client = AsyncOpenAI(api_key=config.openai_api_key)
        test_text = "This is a test for connectivity validation."
        embedding = await get_embedding(test_text, client)
        
        if len(embedding) == config.embedding_dimensions:
            print(f"✅ OpenAI API working - generated {len(embedding)}D embedding")
            return True
        else:
            print(f"❌ Embedding dimension mismatch: got {len(embedding)}, expected {config.embedding_dimensions}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False


def test_supabase_connectivity():
    """Test Supabase database connectivity."""
    print("Testing Supabase database connectivity...")
    
    try:
        # Create Supabase client
        supabase: Client = create_client(config.supabase_url, config.supabase_key)
        
        # Test basic connectivity with a simple query
        response = supabase.table(config.memory_table).select("count", count="exact").limit(1).execute()
        
        print(f"✅ Database connection successful")
        print(f"✅ Memory table '{config.memory_table}' accessible")
        
        # Check if table has data
        if hasattr(response, 'count') and response.count is not None:
            print(f"✅ Table contains {response.count} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connectivity test failed: {e}")
        return False


async def main():
    """Run connectivity tests."""
    print("🔌 AI Memory System - Connectivity Test")
    print("=" * 50)
    
    # Test OpenAI
    openai_ok = await test_openai_connectivity()
    
    print()
    
    # Test Supabase
    supabase_ok = test_supabase_connectivity()
    
    print("\n" + "=" * 50)
    
    if openai_ok and supabase_ok:
        print("🎉 All connectivity tests passed!")
        return 0
    else:
        print("❌ Some connectivity tests failed!")
        if not openai_ok:
            print("  - OpenAI API connectivity failed")
        if not supabase_ok:
            print("  - Supabase database connectivity failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
