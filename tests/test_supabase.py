#!/usr/bin/env python3
"""Quick Supabase connectivity test."""

from supabase import create_client
from config import config

print("Testing Supabase connectivity...")
print(f"URL: {config.supabase_url}")

try:
    client = create_client(config.supabase_url, config.supabase_key)
    result = client.table(config.memory_table).select("*").limit(1).execute()
    print(f"✅ Supabase is accessible!")
    print(f"   Table: {config.memory_table}")
    print(f"   Records found: {len(result.data)}")
except Exception as e:
    print(f"❌ Supabase error: {e}")
    print(f"\n💡 Possible issues:")
    print(f"   1. Database is paused - check Supabase dashboard")
    print(f"   2. Network/DNS issue")
    print(f"   3. Invalid credentials")

