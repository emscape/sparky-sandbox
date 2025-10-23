"""
Google OAuth authentication handler for Sparky.
"""

import jwt
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode

from supabase import create_client, Client
from config import config


class GoogleOAuthHandler:
    """Handle Google OAuth authentication flow."""
    
    def __init__(self):
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
        self.client_id = config.google_client_id
        self.client_secret = config.google_client_secret
        self.redirect_uri = config.oauth_redirect_uri

    def get_auth_url(self) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token."""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Token exchange failed: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"Exception during token exchange: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[Dict]:
        """Get user information from Google using access token."""
        user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user_info_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"User info retrieval failed: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"Exception during user info retrieval: {e}")
            return None

    async def create_or_update_user(self, user_info: Dict) -> Optional[Dict]:
        """Create or update user in database."""
        try:
            google_id = user_info.get('id')
            email = user_info.get('email')
            name = user_info.get('name')
            avatar_url = user_info.get('picture')

            # Check if user exists
            result = self.supabase.table('users').select('*').eq('google_id', google_id).execute()
            
            if result.data:
                # Update existing user
                user_data = {
                    'email': email,
                    'name': name,
                    'avatar_url': avatar_url,
                    'last_login': datetime.utcnow().isoformat()
                }
                updated_result = self.supabase.table('users').update(user_data).eq('google_id', google_id).execute()
                return updated_result.data[0] if updated_result.data else None
            else:
                # Create new user
                user_data = {
                    'google_id': google_id,
                    'email': email,
                    'name': name,
                    'avatar_url': avatar_url,
                    'last_login': datetime.utcnow().isoformat()
                }
                new_result = self.supabase.table('users').insert(user_data).execute()
                return new_result.data[0] if new_result.data else None

        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None

    def create_jwt_token(self, user: Dict) -> str:
        """Create JWT token for user session."""
        payload = {
            'user_id': user['id'],
            'google_id': user['google_id'],
            'email': user['email'],
            'name': user['name'],
            'exp': datetime.utcnow() + timedelta(hours=config.jwt_expiry_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)

    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def process_callback(self, code: str) -> Optional[Dict]:
        """Process the OAuth callback and return user data."""
        try:
            print(f"Processing OAuth callback with code: {code[:10]}...")
            
            # Exchange code for token
            token_data = await self.exchange_code_for_token(code)
            if not token_data:
                print("Token exchange failed")
                return None

            print("Token exchange successful")

            # Get user info
            user_info = await self.get_user_info(token_data['access_token'])
            if not user_info:
                print("User info retrieval failed")
                return None

            print(f"Retrieved user info for: {user_info.get('email')}")

            # Create or update user
            user = await self.create_or_update_user(user_info)
            if user:
                print(f"User created/updated successfully: {user.get('email')}")
            else:
                print("User creation/update failed")
            return user
        except Exception as e:
            print(f"Exception in process_callback: {e}")
            return None