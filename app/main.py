#!/usr/bin/env python3
"""
Main application file for Sparky AI Assistant.
Consolidated web server with Google OAuth authentication.
"""

import asyncio
from typing import Dict, Optional
from pathlib import Path

from aiohttp import web
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from openai import AsyncOpenAI

from config import config
from .auth.supabase_auth import SupabaseAuth
from .chat.routes import ChatHandler
from .memory.utils import MemoryManager


class SparkyApp:
    """Main Sparky application class."""

    def __init__(self):
        """Initialize the application."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase_auth = SupabaseAuth()
        self.chat_handler = ChatHandler(self.openai_client)
        self.memory_manager = MemoryManager()

    def require_auth(self, handler):
        """Decorator to require authentication for routes."""

        async def wrapper(request):
            user = await self.get_current_user(request)
            if not user:
                return web.json_response(
                    {"error": "Authentication required"}, status=401
                )
            request["user"] = user
            return await handler(request)

        return wrapper

    async def get_current_user(self, request) -> Optional[Dict]:
        """Get current user from Supabase session."""
        try:
            from aiohttp_session import get_session

            session = await get_session(request)
            access_token = session.get("supabase_access_token")

            if not access_token:
                return None

            user = self.supabase_auth.get_user_from_session(access_token)
            return user
        except Exception:
            return None

    async def handle_login_redirect(self, request):
        """Redirect to Google OAuth via Supabase."""
        if not config.oauth_enabled:
            return web.Response(
                text="OAuth not configured. Please set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET environment variables.",
                status=503,
            )

        try:
            auth_url = self.supabase_auth.get_google_auth_url()
            return web.Response(status=302, headers={"Location": auth_url})
        except Exception as e:
            return web.Response(text=f"Auth error: {e}", status=500)

    async def handle_oauth_callback(self, request):
        """Handle OAuth callback from Supabase auth."""
        if not config.oauth_enabled:
            return web.Response(text="OAuth not configured", status=503)

        try:
            # With Supabase auth, the callback includes access_token and refresh_token
            access_token = request.query.get("access_token")
            refresh_token = request.query.get("refresh_token")
            
            if not access_token:
                return web.Response(text="Authentication failed: No access token", status=400)

            # Get user info from Supabase
            user = self.supabase_auth.get_user_from_session(access_token)
            if not user:
                return web.Response(text="Authentication failed: Invalid token", status=500)

            # Store tokens in session
            from aiohttp_session import get_session

            session = await get_session(request)
            session["supabase_access_token"] = access_token
            session["supabase_refresh_token"] = refresh_token
            session["user_id"] = user["id"]

            # Redirect to chat interface
            return web.Response(status=302, headers={"Location": "/chat"})

        except Exception as e:
            print(f"OAuth callback error: {e}")
            return web.Response(text="Authentication failed", status=500)

    async def handle_logout(self, request):
        """Handle logout request."""
        try:
            from aiohttp_session import get_session

            session = await get_session(request)
            access_token = session.get("supabase_access_token")
            
            # Sign out from Supabase
            if access_token:
                self.supabase_auth.sign_out(access_token)
            
            session.clear()
            return web.json_response({"success": True})
        except Exception as e:
            print(f"Logout error: {e}")
            return web.json_response({"error": "Logout failed"}, status=500)

    async def handle_auth_status(self, request):
        """Check authentication status."""
        try:
            user = await self.get_current_user(request)
            if user:
                return web.json_response(
                    {
                        "authenticated": True,
                        "user": {
                            "id": user["user_id"],
                            "email": user["email"],
                            "name": user["name"],
                        },
                    }
                )
            else:
                return web.json_response({"authenticated": False})
        except Exception as e:
            print(f"Auth status error: {e}")
            return web.json_response({"authenticated": False})

    async def serve_login(self, request):
        """Serve login page."""
        return web.FileResponse("templates/login.html")

    async def serve_chat(self, request):
        """Serve chat page."""
        user = await self.get_current_user(request)
        if not user:
            return web.Response(status=302, headers={"Location": "/"})
        return web.FileResponse("templates/chat.html")

    async def create_app(self):
        """Create and configure the web application."""
        app = web.Application()

        # Setup session middleware
        secret_key = config.jwt_secret.encode("utf-8")[:32]
        if len(secret_key) < 32:
            secret_key = (secret_key * (32 // len(secret_key) + 1))[:32]

        setup_session(app, EncryptedCookieStorage(secret_key))

        # Health check route (for platforms like Railway)
        async def health(_request):
            return web.json_response({"status": "ok"})

        # Public routes
        app.router.add_get("/", self.serve_login)
        app.router.add_get("/login", self.serve_login)
        app.router.add_get("/chat", self.serve_chat)
        app.router.add_get("/health", health)

        # Authentication routes (no auth required)
        app.router.add_get("/api/auth/google", self.handle_login_redirect)
        app.router.add_get("/api/auth/google/callback", self.handle_oauth_callback)
        app.router.add_post("/api/logout", self.handle_logout)
        app.router.add_get("/api/auth/status", self.handle_auth_status)

        # Protected API routes (require authentication)
        app.router.add_post(
            "/api/chat", self.require_auth(self.chat_handler.handle_chat)
        )
        app.router.add_post(
            "/api/chat/clear", self.require_auth(self.chat_handler.handle_clear)
        )
        app.router.add_post(
            "/api/memory/search", self.require_auth(self.memory_manager.handle_search)
        )

        # Serve static files
        app.router.add_static("/static/", path=Path("./static"), name="static")

        return app


def create_app():
    """Factory function to create the app (for Vercel)."""
    sparky = SparkyApp()
    return asyncio.run(sparky.create_app())


def main():
    """Main entrypoint for local development and deployment (synchronous)."""
    import os

    # Get host and port from environment (for deployment) or use defaults (for local)
    host = os.getenv("HOST", "0.0.0.0")  # Railway/Render need 0.0.0.0
    port = int(os.getenv("PORT", 8080))  # Railway provides PORT env var

    print("=" * 80)
    print("✨ SPARKY AI ASSISTANT")
    print("=" * 80)
    print(f"\nStarting server on {host}:{port}")
    if host == "localhost":
        print("Open your browser and navigate to: http://localhost:8080")
    print("\nPress Ctrl+C to stop the server.")
    print("=" * 80)
    print()

    # Pass coroutine to aiohttp; it will manage the event loop internally
    sparky = SparkyApp()
    web.run_app(sparky.create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
