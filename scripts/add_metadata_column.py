#!/usr/bin/env python3
"""Add metadata column to structured_memory table."""

from supabase import create_client
from config import config

print("Adding metadata column to structured_memory table...")

try:
    client = create_client(config.supabase_url, config.supabase_key)
    
    # Add metadata column using SQL
    sql = """
    ALTER TABLE structured_memory 
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
    """
    
    result = client.rpc('exec_sql', {'sql': sql}).execute()
    print("✅ Metadata column added successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nPlease add the column manually in Supabase SQL Editor:")
    print("ALTER TABLE structured_memory ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;")

