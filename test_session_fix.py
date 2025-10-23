#!/usr/bin/env python3
"""
Test script to verify session cookie configuration fixes.
This script tests the session persistence locally and provides debugging info.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path

# Add the app directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_session_persistence():
    """Test that sessions persist across requests."""
    print("🧪 Testing session persistence...")
    
    # Start a client session
    async with aiohttp.ClientSession() as session:
        base_url = "http://localhost:8080"
        
        print(f"📡 Testing against: {base_url}")
        
        # Test 1: Check health endpoint
        print("\n1️⃣ Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    print("✅ Health endpoint working")
                else:
                    print(f"❌ Health endpoint failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            print("💡 Make sure the server is running with: python app/main.py")
            return False
        
        # Test 2: Test session counter endpoint
        print("\n2️⃣ Testing session persistence...")
        
        # First request - should create session
        async with session.get(f"{base_url}/api/session-test") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ First request - Counter: {data['counter']}")
                print(f"   Cookies received: {data['cookies_received']}")
                
                if data['counter'] != 1:
                    print(f"❌ Expected counter=1, got {data['counter']}")
                    return False
            else:
                print(f"❌ Session test failed: {resp.status}")
                return False
        
        # Second request - should increment counter (session persisted)
        async with session.get(f"{base_url}/api/session-test") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Second request - Counter: {data['counter']}")
                print(f"   Cookies received: {data['cookies_received']}")
                
                if data['counter'] != 2:
                    print(f"❌ Expected counter=2, got {data['counter']}")
                    print("❌ Session not persisting!")
                    return False
                else:
                    print("✅ Session persistence working!")
            else:
                print(f"❌ Session test failed: {resp.status}")
                return False
        
        # Test 3: Check auth status endpoint
        print("\n3️⃣ Testing auth status endpoint...")
        async with session.get(f"{base_url}/api/auth/status") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Auth status: {data}")
                if not data['authenticated']:
                    print("ℹ️  Not authenticated (expected for this test)")
            else:
                print(f"❌ Auth status failed: {resp.status}")
                return False
        
        print("\n🎉 All session tests passed!")
        return True

async def main():
    """Main test function."""
    print("=" * 60)
    print("🔧 SPARKY SESSION FIX VERIFICATION")
    print("=" * 60)
    
    success = await test_session_persistence()
    
    if success:
        print("\n✅ Session configuration appears to be working correctly!")
        print("\n📋 Next steps for deployment:")
        print("   1. Deploy to Railway")
        print("   2. Test OAuth login flow")
        print("   3. Check browser dev tools for cookie settings")
        print("   4. Verify session persistence after login")
    else:
        print("\n❌ Session configuration needs attention!")
        print("\n🔍 Debugging tips:")
        print("   1. Check server logs for [DEBUG] messages")
        print("   2. Verify JWT_SECRET is set consistently")
        print("   3. Check cookie attributes in browser dev tools")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
