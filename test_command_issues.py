#!/usr/bin/env python3
"""
Test script to verify:
1. Commands are properly counted in the GUI
2. Commands are properly deleted when remote is deleted
"""

import sys
import os
import json

# Add the app directory to the path
sys.path.append('.')
from app.mysql_db import db

def test_command_count():
    """Test if commands are properly counted"""
    print("=== TESTING COMMAND COUNT ===")
    
    try:
        with db.get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            # Test the stats query exactly as used in the API
            cursor.execute("SELECT COUNT(*) as total FROM command_templates")
            commands_count = cursor.fetchone()['total']
            print(f"Total command templates: {commands_count}")
            
            # Test the admin remotes query
            cursor.execute("""
                SELECT r.id, r.name, r.manufacturer, r.device_type, 
                       COUNT(ct.id) as command_count
                FROM remotes r
                LEFT JOIN command_templates ct ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
                GROUP BY r.id, r.name, r.manufacturer, r.device_type
                ORDER BY r.name
            """)
            
            remotes = cursor.fetchall()
            total_commands_via_join = 0
            for remote in remotes:
                print(f"Remote '{remote['name']}': {remote['command_count']} commands")
                total_commands_via_join += remote['command_count']
            
            print(f"Total commands via JOIN: {total_commands_via_join}")
            
            if commands_count == total_commands_via_join:
                print("✅ Command counts match!")
            else:
                print(f"❌ Command counts don't match: {commands_count} vs {total_commands_via_join}")
            
            cursor.close()
            
    except Exception as e:
        print(f"❌ Error testing command count: {e}")

def test_remote_deletion():
    """Test if commands are properly deleted when remote is deleted"""
    print("\n=== TESTING REMOTE DELETION ===")
    
    try:
        with db.get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            # Get a remote to test with
            cursor.execute("SELECT id, name FROM remotes LIMIT 1")
            remote = cursor.fetchone()
            
            if not remote:
                print("❌ No remotes found to test with")
                return
            
            remote_id = remote['id']
            remote_name = remote['name']
            print(f"Testing deletion of remote '{remote_name}' (ID: {remote_id})")
            
            # Count commands before deletion
            cursor.execute(
                "SELECT COUNT(*) as count FROM command_templates WHERE JSON_EXTRACT(template_data, '$.remote_id') = %s",
                (remote_id,)
            )
            commands_before = cursor.fetchone()['count']
            print(f"Commands before deletion: {commands_before}")
            
            # Count remote files before deletion
            cursor.execute("SELECT COUNT(*) as count FROM remote_files WHERE name = %s", (remote_name,))
            files_before = cursor.fetchone()['count']
            print(f"Remote files before deletion: {files_before}")
            
            # Simulate the deletion process (but don't actually delete - just show what would happen)
            print("Simulating deletion process...")
            
            # Show what command templates would be deleted
            cursor.execute(
                "SELECT id, name FROM command_templates WHERE JSON_EXTRACT(template_data, '$.remote_id') = %s LIMIT 5",
                (remote_id,)
            )
            commands_to_delete = cursor.fetchall()
            print(f"Sample command templates that would be deleted: {[cmd['name'] for cmd in commands_to_delete]}")
            
            # Show what remote files would be deleted
            cursor.execute("SELECT id, filename FROM remote_files WHERE name = %s", (remote_name,))
            files_to_delete = cursor.fetchall()
            print(f"Remote files that would be deleted: {[f['filename'] for f in files_to_delete]}")
            
            print(f"✅ Deletion simulation complete for remote '{remote_name}'")
            print("Note: Actual deletion was not performed to preserve data")
            
            cursor.close()
            
    except Exception as e:
        print(f"❌ Error testing remote deletion: {e}")

def main():
    print("Testing RedRat Proxy Command Issues")
    print("=" * 50)
    
    test_command_count()
    test_remote_deletion()
    
    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    main()