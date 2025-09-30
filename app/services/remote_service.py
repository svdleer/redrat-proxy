import sys
import os
import xml.etree.ElementTree as ET
import json
import datetime

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from ..mysql_db import db

def process_single_signal(signal_elem, override_name, signals, remote_name, parent_mod_freq=None):
    """Process a single signal element and add it to the signals list"""
    name = signal_elem.find('Name')
    if name is None:
        # Try alternative tag name
        name = signal_elem.find('n')
        
    # Use override name if provided, otherwise use the element's name
    signal_name = override_name if override_name else (name.text if name is not None else None)
    
    uid_elem = signal_elem.find('UID')
    mod_freq_elem = signal_elem.find('ModulationFreq')
    
    # If ModulationFreq not found, try case variations
    if mod_freq_elem is None:
        for child in signal_elem:
            if child.tag.lower() in ['modulationfreq', 'modulation_freq', 'modulationfrequency']:
                mod_freq_elem = child

                break
    
    sig_data_elem = signal_elem.find('SigData')
    

    
    # Get additional signal parameters
    no_repeats_elem = signal_elem.find('NoRepeats')
    intra_sig_pause_elem = signal_elem.find('IntraSigPause')
    
    # Extract Lengths array
    lengths = []
    lengths_elem = signal_elem.find('Lengths')
    if lengths_elem is not None:
        for length_elem in lengths_elem.findall('double'):
            if length_elem.text:
                lengths.append(float(length_elem.text))
    
    # Extract ToggleData
    toggle_data = []
    toggle_data_elem = signal_elem.find('ToggleData')
    if toggle_data_elem is not None:
        for toggle_bit in toggle_data_elem.findall('ToggleBit'):
            bit_no = toggle_bit.find('bitNo')
            len1 = toggle_bit.find('len1')
            len2 = toggle_bit.find('len2')
            if bit_no is not None and len1 is not None and len2 is not None:
                toggle_data.append({
                    'bitNo': int(bit_no.text) if bit_no.text else 0,
                    'len1': int(len1.text) if len1.text else 0,
                    'len2': int(len2.text) if len2.text else 0
                })
    
    # Only add signals with complete data
    if (signal_name and 
        uid_elem is not None and uid_elem.text and
        sig_data_elem is not None and sig_data_elem.text):
        
        signal_data = {
            'name': signal_name,
            'uid': uid_elem.text,
            'modulation_freq': mod_freq_elem.text if mod_freq_elem is not None else (parent_mod_freq or "36000"),
            'sig_data': sig_data_elem.text,
            'no_repeats': int(no_repeats_elem.text) if no_repeats_elem is not None and no_repeats_elem.text else 1,
            'intra_sig_pause': float(intra_sig_pause_elem.text) if intra_sig_pause_elem is not None and intra_sig_pause_elem.text else 0.0,
            'lengths': lengths,
            'toggle_data': toggle_data
        }
        signals.append(signal_data)

        return True
    else:
        skip_reason = []
        if not signal_name:
            skip_reason.append("no name")
        if uid_elem is None or not uid_elem.text:
            skip_reason.append("no UID")
        if sig_data_elem is None or not sig_data_elem.text:
            skip_reason.append("no SigData")

        return False

def parse_remotes_xml(xml_path):
    """Parse the remotes XML file and return a list of remote devices with their commands"""

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

    except Exception as e:

        return []
    
    remotes = []
    
    # Debug: Print all child elements

    
    # Try different ways to find AVDevice elements
    avdevices_container = root.find('AVDevices')
    if avdevices_container is not None:

        devices = avdevices_container.findall('AVDevice')
    elif root.tag == 'AVDevice':

        devices = [root]  # Use the root element itself
    else:

        devices = root.findall('.//AVDevice')
    

    
    # Loop through all AVDevice elements
    for device in devices:
        remote_name = device.find('Name')
        if remote_name is None:
            # Try alternative tag name
            remote_name = device.find('n')
            
        # Skip if no name found
        if remote_name is None or not remote_name.text:

            continue
            
        remote_name = remote_name.text

        
        manufacturer = device.find('Manufacturer').text if device.find('Manufacturer') is not None else None
        device_model = device.find('DeviceModelNumber').text if device.find('DeviceModelNumber') is not None else None
        remote_model = device.find('RemoteModelNumber').text if device.find('RemoteModelNumber') is not None else None
        device_type = device.find('DeviceType').text if device.find('DeviceType') is not None else None
        decoder_class = device.find('DecoderClass').text if device.find('DecoderClass') is not None else None
        
        # Extract configuration data
        config = {}
        for config_elem in ['RCCorrection', 'CreateDelta', 'DecodeDelta', 'DoubleSignals', 'KeyboardSignals', 'XMP1Signals']:
            if device.find(config_elem) is not None:
                # Convert to string to avoid bytes serialization issues
                config[config_elem] = ET.tostring(device.find(config_elem), encoding='unicode')
        
        signals = []
        
        # Look for signals in the Signals container
        signals_container = device.find('Signals')
        if signals_container is not None:

            signal_elements = signals_container.findall('IRPacket')
        else:

            signal_elements = device.findall('.//IRPacket')
        

        
        for signal in signal_elements:
            # Handle regular signals and DoubleSignal containers
            signal_type = signal.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
            
            if signal_type == 'DoubleSignal':
                # Handle DoubleSignal type (contains Signal1 and Signal2)
                # For DoubleSignal, create a single command using Signal1 data as primary
                name = signal.find('Name')
                if name is not None and name.text:
                    base_name = name.text
                    
                    signal1 = signal.find('Signal1')
                    signal2 = signal.find('Signal2')
                    
                    # DEBUG: Print DoubleSignal details for command "1"
                    if base_name == "1":

                        if signal1 is not None:
                            sig1_mod_freq = signal1.find('ModulationFreq')

                        if signal2 is not None:
                            sig2_mod_freq = signal2.find('ModulationFreq')


                    
                    # Use Signal1 as the primary signal for the command (most common approach)
                    if signal1 is not None:
                        process_single_signal(signal1, base_name, signals, remote_name, None)
                    else:
                        # No valid signal found, skip this command
                        logger.warning(f"No valid signal found for command {base_name}")

            else:
                # Handle regular ModulatedSignal
                process_single_signal(signal, None, signals, remote_name, None)
        
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

                imported_count += 1
            
            # Create command templates directly from the signals (no file storage needed)
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
                    'toggle_data': signal.get('toggle_data', [])
                }
                
                # Check for existing template by name and remote_id (not file_id)
                cursor.execute(
                    "SELECT id FROM command_templates WHERE name = %s AND JSON_EXTRACT(template_data, '$.remote_id') = %s",
                    (signal['name'], remote_id)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing template
                    cursor.execute(
                        "UPDATE command_templates SET template_data = %s WHERE id = %s",
                        (json.dumps(template_data), result[0])
                    )

                else:
                    # Create new template linked to remote_id (use remote_id as file_id for compatibility)
                    cursor.execute(
                        """INSERT INTO command_templates 
                           (file_id, name, device_type, template_data, created_by) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (remote_id, signal['name'], remote['device_type'], json.dumps(template_data), user_id)
                    )

                
                conn.commit()
                
    return imported_count

def import_remotes_from_xml(xml_path, user_id):
    """Import remotes from an XML file"""
    # Parse the XML file
    remotes = parse_remotes_xml(xml_path)

    
    if not remotes:
        return 0
    
    # Import the remotes to the database
    imported = import_remotes_to_db(remotes, user_id)
    
    return imported