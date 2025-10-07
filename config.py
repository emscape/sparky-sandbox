"""Configuration management for AI memory system."""

import os
import secrets
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Centralized configuration class with validation."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.openai_api_key = self._get_required_env("OPENAI_API_KEY")
        self.supabase_url = self._get_required_env("SUPABASE_URL")
        self.supabase_key = self._get_required_env("SUPABASE_KEY")

        # Optional configurations with defaults
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        self.memory_table = "structured_memory"

        # Google OAuth settings (optional for deployment, required for auth)
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "not-configured")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "not-configured")
        self.oauth_redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/api/auth/google/callback")
        
        # Allow forced disable of OAuth (for initial Railway deploy without domain)
        disable_oauth_flag = os.getenv("DISABLE_OAUTH", "false").lower() in {"1", "true", "yes", "on"}

        # Check if OAuth is properly configured
        oauth_configured = (
            self.google_client_id != "not-configured" and 
            self.google_client_secret != "not-configured"
        )
        self.oauth_enabled = (not disable_oauth_flag) and oauth_configured
        
        # JWT settings for session management
        self.jwt_secret = self._get_session_secret()
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_hours = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_session_secret(self) -> str:
        """Get or generate JWT secret key."""
        secret = os.getenv("JWT_SECRET")
        if secret:
            return secret
        else:
            # Generate a new secret key - in production, you should set this in .env
            print("Warning: JWT_SECRET not found in environment. Generating a new one.")
            print("Add this to your .env file for persistent sessions:")
            new_secret = secrets.token_hex(32)
            print(f"JWT_SECRET={new_secret}")
            return new_secret

    def validate(self) -> bool:
        """Validate configuration parameters."""
        if self.embedding_dimensions not in [1536, 3072]:
            raise ValueError(f"Unsupported embedding dimensions: {self.embedding_dimensions}")
        return True


def validate_environment() -> None:
    """Validate that all required environment variables are set."""
    config.validate()

def parse_tags(tags_str: str) -> List[str]:
    """Parse comma-separated tags string into list."""
    if not tags_str:
        return []
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]

def validate_importance(importance: int) -> int:
    """Validate importance value is within acceptable range."""
    if not 1 <= importance <= 5:
        raise ValueError("Importance must be between 1 (low) and 5 (critical)")
    return importance

# Global configuration instance
config = Config()
config.validate()
