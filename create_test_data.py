#!/usr/bin/env python3

# This script adds some test data to the database for showcasing the dashboard
# It adds remotes and commands

import sys
import os
import mysql.connector
import random
from datetime import datetime, timedelta

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

# Try to import the database configuration
try:
    from app.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
except ImportError:
    # Default values for Docker
    MYSQL_HOST = 'host.docker.internal'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'password'
    MYSQL_DATABASE = 'redrat'

# Remote names and commands for demo data
REMOTE_NAMES = [
    "Living Room TV", "Bedroom TV", "Media Center", "Home Theater",
    "DVD Player", "Apple TV", "Roku", "Fire Stick", "Xbox", "PlayStation"
]

COMMAND_LIST = [
    "Power", "Volume Up", "Volume Down", "Mute", "Channel Up", "Channel Down",
    "Menu", "Exit", "Up", "Down", "Left", "Right", "OK", "Back",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "Play", "Pause", "Stop", "Record", "Rewind", "Fast Forward", "Guide",
    "Source", "Info", "Netflix", "Hulu", "Amazon", "YouTube", "Home"
]

DEVICES = [
    "Samsung TV", "LG TV", "Sony TV", "TCL TV", "Vizio TV",
    "Xbox", "PlayStation", "Roku", "Apple TV", "Fire Stick",
    "Denon AVR", "Yamaha AVR", "Cable Box", "DVD Player", "Blu-ray Player"
]

STATUSES = ["pending", "executed", "failed"]
STATUS_WEIGHTS = [0.1, 0.8, 0.1]  # 10% pending, 80% executed, 10% failed

def connect_to_db():
    """Connect to the MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        sys.exit(1)

def add_remotes(connection, count=5):
    """Add sample remotes to the database"""
    cursor = connection.cursor()
    
    # First, check if we already have remotes
    cursor.execute("SELECT COUNT(*) FROM remotes")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Database already contains {existing_count} remotes. Skipping remote creation.")
        return
    
    # Select a random subset of remotes to add
    selected_remotes = random.sample(REMOTE_NAMES, min(count, len(REMOTE_NAMES)))
    
    for remote_name in selected_remotes:
        description = f"IR Remote for {remote_name}"
        image_path = None  # No images for now
        
        try:
            cursor.execute(
                "INSERT INTO remotes (name, description, image_path) VALUES (%s, %s, %s)",
                (remote_name, description, image_path)
            )
            print(f"Added remote: {remote_name}")
        except mysql.connector.Error as err:
            print(f"Error adding remote {remote_name}: {err}")
    
    connection.commit()

def add_commands(connection, count=20):
    """Add sample commands to the database"""
    cursor = connection.cursor()
    
    # First, check if we already have commands
    cursor.execute("SELECT COUNT(*) FROM commands")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Database already contains {existing_count} commands. Skipping command creation.")
        return
    
    # Get all remote IDs
    cursor.execute("SELECT id FROM remotes")
    remote_ids = [row[0] for row in cursor.fetchall()]
    
    if not remote_ids:
        print("No remotes found in database. Add remotes first.")
        return
    
    # Get admin user ID
    cursor.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
    admin_id = cursor.fetchone()[0]
    
    # Add random commands
    for _ in range(count):
        remote_id = random.choice(remote_ids)
        command = random.choice(COMMAND_LIST)
        device = random.choice(DEVICES)
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        
        # Generate a random timestamp within the last 7 days
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        created_at = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # For executed commands, add an executed_at timestamp
        executed_at = None
        if status == "executed" or status == "failed":
            executed_at = created_at + timedelta(seconds=random.randint(1, 10))
        
        try:
            cursor.execute(
                """INSERT INTO commands 
                   (remote_id, command, device, status, created_by, created_at, executed_at, status_updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (remote_id, command, device, status, admin_id, created_at, executed_at, executed_at or created_at)
            )
        except mysql.connector.Error as err:
            print(f"Error adding command: {err}")
    
    connection.commit()
    print(f"Added {count} sample commands")

def main():
    """Main function to add test data to the database"""
    print("Creating test data for RedRat dashboard...")
    
    connection = connect_to_db()
    try:
        # Add sample remotes
        add_remotes(connection, count=5)
        
        # Add sample commands
        add_commands(connection, count=30)
        
        print("Test data creation complete!")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
