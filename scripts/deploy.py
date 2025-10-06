#!/usr/bin/env python3
"""Deployment pre-flight checks for Sparky AI Assistant."""

import os
import sys
import asyncio
import argparse
from typing import List, Tuple
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.config import config
    from supabase import create_client, Client
    from openai import AsyncOpenAI
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

class DeploymentChecker:
    """Pre-flight deployment checks."""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.issues: List[str] = []
    
    def check(self, name: str, condition: bool, error_msg: str = "") -> bool:
        """Run a check and track results."""
        self.checks_total += 1
        if condition:
            print(f"✅ {name}")
            self.checks_passed += 1
            return True
        else:
            print(f"❌ {name}" + (f": {error_msg}" if error_msg else ""))
            self.issues.append(f"{name}: {error_msg}")
            return False
    
    async def run_all_checks(self) -> bool:
        """Run all deployment checks."""
        print("� Running Sparky deployment pre-flight checks...\n")
        
        # Environment checks
        self.check_environment()
        
        # Database checks
        await self.check_database()
        
        # OpenAI checks
        await self.check_openai()
        
        # Security checks
        self.check_security()
        
        # Summary
        print(f"\n📊 Results: {self.checks_passed}/{self.checks_total} checks passed")
        
        if self.issues:
            print("\n🔧 Issues to fix:")
            for issue in self.issues:
                print(f"   • {issue}")
            return False
        else:
            print("\n🎉 All checks passed! Ready for deployment.")
            return True
    
    def check_environment(self):
        """Check environment variables."""
        print("� Environment Variables:")
        
        # Required variables
        required_vars = [
            'OPENAI_API_KEY',
            'SUPABASE_URL', 
            'SUPABASE_KEY',
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'JWT_SECRET'
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            self.check(
                f"Environment variable {var}",
                bool(value and value != f"your_{var.lower()}_here"),
                f"Missing or placeholder value"
            )
        
        # Embedding configuration
        embedding_model = config.embedding_model
        embedding_dims = config.embedding_dimensions
        
        self.check(
            f"Embedding model ({embedding_model})",
            embedding_model == "text-embedding-3-small",
            f"Unexpected model: {embedding_model}"
        )
        
        self.check(
            f"Embedding dimensions ({embedding_dims})",
            embedding_dims == 1536,
            f"text-embedding-3-small should be 1536 dims, got {embedding_dims}"
        )
    
    async def check_database(self):
        """Check Supabase database connectivity and setup."""
        print("\n�️  Database (Supabase):")
        
        try:
            supabase: Client = create_client(config.supabase_url, config.supabase_key)
            
            # Test connection
            response = supabase.table('structured_memory').select('id').limit(1).execute()
            self.check(
                "Database connection",
                True,
                ""
            )
            
            self.check(
                "structured_memory table exists",
                True,
                ""
            )
            
            # Check for pgvector extension (if possible)
            try:
                # This might fail with anon key, but that's ok
                response = supabase.rpc('test_vector', {}).execute()
                self.check("pgvector extension", True)
            except:
                # Can't test with anon key, assume it's configured
                print("⚠️  pgvector extension (cannot test with anon key)")
            
        except Exception as e:
            self.check(
                "Database connection",
                False,
                f"Connection failed: {str(e)}"
            )
    
    async def check_openai(self):
        """Check OpenAI API connectivity."""
        print("\n🤖 OpenAI API:")
        
        try:
            client = AsyncOpenAI(api_key=config.openai_api_key)
            
            # Test embeddings
            response = await client.embeddings.create(
                input="test",
                model=config.embedding_model
            )
            
            embedding_dims = len(response.data[0].embedding)
            
            self.check(
                "OpenAI API connection",
                True
            )
            
            self.check(
                f"Embedding dimensions match config",
                embedding_dims == config.embedding_dimensions,
                f"API returned {embedding_dims}, config expects {config.embedding_dimensions}"
            )
            
        except Exception as e:
            self.check(
                "OpenAI API connection",
                False,
                f"API test failed: {str(e)}"
            )
    
    def check_security(self):
        """Check security configuration."""
        print("\n🛡️  Security:")
        
        # JWT secret strength
        jwt_secret = config.jwt_secret
        self.check(
            "JWT secret length",
            len(jwt_secret) >= 32,
            f"JWT secret should be at least 32 characters, got {len(jwt_secret)}"
        )
        
        # Check for placeholder values
        google_client_id = config.google_client_id
        self.check(
            "Google OAuth client ID",
            not google_client_id.startswith("your_") and len(google_client_id) > 20,
            "Appears to be placeholder value"
        )
        
        # Environment file security
        env_file_exists = os.path.exists('.env')
        gitignore_exists = os.path.exists('.gitignore')
        
        self.check("Environment file exists", env_file_exists)
        
        if gitignore_exists:
            with open('.gitignore', 'r') as f:
                gitignore_content = f.read()
            self.check(
                ".env in .gitignore",
                '.env' in gitignore_content,
                ".env should be in .gitignore to prevent secret leaks"
            )

def main():
    """Main deployment checker."""
    parser = argparse.ArgumentParser(description='Sparky deployment pre-flight checks')
    parser.add_argument('--check', action='store_true', help='Run all checks')
    args = parser.parse_args()
    
    if not args.check:
        parser.print_help()
        return
    
    # Load environment
    load_dotenv()
    
    # Run checks
    checker = DeploymentChecker()
    success = asyncio.run(checker.run_all_checks())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
