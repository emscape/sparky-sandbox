"""Supabase authentication handler."""

import os
from typing import Dict, Optional
from supabase import create_client, Client
from config import config


class SupabaseAuth:
    """Handle authentication using Supabase's built-in auth system."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
    
    def get_google_auth_url(self, redirect_to: str = "/chat") -> str:
        """Get Google OAuth URL using Supabase auth."""
        try:
            # Supabase will handle the OAuth flow and redirect back to your app
            response = self.supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": f"{self._get_base_url()}{redirect_to}"
                }
            })
            return response.url
        except Exception as e:
            print(f"Error generating Google auth URL: {e}")
            raise
    
    def get_user_from_session(self, access_token: str) -> Optional[Dict]:
        """Get user information from Supabase session token."""
        try:
            response = self.supabase.auth.get_user(access_token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get("name", ""),
                    "avatar_url": response.user.user_metadata.get("avatar_url", ""),
                    "provider": "google"
                }
            return None
        except Exception as e:
            print(f"Error getting user from session: {e}")
            return None
    
    def _get_base_url(self) -> str:
        """Get the base URL for redirects."""
        # In production, this should be your domain
        # In development, this should be localhost
        if os.getenv("RAILWAY_ENVIRONMENT"):
            return "https://sparky.emily-cameron.pro"
        else:
            return "http://localhost:8080"
    
    def sign_out(self, access_token: str) -> bool:
        """Sign out the user."""
        try:
            self.supabase.auth.sign_out(access_token)
            return True
        except Exception as e:
            print(f"Error signing out: {e}")
            return False