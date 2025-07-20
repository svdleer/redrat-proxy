#!/usr/bin/env python3
"""
RedRat XML Command Debugging Tool
Parse proper RedRat Signal DB XML format and compare with database
"""

import sys
import os
import xml.etree.ElementTree as ET
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import subprocess
import time
import socket

# Load environment variables from .env file
load_dotenv()

def extract_commands_from_redrat_xml(xml_file):
    """Extract command names from RedRat Signal DB XML file."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        commands = []
        
        # RedRat XML structure: AVDeviceDB -> AVDevices -> AVDevice -> Signals -> IRPacket
        # Look for Name elements within IRPacket elements
        for device in root.findall('.//AVDevice'):
            device_name = device.find('Name')
            device_name_text = device_name.text if device_name is not None else "Unknown"
            
            print(f"Found device: {device_name_text}")
            
            signals = device.find('Signals')
            if signals is not None:
                for packet in signals.findall('IRPacket'):
                    name_elem = packet.find('Name')
                    if name_elem is not None and name_elem.text:
                        commands.append({
                            'device': device_name_text,
                            'command': name_elem.text,
                            'uid': packet.find('UID').text if packet.find('UID') is not None else None
                        })
        
        return commands
    except Exception as e:
        print(f"Error reading XML file: {e}")
        return []

def create_ssh_tunnel():
    """Create SSH tunnel to access remote MySQL database."""
    ssh_host = "access-engineering.nl"
    ssh_port = 65001
    ssh_user = "svdleer"
    local_port = 3307  # Use different port to avoid conflicts
    remote_host = "localhost"  # MySQL on remote server
    remote_port = 3306
    
    # Check if tunnel already exists
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', local_port))
        sock.close()
        if result == 0:
            print(f"SSH tunnel already exists on port {local_port}")
            return local_port
    except:
        pass
    
    # Create SSH tunnel
    ssh_command = [
        "ssh", "-N", "-L", 
        f"{local_port}:{remote_host}:{remote_port}",
        f"{ssh_user}@{ssh_host}",
        "-p", str(ssh_port)
    ]
    
    print(f"Creating SSH tunnel: {' '.join(ssh_command)}")
    
    try:
        # Start SSH tunnel in background
        process = subprocess.Popen(ssh_command, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Wait a moment for tunnel to establish
        time.sleep(2)
        
        # Check if tunnel is working
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', local_port))
        sock.close()
        
        if result == 0:
            print(f"SSH tunnel established successfully on port {local_port}")
            return local_port
        else:
            print("Failed to establish SSH tunnel")
            return None
            
    except Exception as e:
        print(f"Error creating SSH tunnel: {e}")
        return None

def get_database_commands():
    """Get IR commands from the database."""
    try:
        # Create SSH tunnel first
        local_port = create_ssh_tunnel()
        if not local_port:
            print("Failed to create SSH tunnel, cannot connect to database")
            return []
        
        # Database connection parameters via SSH tunnel
        config = {
            'host': '127.0.0.1',  # Connect via SSH tunnel
            'port': local_port,
            'database': os.getenv('MYSQL_DB', 'redrat_proxy'),
            'user': os.getenv('MYSQL_USER', 'redrat'),
            'password': os.getenv('MYSQL_PASSWORD', 'password')
        }
        
        print(f"Connecting to MySQL via SSH tunnel: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Get all IR commands from command_templates table
        cursor.execute("""
            SELECT ct.name, r.name as device_name 
            FROM command_templates ct 
            JOIN remote_files rf ON ct.file_id = rf.id 
            LEFT JOIN remotes r ON rf.name = r.name
            ORDER BY r.name, ct.name
        """)
        
        commands = []
        for (command, device) in cursor:
            commands.append({
                'device': device or 'Unknown',
                'command': command
            })
        
        return commands
        
    except Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def compare_commands(xml_file):
    """Compare XML commands with database commands."""
    print(f"Analyzing RedRat XML file: {xml_file}")
    print("-" * 60)
    
    # Extract commands from XML
    xml_commands = extract_commands_from_redrat_xml(xml_file)
    print(f"Found {len(xml_commands)} commands in XML file:")
    
    # Group by device
    devices = {}
    for cmd in xml_commands:
        device = cmd['device']
        if device not in devices:
            devices[device] = []
        devices[device].append(cmd['command'])
    
    for device, commands in devices.items():
        print(f"\n{device} ({len(commands)} commands):")
        for cmd in sorted(commands):
            print(f"  - {cmd}")
    
    # Get database commands
    print(f"\n" + "=" * 60)
    db_commands = get_database_commands()
    print(f"Found {len(db_commands)} commands in database:")
    
    # Group database commands by device
    db_devices = {}
    for cmd in db_commands:
        device = cmd['device']
        if device not in db_devices:
            db_devices[device] = []
        db_devices[device].append(cmd['command'])
    
    for device, commands in db_devices.items():
        print(f"\n{device} ({len(commands)} commands):")
        for cmd in sorted(commands):
            print(f"  - {cmd}")
    
    # Compare and find missing commands
    print(f"\n" + "=" * 60)
    print("COMPARISON ANALYSIS:")
    print("-" * 60)
    
    # Check for POWER specifically
    xml_power_commands = []
    for cmd in xml_commands:
        if 'power' in cmd['command'].lower():
            xml_power_commands.append(f"{cmd['device']}: {cmd['command']}")
    
    db_power_commands = []
    for cmd in db_commands:
        if 'power' in cmd['command'].lower():
            db_power_commands.append(f"{cmd['device']}: {cmd['command']}")
    
    print(f"\nPOWER commands in XML: {len(xml_power_commands)}")
    for cmd in xml_power_commands:
        print(f"  - {cmd}")
    
    print(f"\nPOWER commands in database: {len(db_power_commands)}")
    for cmd in db_power_commands:
        print(f"  - {cmd}")
    
    if xml_power_commands and not db_power_commands:
        print("\n⚠️  ISSUE FOUND: POWER commands exist in XML but not in database!")
        print("   This suggests the import process may have failed or filtered out POWER commands.")
    elif not xml_power_commands:
        print("\n✅ No POWER commands found in XML file.")
    else:
        print("\n✅ POWER commands found in both XML and database.")
    
    # Check for missing commands by device
    for device in devices.keys():
        if device in db_devices:
            xml_set = set(devices[device])
            db_set = set(db_devices[device])
            
            missing_in_db = xml_set - db_set
            extra_in_db = db_set - xml_set
            
            if missing_in_db:
                print(f"\n⚠️  {device} - Commands in XML but missing in database:")
                for cmd in sorted(missing_in_db):
                    print(f"     - {cmd}")
            
            if extra_in_db:
                print(f"\n📝 {device} - Commands in database but not in XML:")
                for cmd in sorted(extra_in_db):
                    print(f"     - {cmd}")
        else:
            print(f"\n⚠️  Device '{device}' found in XML but not in database!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_redrat_xml.py <xml_file>")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    compare_commands(xml_file)
