#!/usr/bin/env python3
"""Simple connectivity test for AI Memory System."""

import asyncio
import sys
from pathlib import Path
import pytest

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from config import config
from utils import get_embedding
from supabase import create_client, Client
from openai import AsyncOpenAI


@pytest.mark.asyncio
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
    print("Testing Supabase connectivity...")
    
    try:
        supabase: Client = create_client(config.supabase_url, config.supabase_key)
        
        # Test a simple query
        response = supabase.table(config.memory_table).select("count", count="exact").execute()
        
        if hasattr(response, 'count'):
            print(f"✅ Supabase connected - {response.count} records in memory table")
        else:
            print("✅ Supabase connected - basic query successful")
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        assert False, f"Supabase connectivity test failed: {e}"


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
