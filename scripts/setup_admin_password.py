#!/usr/bin/env python3
"""
Setup script to generate admin password hash for authentication.
Run this once to set up your admin password.
"""

import bcrypt
import getpass
import os

def generate_password_hash():
    """Generate a secure password hash for the admin user."""
    print("Setting up admin password for Sparky web interface")
    print("=" * 50)
    
    while True:
        password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("Passwords don't match. Please try again.\n")
            continue
            
        if len(password) < 8:
            print("Password must be at least 8 characters long. Please try again.\n")
            continue
            
        break
    
    # Generate password hash
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_string = password_hash.decode('utf-8')
    
    print("\nGenerated password hash:")
    print(f'ADMIN_PASSWORD_HASH="{hash_string}"')
    print("\nAdd this line to your .env file")
    
    # Check if .env exists and offer to append
    if os.path.exists('.env'):
        response = input("\nWould you like me to add this to your .env file? (y/n): ")
        if response.lower() == 'y':
            with open('.env', 'a') as f:
                f.write(f'\nADMIN_PASSWORD_HASH="{hash_string}"\n')
            print("Added to .env file!")
    
    print("\nSetup complete! You can now start the server with authentication.")

if __name__ == "__main__":
    generate_password_hash()