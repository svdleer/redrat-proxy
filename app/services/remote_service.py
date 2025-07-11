import sys
import os
import xml.etree.ElementTree as ET
import json
import datetime
import logging

# Try to import necessary modules with fallbacks for testing
try:
    from werkzeug.utils import secure_filename
except ImportError:
    def secure_filename(filename):
        return filename.replace(' ', '_')

try:
    from app.utils.logger import logger
except ImportError:
    logger = logging.getLogger("redrat")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from ..mysql_db import db


class RemoteService:
    """Service for handling remote operations"""
    
    @staticmethod
    def upload_remote_file(file, user_id):
        """Upload an XML file containing remote data"""
        if not file.filename.endswith('.xml'):
            raise ValueError("Only .xml files are accepted")
        
        filename = secure_filename(file.filename)
        filepath = f"static/remote_files/{filename}"
        
        # Make sure the directory exists
        os.makedirs("app/static/remote_files", exist_ok=True)
        
        file.save(f"app/{filepath}")
        
        if db:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if file already exists
                cursor.execute("SELECT id FROM remote_files WHERE filename = %s", (filename,))
                result = cursor.fetchone()
                
                if result:
                    file_id = result[0]
                    logger.info(f"Remote file '{filename}' already exists with ID {file_id}")
                else:
                    cursor.execute(
                        """INSERT INTO remote_files 
                           (name, filename, filepath, uploaded_by) 
                           VALUES (%s, %s, %s, %s)""",
                        (filename, filename, filepath, user_id)
                    )
                    file_id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"Created new remote file '{filename}' with ID {file_id}")
        
        logger.info(f"Uploaded remote XML file: {filename}")
        return f"app/{filepath}"

    @staticmethod
    def get_remote_files():
        """Get all remote files"""
        if not db:
            return []
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM remote_files")
            return cursor.fetchall()
    
    @staticmethod
    def get_remote_file(file_id):
        """Get a specific remote file by ID"""
        if not db:
            return None
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM remote_files WHERE id = %s", (file_id,))
            return cursor.fetchone()


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
                config[config_elem] = ET.tostring(device.find(config_elem), encoding='unicode')
        
        signals = []
        for signal in device.findall('.//IRPacket'):
            name = signal.find('Name')
            if name is None:
                # Try alternative tag name
                name = signal.find('n')
                
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
                        (file_id, signal['name'], remote['device_type'], json.dumps(template_data), user_id)
                    )
                    print(f"Created command template '{signal['name']}' for remote '{remote['name']}'")
                
                conn.commit()
                
    return imported_count

def import_remotes_from_xml(xml_path, user_id):
    """Import remotes from an XML file"""
    # Initialize database
    db.init_db()
    
    # Parse the XML file
    remotes = parse_remotes_xml(xml_path)
    print(f"Found {len(remotes)} remotes in XML file")
    
    if not remotes:
        return 0
    
    # Import the remotes to the database
    imported = import_remotes_to_db(remotes, user_id)
    
    return imported
