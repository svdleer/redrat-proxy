import sys
import os
import json
import datetime
import binascii
import re

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from ..mysql_db import db

def parse_irnetbox_content(content):
    """Parse IRNetBox content and return device name and signals."""
    signals = {}
    device_name = "Unknown"
    
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        if line.startswith('Device '):
            device_name = line.replace('Device ', '').strip()
            i += 1
            continue
            
        if 'Signal data as IRNetBox' in line or 'Note:' in line or 'Where signals' in line:
            i += 1
            continue
            
        if 'MOD_SIG' in line or 'DMOD_SIG' in line:
            if '<' in line and '>' in line:
                i += 1
                continue
                
            parts = line.strip().split('\t')
            
            if 'DMOD_SIG' in line and len(parts) >= 4:
                signal_name = parts[0]
                signal_type = parts[2]
                lengths_and_data = parts[3].strip().split(' ', 1)
                if len(lengths_and_data) >= 2:
                    max_lengths = int(lengths_and_data[0])
                    hex_data = lengths_and_data[1].strip()
                else:
                    i += 1
                    continue
                if signal_type != 'signal1':
                    i += 1
                    continue
                key = signal_name
            elif 'MOD_SIG' in line and 'DMOD_SIG' not in line and len(parts) >= 4:
                signal_name = parts[0]
                max_lengths = int(parts[2])
                hex_data = parts[3].strip()
                key = signal_name
            else:
                i += 1
                continue
                
            frequency = 38000
            num_repeats = 1
            
            try:
                if hex_data:
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_data)
                    
                    if len(clean_hex) % 2 == 1:
                        clean_hex = '0' + clean_hex
                        
                    signal_bytes = binascii.unhexlify(clean_hex)
                    
                    if len(signal_bytes) >= 12:
                        timer_value = int.from_bytes(signal_bytes[4:6], byteorder='big')
                        if timer_value > 0:
                            frequency = int(1000000 / timer_value)
                        
                        num_periods = int.from_bytes(signal_bytes[6:8], byteorder='big')
                        if num_periods > 1:
                            num_repeats = num_periods
                    
                    print(f"Parsed signal {key}: freq={frequency}Hz, repeats={num_repeats}, data_len={len(signal_bytes)}")
                    
                    signals[key] = {
                        'name': key,
                        'frequency': frequency,
                        'data': binascii.hexlify(signal_bytes).decode('ascii').upper(),
                        'repeats': num_repeats,
                        'max_lengths': max_lengths
                    }
                    
            except Exception as e:
                print(f"Error processing signal {key}: {e}")
            
        i += 1
    
    return device_name, signals

def parse_irnetbox_file(file_path):
    """Parse an IRNetBox format .txt file and return device name and signals."""
    with open(file_path, 'r') as file:
        content = file.read()
    
    return parse_irnetbox_content(content)
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        if line.startswith('Device '):
            device_name = line.replace('Device ', '').strip()
            i += 1
            continue
            
        if 'Signal data as IRNetBox' in line or 'Note:' in line or 'Where signals' in line:
            i += 1
            continue
            
        if 'MOD_SIG' in line or 'DMOD_SIG' in line:
            if '<' in line and '>' in line:
                i += 1
                continue
                
            parts = line.strip().split('\t')
            
            if 'DMOD_SIG' in line and len(parts) >= 4:
                signal_name = parts[0]
                signal_type = parts[2]
                lengths_and_data = parts[3].strip().split(' ', 1)
                if len(lengths_and_data) >= 2:
                    max_lengths = int(lengths_and_data[0])
                    hex_data = lengths_and_data[1].strip()
                else:
                    i += 1
                    continue
                if signal_type != 'signal1':
                    i += 1
                    continue
                key = signal_name
            elif 'MOD_SIG' in line and 'DMOD_SIG' not in line and len(parts) >= 4:
                signal_name = parts[0]
                max_lengths = int(parts[2])
                hex_data = parts[3].strip()
                key = signal_name
            else:
                i += 1
                continue
                
            frequency = 38000
            num_repeats = 1
            
            try:
                if hex_data:
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_data)
                    
                    if len(clean_hex) % 2 == 1:
                        clean_hex = '0' + clean_hex
                        
                    signal_bytes = binascii.unhexlify(clean_hex)
                    
                    if len(signal_bytes) >= 12:
                        timer_value = int.from_bytes(signal_bytes[4:6], byteorder='big')
                        if timer_value > 0:
                            frequency = int(1000000 / timer_value)
                        
                        num_periods = int.from_bytes(signal_bytes[6:8], byteorder='big')
                        if num_periods > 1:
                            num_repeats = num_periods
                    
                    print(f"Parsed signal {key}: freq={frequency}Hz, repeats={num_repeats}, data_len={len(signal_bytes)}")
                    
                    signals[key] = {
                        'name': key,
                        'frequency': frequency,
                        'data': binascii.hexlify(signal_bytes).decode('ascii').upper(),
                        'repeats': num_repeats,
                        'max_lengths': max_lengths
                    }
                    
            except Exception as e:
                print(f"Error processing signal {key}: {e}")
            
        i += 1
    
    return device_name, signals

def import_remotes_to_db(remotes, user_id=None):
    """Import the remotes into the database"""
    # Get admin user ID for uploads if not provided
    if user_id is None:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
            result = cursor.fetchone()
            if result:
                user_id = result[0]
            else:
                raise Exception("No admin user found and no user ID provided")
    
    imported_count = 0
    
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
                conn.commit()
                imported_count += 1  # Count updated remotes too
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
                imported_count += 1
            
            # Save the signals as an IRDB file
            signals_data = json.dumps({
                'remote_name': remote['name'],
                'manufacturer': remote['manufacturer'],
                'device_type': remote['device_type'],
                'signals': remote['signals']
            })
            
            # Create a filename based on the remote name
            filename = f"{remote['name'].replace(' ', '_')}.txt"
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
                    (remote['name'], filename, filepath, remote['device_type'], user_id)
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
                    'modulation_freq': signal['modulation_freq'],
                    'no_repeats': signal.get('no_repeats', 1),
                    'intra_sig_pause': signal.get('intra_sig_pause', 0.0),
                    'lengths': signal.get('lengths', []),
                    'toggle_data': signal.get('toggle_data', []),
                    'max_lengths': signal.get('max_lengths', 16)
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
                        (file_id, signal['name'], remote['device_type'], json.dumps(template_data), user_id)
                    )
                    print(f"Created command template '{signal['name']}' for remote '{remote['name']}'")
                
                conn.commit()
                
    return imported_count

def import_remotes_from_irnetbox(txt_content, user_id):
    """Import remotes from IRNetBox txt content"""
    # Parse the IRNetBox content
    device_name, signals = parse_irnetbox_content(txt_content)
    print(f"Found device '{device_name}' with {len(signals)} signals in IRNetBox file")
    
    if not signals:
        return 0
    
    # Convert to format expected by import_remotes_to_db
    remotes = [{
        'name': device_name,
        'manufacturer': 'IRNetBox',
        'device_model_number': None,
        'remote_model_number': None,
        'device_type': 'IRNetBox',
        'decoder_class': None,
        'config_data': {},
        'signals': [
            {
                'name': signal_name,
                'uid': f"irnetbox_{signal_name}",
                'modulation_freq': str(signal_data['frequency']),
                'sig_data': signal_data['data'],
                'no_repeats': signal_data['repeats'],
                'intra_sig_pause': 0.0,
                'lengths': [],
                'toggle_data': []
            }
            for signal_name, signal_data in signals.items()
        ]
    }]
    
    # Count total signals across all remotes
    total_signals = sum(len(remote.get('signals', [])) for remote in remotes)
    
    # Import the remotes to the database
    imported = import_remotes_to_db(remotes, user_id)
    
    # Return the number of signals imported
    return total_signals
