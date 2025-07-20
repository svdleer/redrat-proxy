#!/usr/bin/env python3
"""
RedRat Database Cleanup and Re-import Script
Cleans up incorrectly imported DoubleSignal entries and re-imports with correct logic
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

def get_db_connection():
    """Get database connection via SSH tunnel."""
    local_port = create_ssh_tunnel()
    if not local_port:
        print("Failed to create SSH tunnel")
        return None
    
    config = {
        'host': '127.0.0.1',
        'port': local_port,
        'database': os.getenv('MYSQL_DB', 'redrat_proxy'),
        'user': os.getenv('MYSQL_USER', 'redrat'),
        'password': os.getenv('MYSQL_PASSWORD', 'password')
    }
    
    try:
        connection = mysql.connector.connect(**config)
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def cleanup_database():
    """Remove all imported remote data to start fresh."""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        print("🧹 Cleaning up database...")
        
        # Delete in correct order due to foreign key constraints
        cursor.execute("DELETE FROM command_templates")
        deleted_templates = cursor.rowcount
        print(f"   Deleted {deleted_templates} command templates")
        
        cursor.execute("DELETE FROM remote_files")
        deleted_files = cursor.rowcount
        print(f"   Deleted {deleted_files} remote files")
        
        cursor.execute("DELETE FROM remotes")
        deleted_remotes = cursor.rowcount
        print(f"   Deleted {deleted_remotes} remotes")
        
        # Reset auto-increment counters
        cursor.execute("ALTER TABLE command_templates AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE remote_files AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE remotes AUTO_INCREMENT = 1")
        
        connection.commit()
        print("✅ Database cleanup completed")
        return True
        
    except Error as e:
        print(f"❌ Database cleanup error: {e}")
        connection.rollback()
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def process_single_signal(signal_elem, command_name, remote_id, file_id, cursor):
    """Process a single signal element and insert into database."""
    # Extract signal data
    uid_elem = signal_elem.find('UID')
    uid = uid_elem.text if uid_elem is not None else None
    
    mod_freq_elem = signal_elem.find('ModulationFreq')
    mod_freq = mod_freq_elem.text if mod_freq_elem is not None else "38000"
    
    sig_data_elem = signal_elem.find('SigData')
    sig_data = sig_data_elem.text if sig_data_elem is not None else ""
    
    no_repeats_elem = signal_elem.find('NoRepeats')
    no_repeats = int(no_repeats_elem.text) if no_repeats_elem is not None else 1
    
    intra_sig_pause_elem = signal_elem.find('IntraSigPause')
    intra_sig_pause = float(intra_sig_pause_elem.text) if intra_sig_pause_elem is not None else 0.0
    
    # Extract lengths
    lengths = []
    lengths_elem = signal_elem.find('Lengths')
    if lengths_elem is not None:
        for double_elem in lengths_elem.findall('double'):
            if double_elem.text:
                lengths.append(float(double_elem.text))
    
    # Extract toggle data
    toggle_data = []
    toggle_data_elem = signal_elem.find('ToggleData')
    if toggle_data_elem is not None:
        for toggle_bit in toggle_data_elem.findall('ToggleBit'):
            bit_no_elem = toggle_bit.find('bitNo')
            len1_elem = toggle_bit.find('len1')
            len2_elem = toggle_bit.find('len2')
            
            if all(elem is not None for elem in [bit_no_elem, len1_elem, len2_elem]):
                toggle_data.append({
                    'bitNo': int(bit_no_elem.text),
                    'len1': int(len1_elem.text),
                    'len2': int(len2_elem.text)
                })
    
    # Create template data JSON
    template_data = {
        'uid': uid,
        'command': command_name,
        'remote_id': remote_id,
        'modulation_freq': mod_freq,
        'signal_data': sig_data,
        'no_repeats': no_repeats,
        'intra_sig_pause': intra_sig_pause,
        'lengths': lengths,
        'toggle_data': toggle_data
    }
    
    # Get device type from remotes table
    cursor.execute("SELECT device_type FROM remotes WHERE id = %s", (remote_id,))
    result = cursor.fetchone()
    device_type = result[0] if result else 'UNKNOWN'
    
    # Insert command template
    insert_query = """
        INSERT INTO command_templates (file_id, name, device_type, template_data, created_by, created_at)
        VALUES (%s, %s, %s, %s, 1, NOW())
    """
    
    cursor.execute(insert_query, (file_id, command_name, device_type, str(template_data).replace("'", '"')))
    print(f"     ✓ {command_name}")

def import_xml_file(xml_file):
    """Import XML file with corrected DoubleSignal logic."""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        cursor = connection.cursor()
        
        print(f"📥 Importing XML file: {xml_file}")
        
        # Process each AVDevice
        for device in root.findall('.//AVDevice'):
            device_name_elem = device.find('Name')
            if device_name_elem is None or not device_name_elem.text:
                continue
            
            device_name = device_name_elem.text
            print(f"\n🔧 Processing device: {device_name}")
            
            # Get device info
            manufacturer_elem = device.find('Manufacturer')
            manufacturer = manufacturer_elem.text if manufacturer_elem is not None else 'Unknown'
            
            device_model_elem = device.find('DeviceModelNumber')
            device_model = device_model_elem.text if device_model_elem is not None else None
            
            remote_model_elem = device.find('RemoteModelNumber')
            remote_model = remote_model_elem.text if remote_model_elem is not None else None
            
            device_type_elem = device.find('DeviceType')
            device_type = device_type_elem.text if device_type_elem is not None else 'UNKNOWN'
            
            decoder_class_elem = device.find('DecoderClass')
            decoder_class = decoder_class_elem.text if decoder_class_elem is not None else 'default'
            
            # Insert remote
            remote_insert = """
                INSERT INTO remotes (name, manufacturer, device_model_number, remote_model_number, 
                                   device_type, decoder_class, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            description = f"Manufacturer: {manufacturer}, Type: {device_type}"
            cursor.execute(remote_insert, (device_name, manufacturer, device_model, remote_model, 
                                         device_type, decoder_class, description))
            remote_id = cursor.lastrowid
            
            # Insert remote file entry
            file_insert = """
                INSERT INTO remote_files (name, filename, filepath, device_type, uploaded_by, uploaded_at)
                VALUES (%s, %s, %s, %s, 1, NOW())
            """
            
            filename = f"{device_name}.xml"
            filepath = f"static/remote_files/{filename}"
            cursor.execute(file_insert, (device_name, filename, filepath, device_type))
            file_id = cursor.lastrowid
            
            # Process signals with corrected DoubleSignal logic
            signals_elem = device.find('Signals')
            if signals_elem is not None:
                signal_count = 0
                for signal in signals_elem.findall('IRPacket'):
                    signal_type = signal.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
                    name_elem = signal.find('Name')
                    
                    if name_elem is None or not name_elem.text:
                        continue
                    
                    command_name = name_elem.text
                    
                    if signal_type == 'DoubleSignal':
                        # Handle DoubleSignal correctly - treat as ONE command
                        print(f"   📡 Processing DoubleSignal: {command_name}")
                        signal1 = signal.find('Signal1')
                        if signal1 is not None:
                            # Use Signal1 as the primary signal (keep original name)
                            process_single_signal(signal1, command_name, remote_id, file_id, cursor)
                            signal_count += 1
                        else:
                            print(f"     ⚠️  Warning: DoubleSignal '{command_name}' has no Signal1")
                    else:
                        # Handle regular ModulatedSignal
                        print(f"   📡 Processing ModulatedSignal: {command_name}")
                        process_single_signal(signal, command_name, remote_id, file_id, cursor)
                        signal_count += 1
                
                print(f"   ✅ Imported {signal_count} signals for {device_name}")
        
        connection.commit()
        print(f"\n🎉 XML import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        connection.rollback()
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def verify_import():
    """Verify the import worked correctly."""
    print(f"\n🔍 Verifying import...")
    
    # Use our existing debug script to check the results
    os.system("python3 debug_redrat_xml.py remotes.xml")

def main():
    print("🚀 RedRat Database Cleanup and Re-import")
    print("=" * 50)
    
    xml_file = "remotes.xml"
    
    if not os.path.exists(xml_file):
        print(f"❌ XML file not found: {xml_file}")
        return
    
    # Step 1: Cleanup database
    print("\nStep 1: Database Cleanup")
    if not cleanup_database():
        print("❌ Failed to cleanup database")
        return
    
    # Step 2: Re-import with corrected logic
    print("\nStep 2: Re-import XML with corrected logic")
    if not import_xml_file(xml_file):
        print("❌ Failed to import XML file")
        return
    
    # Step 3: Verify results
    print("\nStep 3: Verification")
    verify_import()
    
    print(f"\n✅ Process completed!")
    print("The POWER command should now appear as 'POWER' (not POWER_Signal1/Signal2)")

if __name__ == "__main__":
    main()
