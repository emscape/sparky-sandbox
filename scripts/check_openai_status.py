#!/usr/bin/env python3
"""
Check OpenAI API Status and Limits
Diagnose API key, credits, and rate limit issues.
"""

import asyncio
import sys
from openai import AsyncOpenAI
from config import config


async def check_api_status():
    """Check OpenAI API status and limits."""
    print("="*60)
    print("🔍 OPENAI API STATUS CHECK")
    print("="*60)
    
    # Check API key format
    api_key = config.openai_api_key
    print(f"\n🔑 API Key Check:")
    print(f"   Key starts with: {api_key[:10]}...")
    print(f"   Key length: {len(api_key)} characters")
    
    if api_key.startswith('sk-proj-'):
        print(f"   ✅ Project-based API key detected")
    elif api_key.startswith('sk-'):
        print(f"   ✅ Standard API key detected")
    else:
        print(f"   ⚠️  Unusual API key format")
    
    # Test API connectivity
    print(f"\n🌐 Testing API Connectivity:")
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        # Try a simple embedding request
        print(f"   Attempting test embedding request...")
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input="test"
        )
        print(f"   ✅ API is working!")
        print(f"   Model: {response.model}")
        print(f"   Embedding dimensions: {len(response.data[0].embedding)}")
        
        # Try to get account info (if available)
        print(f"\n💰 Account Status:")
        print(f"   ✅ API key is valid and has access")
        print(f"   ✅ Embeddings are working")
        
    except Exception as e:
        error_str = str(e)
        print(f"   ❌ API Error: {error_str}")
        
        if "429" in error_str:
            print(f"\n🚨 RATE LIMIT / QUOTA ISSUE DETECTED")
            print(f"\nPossible causes:")
            print(f"   1. API key is from different org than the one with $9.55")
            print(f"   2. You're on free tier with very low rate limits")
            print(f"   3. You've exceeded your usage limits for this billing period")
            print(f"   4. Your payment method needs verification")
            
            if "insufficient_quota" in error_str:
                print(f"\n💡 SOLUTION:")
                print(f"   This specific error means the API key doesn't have access")
                print(f"   to the credits in your account.")
                print(f"\n   Steps to fix:")
                print(f"   1. Go to: https://platform.openai.com/api-keys")
                print(f"   2. Check which PROJECT this API key belongs to")
                print(f"   3. Go to: https://platform.openai.com/settings/organization/billing/overview")
                print(f"   4. Verify the billing is for the SAME organization/project")
                print(f"   5. If different, create a NEW API key from the correct project")
                
        elif "401" in error_str:
            print(f"\n🚨 AUTHENTICATION ERROR")
            print(f"   Your API key is invalid or expired")
            print(f"   Generate a new key at: https://platform.openai.com/api-keys")
            
        elif "500" in error_str:
            print(f"\n🚨 OPENAI SERVER ERROR")
            print(f"   This is temporary - try again in a few minutes")
            
        return False
    
    # Test rate limits with multiple requests
    print(f"\n⚡ Testing Rate Limits:")
    print(f"   Sending 3 rapid requests to test limits...")
    
    success_count = 0
    for i in range(3):
        try:
            await client.embeddings.create(
                model="text-embedding-3-small",
                input=f"test message {i}"
            )
            success_count += 1
            print(f"   ✅ Request {i+1}/3 succeeded")
            await asyncio.sleep(0.5)  # Small delay
        except Exception as e:
            print(f"   ❌ Request {i+1}/3 failed: {str(e)[:100]}")
    
    if success_count == 3:
        print(f"\n✅ Rate limits look good!")
    elif success_count > 0:
        print(f"\n⚠️  Partial success - you may have low rate limits")
    else:
        print(f"\n❌ All requests failed - rate limit issue")
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    
    if success_count >= 2:
        print(f"✅ Your API is working and ready for ingestion!")
        print(f"\n🚀 Next step:")
        print(f"   C:\\Python313\\python.exe ingest_sparky_export.py chat-history")
    else:
        print(f"❌ API issues detected - see details above")
        print(f"\n🔧 Most likely fix:")
        print(f"   1. Check your API key is from the correct project")
        print(f"   2. Verify billing is set up for that project")
        print(f"   3. Generate a new API key if needed")
    
    print(f"{'='*60}")
    
    return success_count >= 2


async def main():
    """Main function."""
    try:
        success = await check_api_status()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

