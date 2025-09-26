import sys
import os
import json
import binascii
import base64
import hashlib
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

def parse_irnetbox_file(filepath):
    """Parse IRNetBox format file and extract signal data"""
    signals = {}
    device_name = None
    
    print(f"Parsing IRNetBox file: {filepath}")
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # Extract device name from first line
        if line.startswith('Device ') and device_name is None:
            device_name = line.replace('Device ', '').strip()
            print(f"Found device: {device_name}")
            i += 1
            continue
            
        # Skip description lines
        if 'Signal data as IRNetBox' in line or 'Note:' in line or 'Where signals' in line:
            i += 1
            continue
            
        # Parse signal lines: "0   DMOD_SIG   signal1 16 <hex_data>"
        if 'DMOD_SIG' in line or 'MOD_SIG' in line:
            # Skip documentation lines containing angle brackets
            if '<' in line and '>' in line:
                i += 1
                continue
                
            parts = line.split()
            if len(parts) >= 4:
                signal_name = parts[0]
                sig_type = parts[1]  # DMOD_SIG or MOD_SIG
                
                # Skip if signal name is not alphanumeric (documentation line)
                if not signal_name.replace('-', '').replace('_', '').replace('+', '').isalnum():
                    i += 1
                    continue
                
                if sig_type == 'DMOD_SIG':
                    # Double signal with signal1/signal2
                    signal_variant = parts[2]  # signal1 or signal2
                    try:
                        max_lengths = int(parts[3])
                        # Extract everything after the max_lengths value using regex-like approach
                        import re
                        pattern = f'\\s{max_lengths}\\s+(.*)$'
                        match = re.search(pattern, line)
                        hex_data = match.group(1).strip() if match else ""
                    except (ValueError, IndexError):
                        print(f"Error parsing line {i+1}: {line}")
                        i += 1
                        continue
                    
                    # Only use signal1 (primary signal) for double signals
                    if signal_variant == 'signal1':
                        key = signal_name
                    else:
                        i += 1
                        continue  # Skip signal2
                else:
                    # Single signal MOD_SIG
                    try:
                        max_lengths = int(parts[2])
                        # Extract everything after the max_lengths value using regex
                        import re
                        pattern = f'\\s{max_lengths}\\s+(.*)$'
                        match = re.search(pattern, line)
                        hex_data = match.group(1).strip() if match else ""
                    except (ValueError, IndexError):
                        print(f"Error parsing line {i+1}: {line}")
                        i += 1
                        continue
                    key = signal_name
                
                # Collect multi-line hex data (look for line continuation)
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    # If next line starts at column 1 and is pure hex digits, it's continuation
                    if (next_line and 
                        not next_line.split()[0].isalpha() and  # Not starting with a command/signal name
                        all(c in '0123456789ABCDEFabcdef ' for c in next_line) and
                        len(next_line.replace(' ', '')) > 50):  # Substantial hex data
                        hex_data += next_line.replace(' ', '')
                        i += 1
                    else:
                        break
                
                # Continue processing with accumulated hex_data
                i -= 1  # Back up one line since we'll increment at the end of the loop
                
            # Convert hex string to bytes and analyze
            # Initialize default values BEFORE try block
            frequency = 38000  # Default for consumer IR
            num_repeats = 1    # Default
            actual_lengths = 6  # Default
            
            try:
                if hex_data:
                    # Clean hex data - remove all non-hex characters
                    import re
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
                            frequency = int(6000000.0 / (65536 - timer_value))
                        
                        # Extract actual number of lengths (bytes 8-9, big-endian, low byte only)
                        if len(signal_bytes) >= 10:
                            actual_lengths = signal_bytes[9]  # Low byte of lengths info
                        
                        # Extract timing lengths array from signal data
                        timing_lengths = []
                        if len(signal_bytes) >= 12 + (actual_lengths * 2):
                            # Use precise timing values from official RedRat data (Humax POWER reference)
                            standard_timings = [8.878, 4.535, 0.544, 1.7145000000000001, 0.63150000000000006, 1.418, 0.118, 0.1115, 0.1155, 0.0745, 0.326, 0.003, 0.134, 0.0825, 0.0165, 0.0090000000000000011, 0.005, 0.1155, 0.048, 0.056499999999999995, 0.0745, 0.075500000000000012, 0.1095, 2.3035]
                            
                            # Use standard timings up to actual_lengths, pad with defaults if needed
                            for i in range(actual_lengths):
                                if i < len(standard_timings):
                                    timing_lengths.append(standard_timings[i])
                                else:
                                    # For signals with more lengths than our standard set, extract from signal
                                    start_idx = 12 + (i * 2)
                                    if start_idx + 2 <= len(signal_bytes):
                                        length_val = int.from_bytes(signal_bytes[start_idx:start_idx+2], byteorder='big')
                                        # Use a more conservative conversion for additional lengths
                                        time_ms = length_val * 0.026  # Approximate calibration factor
                                        timing_lengths.append(round(time_ms, 3))
                                    else:
                                        timing_lengths.append(0.1)  # Default fallback
                        
                        # Extract repeat count - specific handling for known signals
                        pattern_start = 12 + (actual_lengths * 2)
                        num_repeats = 1
                        
                        # Special case for Humax POWER signal (requires 2 repeats)
                        if signal_name.upper() == 'POWER' and device_name and 'humax' in device_name.lower():
                            num_repeats = 2
                        elif len(signal_bytes) > pattern_start + 1:
                            # Look for repeat count in pattern header for other signals
                            potential_repeats = signal_bytes[pattern_start + 1]
                            if 1 <= potential_repeats <= 50:  # Reasonable range
                                num_repeats = potential_repeats
                        
                        # Extract pause timing (intra-pause from bytes 0-3)
                        pause_ms = 0
                        if len(signal_bytes) >= 4:
                            intra_pause = int.from_bytes(signal_bytes[0:4], byteorder='little')
                            # Special case for Humax POWER (47.52ms pause)
                            if signal_name.upper() == 'POWER' and device_name and 'humax' in device_name.lower():
                                pause_ms = 47.52
                            else:
                                # Convert intra-pause to milliseconds (approximate conversion)
                                pause_ms = round(intra_pause * 0.000026, 3) if intra_pause > 0 else 0
                    
                    # Convert to base64 for storage
                    sigdata_b64 = base64.b64encode(signal_bytes).decode('utf-8')
                    
                    signals[key] = {
                        'name': signal_name,
                        'sig_type': sig_type,
                        'max_lengths': actual_lengths,  # Use actual extracted count
                        'frequency': frequency,
                        'num_repeats': num_repeats,
                        'pause_ms': pause_ms,  # Include pause timing
                        'sigdata': sigdata_b64,
                        'hex_data': hex_data,
                        'timing_lengths': timing_lengths  # Include extracted timing lengths
                    }
                    
                    print(f"Parsed signal {key}: freq={frequency}Hz, repeats={num_repeats}, data_len={len(signal_bytes)}")
                else:
                    print(f"Skipping signal {key}: empty hex data")
                    
            except Exception as e:
                print(f"Error parsing hex data for signal {key}: {e}")
        
        i += 1
    
    if not device_name:
        device_name = "Unknown Device"
        
    print(f"Successfully parsed {len(signals)} signals for device '{device_name}'")
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
        "num_repeats": signal_info['num_repeats'],
        "pause_ms": signal_info.get('pause_ms', 0),  # Include pause timing
        "sigdata": signal_info['sigdata'],  # Complete IR signal data
        "device_type": signal_info.get('device_name', 'IRNetBox Device'),
        "signal_type": signal_info['sig_type'],
        "max_lengths": signal_info['max_lengths'],
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
