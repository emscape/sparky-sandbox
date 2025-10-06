#!/usr/bin/env python3
"""
Generate a password hash for the admin user.
This script generates a hash for a default password.
"""

import bcrypt

def generate_hash_for_password(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')

if __name__ == "__main__":
    # Use a default secure password - you can change this
    default_password = "sparky2024!"
    hash_result = generate_hash_for_password(default_password)
    
    print("Generated password hash for authentication:")
    print(f"Password: {default_password}")
    print(f"Hash: {hash_result}")
    print("\nAdd this to your .env file:")
    print(f'ADMIN_PASSWORD_HASH="{hash_result}"')