import sys
import os
import json
import binascii
import base64
import hashlib
import re
from datetime import datetime

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from ..mysql_db import db

def detect_irnetbox_format(filepath):
    """Detect if file is in IRNetBox format"""
    try:
        with open(filepath, 'r') as f:
            content = f.read(500)  # Read first 500 chars
            
            # IRNetBox format indicators
            if 'Signal data as IRNetBox data blocks' in content:
                return True
            if 'MOD_SIG' in content or 'DMOD_SIG' in content:
                return True
            if content.startswith('Device '):
                return True
                
        return False
    except Exception:
        return False

def parse_irnetbox_file(file_path):
    """
    Parse an IRNetBox format .txt file and return device name and signals.
    
    Returns:
        tuple: (device_name, signals_dict)
    """
    signals = {}
    device_name = "Unknown"
    
    # Read the file
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Parse device name from first line
        if line.startswith('Device '):
            device_name = line.replace('Device ', '').strip()
            i += 1
            continue
            
        # Skip description lines
        if 'Signal data as IRNetBox' in line or 'Note:' in line or 'Where signals' in line:
            i += 1
            continue
            
        # Parse signal lines (both MOD_SIG and DMOD_SIG)
        if 'MOD_SIG' in line or 'DMOD_SIG' in line:
            # Skip documentation lines containing angle brackets
            if '<' in line and '>' in line:
                i += 1
                continue
                
            # Split by tabs for the IRNetBox format
            parts = line.strip().split('\t')
            
            if 'DMOD_SIG' in line and len(parts) >= 4:
                signal_name = parts[0]
                # DMOD_SIG format: signal_name \t DMOD_SIG \t signal1/signal2 \t max_lengths hex_data
                signal_type = parts[2]  # 'signal1' or 'signal2'
                # Parts[3] contains "max_lengths hex_data" combined, need to split
                lengths_and_data = parts[3].strip().split(' ', 1)
                if len(lengths_and_data) >= 2:
                    max_lengths = int(lengths_and_data[0])
                    hex_data = lengths_and_data[1].strip()
                else:
                    i += 1
                    continue
                # Only process signal1 for simplicity
                if signal_type != 'signal1':
                    i += 1
                    continue
                key = signal_name  # Use just the signal name, not the combined key
            elif 'MOD_SIG' in line and 'DMOD_SIG' not in line and len(parts) >= 4:
                signal_name = parts[0]
                # MOD_SIG format: signal_name \t MOD_SIG \t max_lengths \t hex_data
                max_lengths = int(parts[2])
                hex_data = parts[3].strip()
                key = signal_name
            else:
                i += 1
                continue
                
            # Convert hex string to bytes and analyze
            frequency = 38000  # Default for consumer IR
            num_repeats = 1    # Default
            
            try:
                if hex_data:
                    # Clean hex data - remove all non-hex characters
                    import re  # Ensure re is available in this scope
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_data)
                    
                    # Handle odd-length hex strings (IRNetBox format may have nibble alignment)
                    if len(clean_hex) % 2 == 1:
                        clean_hex = '0' + clean_hex  # Pad with leading zero
                        
                    signal_bytes = binascii.unhexlify(clean_hex)
                    
                    if len(signal_bytes) >= 12:
                        # RedRat MK4 structure: intra_pause(4) + timer(2) + periods(2) + lengths_info(2) + ...
                        # Extract timer value (bytes 4-5, big-endian) and convert to frequency
                        timer_value = int.from_bytes(signal_bytes[4:6], byteorder='big')
                        if timer_value > 0:
                            frequency = int(1000000 / timer_value)  # Convert to Hz
                        
                        # Extract number of periods (bytes 6-7, big-endian)
                        num_periods = int.from_bytes(signal_bytes[6:8], byteorder='big')
                        if num_periods > 1:
                            num_repeats = num_periods
                    
                    # Debug output
                    print(f"Parsed signal {key}: freq={frequency}Hz, repeats={num_repeats}, data_len={len(signal_bytes)}")
                    
                    # Store in signals dictionary
                    signals[key] = {
                        'name': key,
                        'frequency': frequency,
                        'data': binascii.hexlify(signal_bytes).decode('ascii').upper(),
                        'repeats': num_repeats,
                        'max_lengths': max_lengths
                    }
                    
            except Exception as e:
                print(f"Error processing signal {key}: {e}")
            
        # Move to next line
        i += 1
    
    return device_name, signals
def create_template_data(signal_name, signal_info):
    """Create the complete template_data JSON with SigData"""
    
    # Generate a UID (using signal_name for consistency)
    uid_hash = hashlib.md5(f"{signal_info.get('device_name', 'Device')}-{signal_name}".encode()).hexdigest()[:22]
    uid = uid_hash + "=="  # Add padding to make it look like base64
    
    # Use actual timing lengths extracted from signal data
    lengths = signal_info.get('timing_lengths', [])
    
    template_data = {
        "uid": uid,
        "lengths": lengths,
        "frequency": signal_info['frequency'],
        "num_repeats": signal_info.get('repeats', 1),  # Use 'repeats' key from parsed data
        "pause_ms": signal_info.get('pause_ms', 0),  # Include pause timing
        "sigdata": signal_info.get('data', ''),  # Use 'data' key from parsed data
        "device_type": signal_info.get('device_name', 'IRNetBox Device'),
        "signal_type": "IRNetBox",  # Set a default signal type
        "max_lengths": signal_info.get('max_lengths', 16),  # Default max_lengths
        "remote_id": signal_info.get('remote_id')  # Link to remotes table
    }
    
    return json.dumps(template_data)

def import_irnetbox_to_db(device_name, signals, user_id=None):
    """Import IRNetBox signals into the database"""
    
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
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if this remote already exists in remotes table
        cursor.execute("SELECT id FROM remotes WHERE name = %s", (device_name,))
        existing_remote = cursor.fetchone()
        
        if existing_remote:
            remote_id = existing_remote[0]
            print(f"Remote '{device_name}' already exists in remotes table with ID {remote_id}")
            # Delete existing command templates for this remote
            cursor.execute("DELETE FROM command_templates WHERE JSON_EXTRACT(template_data, '$.remote_id') = %s", (remote_id,))
            deleted_count = cursor.rowcount
            print(f"Deleted {deleted_count} existing command templates")
        else:
            # Create new remote entry in remotes table
            cursor.execute("""
                INSERT INTO remotes (name, manufacturer, device_type, description)
                VALUES (%s, %s, %s, %s)
            """, (device_name, 'IRNetBox', 'IRNetBox', f'Imported from IRNetBox format'))
            remote_id = cursor.lastrowid
            print(f"Created new remote '{device_name}' with ID {remote_id}")
        
        # Check if remote file already exists
        cursor.execute("SELECT id FROM remote_files WHERE name = %s", (device_name,))
        result = cursor.fetchone()
        
        # Create filename
        filename = f"{device_name.replace(' ', '_').replace('-', '_')}_IRNetBox.txt"
        filepath = f"static/remote_files/{filename}"
        
        if result:
            file_id = result[0]
            print(f"Remote file '{device_name}' already exists with ID {file_id}, updating...")
        else:
            # Create new remote file entry
            cursor.execute("""
                INSERT INTO remote_files (name, filename, filepath, device_type, uploaded_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (device_name, filename, filepath, 'IRNetBox', user_id))
            file_id = cursor.lastrowid
            print(f"Created new remote file '{device_name}' with ID {file_id}")
        
        # Import all signals
        imported_count = 0
        for signal_name, signal_info in signals.items():
            # Add device name and remote_id to signal info for template creation
            signal_info['device_name'] = device_name
            signal_info['remote_id'] = remote_id
            
            template_data = create_template_data(signal_name, signal_info)
            
            cursor.execute("""
                INSERT INTO command_templates 
                (file_id, name, device_type, template_data, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                file_id,
                signal_name,
                device_name,
                template_data,
                user_id
            ))
            imported_count += 1
            print(f"Imported command '{signal_name}' with complete SigData")
        
        conn.commit()
        print(f"Successfully imported {imported_count} commands for {device_name}")
        
        return imported_count

def import_remotes_from_irnetbox(filepath, user_id):
    """Import remotes from an IRNetBox format file"""
    
    # Debug: Check file exists and size
    import os
    if not os.path.exists(filepath):
        raise Exception(f"File does not exist: {filepath}")
    
    file_size = os.path.getsize(filepath)
    print(f"DEBUG: File {filepath} exists, size: {file_size} bytes")
    
    # Debug: Check first few lines
    with open(filepath, 'r') as f:
        first_lines = [f.readline().strip() for _ in range(5)]
    print(f"DEBUG: First 5 lines: {first_lines}")
    
    # Validate file format
    format_valid = detect_irnetbox_format(filepath)
    print(f"DEBUG: Format detection result: {format_valid}")
    if not format_valid:
        raise Exception("File is not in valid IRNetBox format")
    
    # Parse the IRNetBox file
    print(f"DEBUG: Starting to parse IRNetBox file")
    device_name, signals = parse_irnetbox_file(filepath)
    print(f"DEBUG: Parse completed - device: {device_name}, signals: {len(signals)}")
    
    if not signals:
        raise Exception("No valid signals found in IRNetBox file")
    
    print(f"Found device '{device_name}' with {len(signals)} signals")
    
    # Import to database
    imported_count = import_irnetbox_to_db(device_name, signals, user_id)
    
    return imported_count
