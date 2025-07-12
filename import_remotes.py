#!/usr/bin/env python3

# Script to import remotes.xml into the database
# This script reads the RedRat XML file and imports the devices and signals into the database

import sys
import os
import xml.etree.ElementTree as ET
import uuid
import json
import datetime

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from mysql_db import db

def parse_remotes_xml(xml_path):
    """Parse the remotes XML file and return a list of remote devices with their commands"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file: {e}")
        return []
    
    remotes = []
    
    # Loop through all AVDevice elements
    for device in root.findall('.//AVDevice'):
        remote_name = device.find('n').text if device.find('n') is not None else None
        if not remote_name:
            continue
            
        manufacturer = device.find('Manufacturer').text if device.find('Manufacturer') is not None else None
        device_model = device.find('DeviceModelNumber').text if device.find('DeviceModelNumber') is not None else None
        remote_model = device.find('RemoteModelNumber').text if device.find('RemoteModelNumber') is not None else None
        device_type = device.find('DeviceType').text if device.find('DeviceType') is not None else None
        decoder_class = device.find('DecoderClass').text if device.find('DecoderClass') is not None else None
        
        # Extract configuration data
        config = {}
        for config_elem in ['RCCorrection', 'CreateDelta', 'DecodeDelta', 'DoubleSignals', 'KeyboardSignals', 'XMP1Signals']:
            if device.find(config_elem) is not None:
                config[config_elem] = ET.tostring(device.find(config_elem), encoding='unicode')
        
        signals = []
        for signal in device.findall('.//IRPacket'):
            name = signal.find('Name')
            uid_elem = signal.find('UID')
            mod_freq_elem = signal.find('ModulationFreq')
            sig_data_elem = signal.find('SigData')
            
            # Only add signals with complete data
            if (name is not None and name.text and 
                uid_elem is not None and uid_elem.text and
                sig_data_elem is not None and sig_data_elem.text):
                
                signals.append({
                    'name': name.text,
                    'uid': uid_elem.text,
                    'modulation_freq': mod_freq_elem.text if mod_freq_elem is not None else "36000",
                    'sig_data': sig_data_elem.text
                })
        
        remotes.append({
            'name': remote_name,
            'manufacturer': manufacturer,
            'device_model_number': device_model,
            'remote_model_number': remote_model,
            'device_type': device_type,
            'decoder_class': decoder_class,
            'config_data': config,
            'signals': signals
        })
    
    return remotes

def import_remotes_to_db(remotes):
    """Import the remotes into the database"""
    # Get admin user ID for uploads
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
        admin_id = cursor.fetchone()[0]
    
    # Process each remote
    for remote in remotes:
        if not remote['name']:
            print("Skipping remote with no name")
            continue
            
        # Save the remote
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if remote already exists
            cursor.execute("SELECT id FROM remotes WHERE name = %s", (remote['name'],))
            result = cursor.fetchone()
            
            # Prepare config data JSON
            config_json = json.dumps(remote['config_data']) if remote['config_data'] else None
            description = f"Manufacturer: {remote['manufacturer']}, Type: {remote['device_type']}"
            
            if result:
                remote_id = result[0]
                print(f"Remote '{remote['name']}' already exists with ID {remote_id}, updating...")
                # Update the remote with new data
                cursor.execute("""
                    UPDATE remotes SET 
                    manufacturer = %s, 
                    device_model_number = %s, 
                    remote_model_number = %s, 
                    device_type = %s, 
                    decoder_class = %s, 
                    description = %s, 
                    config_data = %s
                    WHERE id = %s
                """, (
                    remote['manufacturer'],
                    remote['device_model_number'],
                    remote['remote_model_number'],
                    remote['device_type'],
                    remote['decoder_class'],
                    description,
                    config_json,
                    remote_id
                ))
            else:
                # Create the remote
                cursor.execute("""
                    INSERT INTO remotes (
                        name, manufacturer, device_model_number, remote_model_number, 
                        device_type, decoder_class, description, config_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    remote['name'], 
                    remote['manufacturer'],
                    remote['device_model_number'],
                    remote['remote_model_number'],
                    remote['device_type'],
                    remote['decoder_class'],
                    description,
                    config_json
                ))
                remote_id = cursor.lastrowid
                conn.commit()
                print(f"Created new remote '{remote['name']}' with ID {remote_id}")
            
            # Save the signals as an IRDB file
            signals_data = json.dumps({
                'remote_name': remote['name'],
                'manufacturer': remote['manufacturer'],
                'device_type': remote['device_type'],
                'signals': remote['signals']
            })
            
            # Create a filename based on the remote name
            filename = f"{remote['name'].replace(' ', '_')}.xml"
            filepath = f"static/remote_files/{filename}"
            
            # Make sure the directory exists
            os.makedirs("app/static/remote_files", exist_ok=True)
            
            # Write the signal data to a file
            with open(f"app/{filepath}", 'w') as f:
                f.write(signals_data)
            
            # Add the remote file to the database
            cursor.execute("SELECT id FROM remote_files WHERE filename = %s", (filename,))
            result = cursor.fetchone()
            
            if result:
                file_id = result[0]
                print(f"Remote file '{filename}' already exists with ID {file_id}")
            else:
                cursor.execute(
                    "INSERT INTO remote_files (name, filename, filepath, device_type, uploaded_by) VALUES (%s, %s, %s, %s, %s)",
                    (remote['name'], filename, filepath, remote['device_type'], admin_id)
                )
                file_id = cursor.lastrowid
                conn.commit()
                print(f"Created new remote file '{filename}' with ID {file_id}")
            
            # Create command templates from the signals
            for signal in remote['signals']:
                if not signal['name']:
                    continue
                    
                template_data = {
                    'remote_id': remote_id,
                    'command': signal['name'],
                    'signal_data': signal['sig_data'],
                    'uid': signal['uid'],
                    'modulation_freq': signal['modulation_freq']
                }
                
                cursor.execute(
                    "SELECT id FROM command_templates WHERE name = %s AND file_id = %s",
                    (signal['name'], file_id)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing template
                    cursor.execute(
                        "UPDATE command_templates SET template_data = %s WHERE id = %s",
                        (json.dumps(template_data), result[0])
                    )
                    print(f"Updated command template '{signal['name']}' for remote '{remote['name']}'")
                else:
                    # Create new template
                    cursor.execute(
                        """INSERT INTO command_templates 
                           (file_id, name, device_type, template_data, created_by) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (file_id, signal['name'], remote['device_type'], json.dumps(template_data), admin_id)
                    )
                    print(f"Created command template '{signal['name']}' for remote '{remote['name']}'")
                
                conn.commit()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    else:
        xml_path = "remotes.xml"
    
    print(f"Importing remotes from {xml_path}")
    
    # Initialize database
    db.init_db()
    
    # Parse the XML file
    remotes = parse_remotes_xml(xml_path)
    print(f"Found {len(remotes)} remotes in XML file")
    
    # Import the remotes to the database
    import_remotes_to_db(remotes)
    
    print("Import completed!")

if __name__ == "__main__":
    main()
