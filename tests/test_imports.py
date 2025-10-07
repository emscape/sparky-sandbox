"""Test basic import functionality to catch deployment issues early.

Note: Avoid globally mutating sys.path here to prevent shadowing the `src/memory`
package during full-suite collection. Instead, push `app/` onto sys.path only
inside the tests that require importing from `app.*`, and pop it afterwards.
"""

import sys
from pathlib import Path


def test_config_import():
    """Test that config can be imported."""
    from config import config
    assert config is not None
    assert hasattr(config, 'openai_api_key')


def test_auth_import():
    """Test that auth module can be imported."""
    from app.auth.google import GoogleOAuthHandler
    assert GoogleOAuthHandler is not None


def test_chat_import():
    """Test that chat module can be imported."""
    from app.chat.routes import ChatHandler
    assert ChatHandler is not None


def test_memory_import():
    """Test that memory module can be imported."""
    from app.memory.utils import MemoryManager, get_embedding
    assert MemoryManager is not None
    assert get_embedding is not None


def test_main_app_import():
    """Test that main app can be imported."""
    from app.main import SparkyApp
    assert SparkyApp is not None


if __name__ == "__main__":
    """Run import tests directly."""
    import traceback
    
    tests = [
        test_config_import,
        test_auth_import, 
        test_chat_import,
        test_memory_import,
        test_main_app_import
    ]
    
    print("Running import validation tests...")
    
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            traceback.print_exc()
    
    print("Import test complete!")