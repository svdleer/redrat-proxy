#!/usr/bin/env python3
"""
Quick database table check
"""

import sys
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import subprocess
import time
import socket

load_dotenv()

def create_ssh_tunnel():
    """Create SSH tunnel to access remote MySQL database."""
    ssh_host = "access-engineering.nl"
    ssh_port = 65001
    ssh_user = "svdleer"
    local_port = 3307
    remote_host = "localhost"
    remote_port = 3306
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', local_port))
        sock.close()
        if result == 0:
            print(f"SSH tunnel already exists on port {local_port}")
            return local_port
    except:
        pass
    
    return None

def check_database():
    """Check database tables and structure."""
    try:
        local_port = create_ssh_tunnel()
        if not local_port:
            print("No SSH tunnel available")
            return
        
        config = {
            'host': '127.0.0.1',
            'port': local_port,
            'database': os.getenv('MYSQL_DB', 'redrat_proxy'),
            'user': os.getenv('MYSQL_USER', 'redrat'),
            'password': os.getenv('MYSQL_PASSWORD', 'password')
        }
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Show all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"Tables in database '{config['database']}':")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check if we have any IR-related tables
        for table in tables:
            table_name = table[0]
            if 'ir' in table_name.lower() or 'command' in table_name.lower() or 'remote' in table_name.lower():
                print(f"\nDescribing table '{table_name}':")
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col[0]} - {col[1]}")
                
                # Show sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                print(f"  Sample data ({len(rows)} rows):")
                for row in rows:
                    print(f"    {row}")
        
    except Error as e:
        print(f"Database error: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    check_database()
