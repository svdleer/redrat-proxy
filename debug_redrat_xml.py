#!/usr/bin/env python3
"""
RedRat XML Command Debugging Tool
Parse proper RedRat Signal DB XML format and compare with database
"""

import sys
import xml.etree.ElementTree as ET
import mysql.connector
from mysql.connector import Error

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

def get_database_commands():
    """Get IR commands from the database."""
    try:
        # Database connection parameters
        config = {
            'host': 'localhost',
            'database': 'redrat_db',
            'user': 'redrat_user',
            'password': 'redrat_password'
        }
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Get all IR commands
        cursor.execute("SELECT command, device FROM ir_commands ORDER BY device, command")
        
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
