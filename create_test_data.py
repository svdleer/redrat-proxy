#!/usr/bin/env python3

# This script adds some test data to the database for showcasing the dashboard
# It adds remotes and commands

import sys
import os
import random
from datetime import datetime, timedelta

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from mysql_db import db

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

def add_remotes(count=5):
    """Add sample remotes to the database"""
    # First, check if we already have remotes
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM remotes")
        existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Database already contains {existing_count} remotes. Skipping remote creation.")
        return
    
    # Select a random subset of remotes to add
    selected_remotes = random.sample(REMOTE_NAMES, min(count, len(REMOTE_NAMES)))
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        for remote_name in selected_remotes:
            description = f"IR Remote for {remote_name}"
            image_path = None  # No images for now
            
            try:
                cursor.execute(
                    "INSERT INTO remotes (name, description, image_path) VALUES (%s, %s, %s)",
                    (remote_name, description, image_path)
                )
                print(f"Added remote: {remote_name}")
            except Exception as err:
                print(f"Error adding remote {remote_name}: {err}")
        
        conn.commit()

def add_commands(count=20):
    """Add sample commands to the database"""
    # First, check if we already have commands
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM commands")
        existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Database already contains {existing_count} commands. Skipping command creation.")
        return
    
    # Get all remote IDs
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM remotes")
        remote_ids = [row[0] for row in cursor.fetchall()]
    
    if not remote_ids:
        print("No remotes found in database. Add remotes first.")
        return
    
    # Get admin user ID
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
        admin_id = cursor.fetchone()[0]
    
    # Add random commands
    with db.get_connection() as conn:
        cursor = conn.cursor()
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
            except Exception as err:
                print(f"Error adding command: {err}")
        
        conn.commit()
        print(f"Added {count} sample commands")

def main():
    """Main function to add test data to the database"""
    print("Creating test data for RedRat dashboard...")
    
    # Initialize database
    db.init_db()
    
    # Add sample remotes
    add_remotes(count=5)
    
    # Add sample commands
    add_commands(count=30)
    
    print("Test data creation complete!")

if __name__ == "__main__":
    main()
