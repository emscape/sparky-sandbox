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
        """Get current user from Supabase session, with debug logging."""
        try:
            from aiohttp_session import get_session
            session = await get_session(request)
            print(f"[DEBUG] Session contents: {dict(session)}")
            access_token = session.get("supabase_access_token")
            print(f"[DEBUG] Access token: {access_token}")
            if not access_token:
                print("[DEBUG] No access token found in session.")
                return None
            user = self.supabase_auth.get_user_from_session(access_token)
            print(f"[DEBUG] User from session: {user}")
            return user
        except Exception as e:
            print(f"[DEBUG] Exception in get_current_user: {e}")
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
        """Handle OAuth callback from Supabase auth, with debug logging."""
        if not config.oauth_enabled:
            return web.Response(text="OAuth not configured", status=503)

        try:
            print(f"[DEBUG] OAuth callback - Request headers: {dict(request.headers)}")
            print(f"[DEBUG] OAuth callback - Request cookies: {dict(request.cookies)}")
            print(f"[DEBUG] OAuth callback - Request URL: {request.url}")

            code = request.query.get("code")
            print(f"[DEBUG] OAuth callback code: {code}")
            if not code:
                print("[DEBUG] Missing code in OAuth callback.")
                return web.Response(text="Authentication failed: Missing code", status=400)

            session_data = self.supabase_auth.exchange_code_for_session(code)
            print(f"[DEBUG] Session data from exchange: {session_data}")
            if not session_data:
                print("[DEBUG] Invalid session data after code exchange.")
                return web.Response(text="Authentication failed: Invalid session", status=500)

            access_token = session_data["access_token"]
            refresh_token = session_data.get("refresh_token")
            user = session_data["user"]

            # Store tokens in session
            from aiohttp_session import get_session

            print(f"[DEBUG] Getting session from request...")
            session = await get_session(request)
            print(f"[DEBUG] Session before storing tokens: {dict(session)}")

            session["supabase_access_token"] = access_token
            session["supabase_refresh_token"] = refresh_token
            session["user_id"] = user["id"]
            print(f"[DEBUG] Session after storing tokens: {dict(session)}")

            # Force session to be saved by marking it as changed
            session.changed()
            print(f"[DEBUG] Session marked as changed for persistence")

            # Create response and check if cookies are being set
            response = web.Response(status=302, headers={"Location": "/chat"})
            print(f"[DEBUG] Response cookies: {dict(response.cookies) if hasattr(response, 'cookies') else 'No cookies attribute'}")

            return response

        except Exception as e:
            print(f"[DEBUG] OAuth callback error: {e}")
            import traceback
            traceback.print_exc()
            return web.Response(text="Authentication failed", status=500)
    async def handle_session_debug(self, request):
        """Debug endpoint to inspect session state after login."""
        from aiohttp_session import get_session
        session = await get_session(request)
        print(f"[DEBUG] /api/session-debug session: {dict(session)}")
        return web.json_response({"session": dict(session)})

    async def handle_session_test(self, request):
        """Test endpoint to verify session persistence."""
        from aiohttp_session import get_session
        session = await get_session(request)

        # Get or initialize test counter
        counter = session.get("test_counter", 0)
        counter += 1
        session["test_counter"] = counter
        session.changed()

        print(f"[DEBUG] Session test - Counter: {counter}, Session: {dict(session)}")
        return web.json_response({
            "counter": counter,
            "session_id": session.get("session_id", "none"),
            "cookies_received": dict(request.cookies)
        })

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
                            "id": user["id"],
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
        """Serve chat page, handling Supabase OAuth redirect."""
        from aiohttp_session import get_session

        # Check if this is a Supabase OAuth redirect with tokens
        access_token = request.query.get('access_token')
        refresh_token = request.query.get('refresh_token')

        if access_token:
            print(f"[DEBUG] Chat route - Processing Supabase OAuth redirect")
            print(f"[DEBUG] Chat route - Access token present: {bool(access_token)}")
            print(f"[DEBUG] Chat route - Refresh token present: {bool(refresh_token)}")

            try:
                # Get user info from Supabase
                user_info = self.supabase_auth.get_user_from_session(access_token)
                if user_info:
                    print(f"[DEBUG] Chat route - User info: {user_info}")

                    # Create aiohttp session
                    session = await get_session(request)
                    session["supabase_access_token"] = access_token
                    if refresh_token:
                        session["supabase_refresh_token"] = refresh_token
                    session["user_id"] = user_info["id"]
                    session["user_email"] = user_info["email"]
                    session.changed()

                    print(f"[DEBUG] Chat route - Session created: {dict(session)}")

                    # Redirect to clean URL without tokens
                    return web.Response(status=302, headers={"Location": "/chat"})
                else:
                    print(f"[DEBUG] Chat route - Failed to get user info from token")
            except Exception as e:
                print(f"[DEBUG] Chat route - Error processing OAuth redirect: {e}")
                import traceback
                traceback.print_exc()

        # Normal chat page serving - check authentication
        user = await self.get_current_user(request)
        if not user:
            print(f"[DEBUG] Chat route - No authenticated user, redirecting to login")
            return web.Response(status=302, headers={"Location": "/"})

        print(f"[DEBUG] Chat route - Serving chat page for user: {user.get('email', 'unknown')}")
        return web.FileResponse("templates/chat.html")

    async def create_app(self):
        """Create and configure the web application."""
        app = web.Application()

        # Setup session middleware with proper cookie attributes for HTTPS
        secret_key = config.jwt_secret.encode("utf-8")[:32]
        if len(secret_key) < 32:
            secret_key = (secret_key * (32 // len(secret_key) + 1))[:32]

        # Determine if we're in production (Railway) or local development
        import os
        is_production = bool(os.getenv("RAILWAY_ENVIRONMENT"))

        # Allow override of cookie security settings via environment
        cookie_secure = os.getenv("COOKIE_SECURE", str(is_production)).lower() in ("true", "1", "yes")
        # Try None for debugging cross-site issues, fallback to Lax
        cookie_samesite = os.getenv("COOKIE_SAMESITE", "None" if is_production else "None")

        # For HTTPS environments, we need to ensure proper cookie attributes
        # Try different approaches based on aiohttp version compatibility
        try:
            # Modern aiohttp approach with explicit cookie attributes
            cookie_storage = EncryptedCookieStorage(
                secret_key,
                cookie_name="AIOHTTP_SESSION",
                secure=cookie_secure,
                httponly=True,
                samesite=cookie_samesite if cookie_samesite != "None" else None,
                max_age=86400
            )
            print(f"[DEBUG] Using modern cookie storage with secure={cookie_secure}, samesite={cookie_samesite}")
        except TypeError:
            # Fallback for older aiohttp versions
            cookie_storage = EncryptedCookieStorage(
                secret_key,
                cookie_name="AIOHTTP_SESSION",
                max_age=86400
            )
            print(f"[DEBUG] Using fallback cookie storage (older aiohttp version)")

        print(f"[DEBUG] Session cookie config - Production: {is_production}, Secure: {cookie_secure}, SameSite: {cookie_samesite}")

        setup_session(app, cookie_storage)

        # Add middleware to debug cookie issues and fix cookie attributes
        @web.middleware
        async def cookie_fix_middleware(request, handler):
            print(f"[DEBUG] Request URL: {request.url}")
            print(f"[DEBUG] Request host: {request.host}")
            print(f"[DEBUG] Request scheme: {request.scheme}")
            print(f"[DEBUG] Request cookies: {dict(request.cookies)}")

            response = await handler(request)

            # Debug response cookies and headers
            if hasattr(response, 'cookies'):
                print(f"[DEBUG] Response cookies: {dict(response.cookies)}")
                for cookie_name, cookie_obj in response.cookies.items():
                    print(f"[DEBUG] Cookie {cookie_name} details: {cookie_obj}")

            # Check Set-Cookie headers
            if hasattr(response, 'headers'):
                set_cookie_headers = response.headers.getall('Set-Cookie', [])
                print(f"[DEBUG] Set-Cookie headers: {set_cookie_headers}")

            # Fix session cookie attributes for HTTPS if needed
            if is_production and hasattr(response, 'cookies'):
                for cookie_name, cookie_obj in response.cookies.items():
                    if cookie_name == "AIOHTTP_SESSION":
                        print(f"[DEBUG] Fixing cookie attributes for {cookie_name}")
                        cookie_obj['secure'] = True
                        cookie_obj['httponly'] = True
                        cookie_obj['samesite'] = 'Lax'
                        print(f"[DEBUG] Cookie {cookie_name} attributes after fix: {cookie_obj}")

            return response

        app.middlewares.append(cookie_fix_middleware)

        # Health check route (for platforms like Railway)
        async def health(_request):
            return web.json_response({"status": "ok"})

        # Public routes
        app.router.add_get("/", self.serve_login)
        app.router.add_get("/login", self.serve_login)
        app.router.add_get("/chat", self.serve_chat)
        app.router.add_get("/health", health)

        # Debug routes for session inspection
        app.router.add_get("/api/session-debug", self.handle_session_debug)
        app.router.add_get("/api/session-test", self.handle_session_test)

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
