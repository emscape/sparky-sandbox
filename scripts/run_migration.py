#!/usr/bin/env python3
"""Run database migrations."""

import sys
from pathlib import Path
from supabase import create_client
from config import config

def run_migration(sql_file: Path):
    """Execute a SQL migration file."""
    print(f"Running migration: {sql_file.name}")
    
    try:
        client = create_client(config.supabase_url, config.supabase_key)
        
        # Read SQL file
        sql = sql_file.read_text()
        
        # Split into individual statements and execute
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"  Executing statement {i}/{len(statements)}...")
                # Note: Supabase Python client doesn't have direct SQL execution
                # You'll need to run this in Supabase SQL Editor
                print(f"  Statement: {statement[:100]}...")
        
        print(f"\n⚠️  Please run this migration manually in Supabase SQL Editor:")
        print(f"  1. Go to: https://supabase.com/dashboard/project/{config.supabase_url.split('//')[1].split('.')[0]}/sql/new")
        print(f"  2. Copy and paste the contents of: {sql_file}")
        print(f"  3. Click 'Run'\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all pending migrations."""
    migrations_dir = Path('supabase/migrations')
    
    if not migrations_dir.exists():
        print("❌ Migrations directory not found")
        sys.exit(1)
    
    # Get all SQL files
    sql_files = sorted(migrations_dir.glob('*.sql'))
    
    if not sql_files:
        print("No migrations found")
        return
    
    print("=" * 80)
    print("DATABASE MIGRATIONS")
    print("=" * 80)
    print()
    
    # For now, just show the SQL that needs to be run
    migration_file = migrations_dir / '002_add_conversations.sql'
    
    if migration_file.exists():
        print(f"📄 Migration file: {migration_file}")
        print()
        print("SQL to run:")
        print("-" * 80)
        print(migration_file.read_text())
        print("-" * 80)
        print()
        print("✅ Copy the SQL above and run it in Supabase SQL Editor")
        print(f"   URL: https://supabase.com/dashboard/project/pprvugnxdzvzrvsduuiq/sql/new")
    else:
        print("❌ Migration file not found")


if __name__ == "__main__":
    main()

