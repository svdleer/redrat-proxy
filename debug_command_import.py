#!/usr/bin/env python3
"""
RedRat Command Import Debugging Tool
Compare XML file commands with database entries
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def parse_xml_commands(xml_file):
    """Parse commands from RedRat XML file"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        commands = []
        
        # Look for different XML structures
        # Method 1: Direct command elements
        for cmd in root.findall('.//command'):
            name = cmd.get('name') or cmd.get('id')
            if name:
                commands.append({
                    'name': name,
                    'type': 'direct_command',
                    'has_data': bool(cmd.text and cmd.text.strip())
                })
        
        # Method 2: Signal elements
        for signal in root.findall('.//signal'):
            name = signal.get('name') or signal.get('id')
            if name:
                commands.append({
                    'name': name,
                    'type': 'signal',
                    'has_data': bool(signal.text and signal.text.strip())
                })
        
        # Method 3: Look for any element with IR data
        for elem in root.iter():
            if elem.tag.lower() in ['power', 'power_on', 'power_off'] or 'power' in elem.tag.lower():
                commands.append({
                    'name': elem.tag,
                    'type': 'power_element',
                    'has_data': bool(elem.text and elem.text.strip()),
                    'attributes': dict(elem.attrib)
                })
        
        return commands
        
    except Exception as e:
        print(f"❌ Error parsing XML file: {e}")
        return []

def check_database_commands(remote_name=None):
    """Check what commands are in the database"""
    try:
        # We'll create SQL queries to check the database
        sql_queries = []
        
        if remote_name:
            sql_queries.append(f"""
            SELECT ct.name as command_name, rf.name as remote_name, ct.template_data 
            FROM command_templates ct 
            JOIN remote_files rf ON ct.file_id = rf.id 
            WHERE rf.name LIKE '%{remote_name}%';
            """)
        else:
            sql_queries.append("""
            SELECT ct.name as command_name, rf.name as remote_name, ct.template_data 
            FROM command_templates ct 
            JOIN remote_files rf ON ct.file_id = rf.id;
            """)
        
        return sql_queries
        
    except Exception as e:
        print(f"❌ Error creating database queries: {e}")
        return []

def compare_commands(xml_commands, db_commands):
    """Compare XML and database commands"""
    print("🔍 COMMAND COMPARISON")
    print("=" * 50)
    
    xml_names = set(cmd['name'] for cmd in xml_commands)
    db_names = set(cmd['name'] for cmd in db_commands)
    
    print(f"📄 XML file commands: {len(xml_names)}")
    for name in sorted(xml_names):
        print(f"  - {name}")
    
    print(f"\n💾 Database commands: {len(db_names)}")
    for name in sorted(db_names):
        print(f"  - {name}")
    
    # Find missing commands
    missing_in_db = xml_names - db_names
    missing_in_xml = db_names - xml_names
    
    if missing_in_db:
        print(f"\n⚠️  Commands in XML but NOT in database ({len(missing_in_db)}):")
        for name in sorted(missing_in_db):
            print(f"  - {name}")
    
    if missing_in_xml:
        print(f"\n⚠️  Commands in database but NOT in XML ({len(missing_in_xml)}):")
        for name in sorted(missing_in_xml):
            print(f"  - {name}")
    
    # Case sensitivity check
    print(f"\n🔤 Case Sensitivity Analysis:")
    xml_lower = {name.lower(): name for name in xml_names}
    db_lower = {name.lower(): name for name in db_names}
    
    case_mismatches = []
    for lower_name in xml_lower:
        if lower_name in db_lower and xml_lower[lower_name] != db_lower[lower_name]:
            case_mismatches.append((xml_lower[lower_name], db_lower[lower_name]))
    
    if case_mismatches:
        print("  Case mismatches found:")
        for xml_name, db_name in case_mismatches:
            print(f"    XML: '{xml_name}' ↔ DB: '{db_name}'")
    else:
        print("  No case mismatches detected")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_command_import.py <xml_file> [remote_name]")
        print("\nThis tool compares commands between RedRat XML files and the database")
        print("Examples:")
        print("  python3 debug_command_import.py remote.xml")
        print("  python3 debug_command_import.py remote.xml 'TV Remote'")
        return
    
    xml_file = sys.argv[1]
    remote_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(xml_file).exists():
        print(f"❌ XML file not found: {xml_file}")
        return
    
    print("🔍 RedRat Command Import Debug Tool")
    print("=" * 40)
    print(f"XML File: {xml_file}")
    if remote_name:
        print(f"Remote Filter: {remote_name}")
    print()
    
    # Parse XML commands
    print("📄 Parsing XML file...")
    xml_commands = parse_xml_commands(xml_file)
    
    if not xml_commands:
        print("❌ No commands found in XML file")
        return
    
    print(f"✅ Found {len(xml_commands)} elements in XML")
    
    # Show XML command details
    print("\n📋 XML Commands Detail:")
    for cmd in xml_commands:
        print(f"  {cmd['name']} ({cmd['type']}) - Has data: {cmd['has_data']}")
        if 'attributes' in cmd:
            print(f"    Attributes: {cmd['attributes']}")
    
    # Generate database queries
    print(f"\n💾 Database Query (run these manually):")
    queries = check_database_commands(remote_name)
    for query in queries:
        print(query)
    
    print(f"\n💡 Manual Database Check:")
    print("Connect to your database and run:")
    print("1. List all remote files:")
    print("   SELECT id, name, filename FROM remote_files;")
    print()
    print("2. List all command templates:")
    print("   SELECT ct.name, rf.name as remote_name FROM command_templates ct JOIN remote_files rf ON ct.file_id = rf.id;")
    print()
    print("3. Search for POWER commands (case-insensitive):")
    print("   SELECT * FROM command_templates WHERE LOWER(name) LIKE '%power%';")
    print()
    print("4. Check specific remote file commands:")
    print("   SELECT name FROM command_templates ct JOIN remote_files rf ON ct.file_id = rf.id WHERE rf.filename LIKE '%your_file%';")

if __name__ == '__main__':
    main()
