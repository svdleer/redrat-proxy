#!/usr/bin/env python3
"""
Generate bcrypt password hash for RedRat admin user
"""
import bcrypt
import sys

def generate_password_hash(password):
    """Generate bcrypt hash for password"""
    # Generate salt and hash the password
    salt = bcrypt.gensalt(rounds=12)
    hash_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hash_bytes.decode('utf-8')

def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
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
