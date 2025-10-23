"""Supabase authentication handler."""

import os
from typing import Dict, Optional

from supabase import Client, create_client

from config import config


class SupabaseAuth:
    """Handle authentication using Supabase's built-in auth system."""

    def __init__(self) -> None:
        """Initialize Supabase client."""
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)

    def get_google_auth_url(self, redirect_to: str = "/chat") -> str:
        """Get Google OAuth URL using Supabase auth."""
        try:
            response = self.supabase.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {
                        "redirect_to": f"{self._get_base_url()}{redirect_to}",
                    },
                }
            )
            return response.url
        except Exception as e:
            print(f"Error generating Google auth URL: {e}")
            raise

    def exchange_code_for_session(self, code: str) -> Optional[Dict]:
        """Exchange the Supabase authorization code for a session."""
        try:
            response = self.supabase.auth.exchange_code_for_session({"auth_code": code})
            if not response or not response.session or not response.user:
                return None

            session = response.session
            user = response.user

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.user_metadata.get("name", ""),
                    "avatar_url": user.user_metadata.get("avatar_url", ""),
                    "provider": user.app_metadata.get("provider", "google"),
                },
            }
        except Exception as e:
            print(f"Error exchanging code for session: {e}")
            return None

    def get_user_from_session(self, access_token: str) -> Optional[Dict]:
        """Get user information from a Supabase access token."""
        try:
            response = self.supabase.auth.get_user(access_token)
            if response.user:
                user = response.user
                return {
                    "id": user.id,
                    "email": user.email,
                    "name": user.user_metadata.get("name", ""),
                    "avatar_url": user.user_metadata.get("avatar_url", ""),
                    "provider": user.app_metadata.get("provider", "google"),
                }
            return None
        except Exception as e:
            print(f"Error getting user from session: {e}")
            return None

    def _get_base_url(self) -> str:
        """Get the base URL for redirects."""
        if os.getenv("RAILWAY_ENVIRONMENT"):
            return "https://sparky.emily-cameron.pro"
        return "http://localhost:8080"

    def sign_out(self, access_token: str) -> bool:
        """Sign out the user."""
        try:
            self.supabase.auth.sign_out(access_token)
            return True
        except Exception as e:
            print(f"Error signing out: {e}")
            return False