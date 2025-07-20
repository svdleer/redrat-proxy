#!/usr/bin/env python3
"""
RedRat JSON Command Import Debugging Tool
Compare JSON file commands with database entries
"""

import json
import sys
import mysql.connector
from mysql.connector import Error
from pathlib import Path

def parse_json_commands(json_file):
    """Parse commands from RedRat JSON file"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        commands = []
        
        # Extract remote information
        remote_name = data.get('remote_name', 'Unknown')
        manufacturer = data.get('manufacturer', 'Unknown')
        device_type = data.get('device_type', 'Unknown')
        
        print(f"📋 Remote: {remote_name} ({manufacturer}) - {device_type}")
        
        # Extract signal commands
        if 'signals' in data:
            for signal in data['signals']:
                name = signal.get('name')
                if name:
                    commands.append({
                        'name': name,
                        'uid': signal.get('uid', 'N/A'),
                        'modulation_freq': signal.get('modulation_freq', 'N/A'),
                        'has_sig_data': bool(signal.get('sig_data')),
                        'no_repeats': signal.get('no_repeats', 0)
                    })
        
        return remote_name, commands
        
    except Exception as e:
        print(f"❌ Error parsing JSON file: {e}")
        return None, []

def check_database_commands(remote_name=None):
    """Check what commands are in the database"""
    try:
        # Database connection parameters
        db_config = {
            'host': 'localhost',
            'database': 'redrat_proxy',
            'user': 'redrat_user',
            'password': 'secure_password123'
        }
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        if remote_name:
            query = """
            SELECT ct.name as command_name, rf.name as remote_name, ct.template_data, rf.file_path
            FROM command_templates ct 
            JOIN remote_files rf ON ct.file_id = rf.id 
            WHERE rf.name LIKE %s OR rf.file_path LIKE %s
            ORDER BY ct.name;
            """
            cursor.execute(query, (f'%{remote_name}%', f'%{remote_name}%'))
        else:
            query = """
            SELECT ct.name as command_name, rf.name as remote_name, ct.template_data, rf.file_path
            FROM command_templates ct 
            JOIN remote_files rf ON ct.file_id = rf.id
            ORDER BY rf.name, ct.name;
            """
            cursor.execute(query)
        
        results = cursor.fetchall()
        
        db_commands = []
        for row in results:
            command_name, remote_name_db, template_data, file_path = row
            db_commands.append({
                'name': command_name,
                'remote_name': remote_name_db,
                'has_template_data': bool(template_data),
                'file_path': file_path
            })
        
        cursor.close()
        connection.close()
        
        return db_commands
        
    except Error as e:
        print(f"❌ Database error: {e}")
        return []

def compare_commands(json_commands, db_commands, remote_name):
    """Compare JSON commands with database commands"""
    
    print(f"\n🔍 Comparing commands for remote: {remote_name}")
    print("=" * 60)
    
    # Convert to sets for comparison (case-insensitive)
    json_command_names = {cmd['name'].upper() for cmd in json_commands}
    db_command_names = {cmd['name'].upper() for cmd in db_commands}
    
    print(f"\n📄 JSON file commands ({len(json_command_names)}):")
    for cmd in sorted(json_command_names):
        print(f"  • {cmd}")
    
    print(f"\n💾 Database commands ({len(db_command_names)}):")
    for cmd in sorted(db_command_names):
        print(f"  • {cmd}")
    
    # Find missing commands
    missing_in_db = json_command_names - db_command_names
    missing_in_json = db_command_names - json_command_names
    common_commands = json_command_names & db_command_names
    
    print(f"\n✅ Common commands ({len(common_commands)}):")
    for cmd in sorted(common_commands):
        print(f"  • {cmd}")
    
    if missing_in_db:
        print(f"\n❌ Commands in JSON but missing in database ({len(missing_in_db)}):")
        for cmd in sorted(missing_in_db):
            print(f"  • {cmd}")
            # Find the original command details
            for json_cmd in json_commands:
                if json_cmd['name'].upper() == cmd:
                    print(f"    - UID: {json_cmd['uid']}")
                    print(f"    - Freq: {json_cmd['modulation_freq']} Hz")
                    print(f"    - Has data: {json_cmd['has_sig_data']}")
                    break
    
    if missing_in_json:
        print(f"\n⚠️  Commands in database but missing in JSON ({len(missing_in_json)}):")
        for cmd in sorted(missing_in_json):
            print(f"  • {cmd}")
    
    return {
        'json_commands': len(json_command_names),
        'db_commands': len(db_command_names),
        'common': len(common_commands),
        'missing_in_db': len(missing_in_db),
        'missing_in_json': len(missing_in_json),
        'missing_commands': list(missing_in_db)
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_json_command_import.py <json_file_path>")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        sys.exit(1)
    
    print(f"🔍 Analyzing RedRat JSON file: {json_file.name}")
    print("=" * 60)
    
    # Parse JSON commands
    remote_name, json_commands = parse_json_commands(json_file)
    
    if not json_commands:
        print("❌ No commands found in JSON file")
        sys.exit(1)
    
    # Check database commands
    print(f"\n💾 Checking database for remote: {remote_name}")
    db_commands = check_database_commands(remote_name)
    
    if not db_commands:
        print(f"❌ No commands found in database for remote: {remote_name}")
        print("\n🔍 Checking all database commands...")
        db_commands = check_database_commands()
        
        if db_commands:
            print(f"\n💾 Found {len(db_commands)} total commands in database:")
            remotes = {}
            for cmd in db_commands:
                remote = cmd['remote_name']
                if remote not in remotes:
                    remotes[remote] = []
                remotes[remote].append(cmd['name'])
            
            for remote, commands in remotes.items():
                print(f"  📡 {remote}: {len(commands)} commands")
        else:
            print("❌ No commands found in database at all")
            sys.exit(1)
    
    # Compare commands
    results = compare_commands(json_commands, db_commands, remote_name)
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 30)
    print(f"JSON commands: {results['json_commands']}")
    print(f"DB commands: {results['db_commands']}")
    print(f"Common: {results['common']}")
    print(f"Missing in DB: {results['missing_in_db']}")
    print(f"Missing in JSON: {results['missing_in_json']}")
    
    if results['missing_in_db'] > 0:
        print(f"\n🚨 ISSUE DETECTED: {results['missing_in_db']} commands are missing from database!")
        print("Missing commands:", ", ".join(results['missing_commands']))
    else:
        print(f"\n✅ All JSON commands are present in the database!")

if __name__ == "__main__":
    main()
