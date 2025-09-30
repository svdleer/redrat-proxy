#!/usr/bin/env python3
"""
Generate bcrypt password hash for RedRat admin user and API key hashes
"""
import bcrypt
import hashlib
import sys

def generate_password_hash(password):
    """Generate bcrypt hash for password"""
    # Generate salt and hash the password
    salt = bcrypt.gensalt(rounds=12)
    hash_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hash_bytes.decode('utf-8')

def generate_api_key_hash(api_key):
    """Generate SHA-256 hash for API key"""
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

def main():
    if len(sys.argv) > 1:
        input_value = sys.argv[1]
        if input_value.startswith('rr_'):
            # This looks like an API key
            hash_value = generate_api_key_hash(input_value)
            print(f"\nAPI Key: {input_value}")
            print(f"SHA-256 hash: {hash_value}")
            print("\nSQL command to insert API key:")
            print(f"INSERT INTO api_keys (name, key_hash, user_id, is_active) VALUES ('Default API Key', '{hash_value}', 1, TRUE);")
        else:
            # This is a password
            if len(input_value) < 4:
                print("Password should be at least 4 characters long")
                return
            
            hash_value = generate_password_hash(input_value)
            print(f"\nNew password: {input_value}")
            print(f"Bcrypt hash: {hash_value}")
            print("\nSQL command to update admin password:")
            print(f"UPDATE users SET password_hash = '{hash_value}' WHERE username = 'admin';")
            print("\nOr update the mysql_schema.sql INSERT statement:")
            print(f"('admin', '{hash_value}', TRUE);")
    else:
        choice = input("Generate (p)assword hash or (a)pi key hash? [p/a]: ").lower()
        if choice == 'a':
            api_key = input("Enter API key: ")
            hash_value = generate_api_key_hash(api_key)
            print(f"\nAPI Key: {api_key}")
            print(f"SHA-256 hash: {hash_value}")
            print("\nSQL command to insert API key:")
            print(f"INSERT INTO api_keys (name, key_hash, user_id, is_active) VALUES ('Default API Key', '{hash_value}', 1, TRUE);")
        else:
            password = input("Enter new admin password: ")
            if len(password) < 4:
                print("Password should be at least 4 characters long")
                return
            
            hash_value = generate_password_hash(password)
            print(f"\nNew password: {password}")
            print(f"Bcrypt hash: {hash_value}")
            print("\nSQL command to update admin password:")
            print(f"UPDATE users SET password_hash = '{hash_value}' WHERE username = 'admin';")
            print("\nOr update the mysql_schema.sql INSERT statement:")
            print(f"('admin', '{hash_value}', TRUE);")

if __name__ == "__main__":
    main()
