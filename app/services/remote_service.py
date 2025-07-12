import sys
import os
import xml.etree.ElementTree as ET
import json
import datetime
import logging
import uuid
import base64
from io import BytesIO
import re

# Add support for XML indentation for Python versions before 3.9
if not hasattr(ET, 'indent'):
    def indent(elem, level=0):
        """Add indentation to XML elements for pretty printing"""
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                indent(child, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    # Add the indent function to ElementTree
    ET.indent = indent

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
        """Upload and process an XML file containing remote data
        
        This method processes the XML file without permanently storing it.
        It extracts all remote information and creates appropriate database entries.
        """
        if not file.filename.endswith('.xml'):
            raise ValueError("Only .xml files are accepted")
        
        filename = secure_filename(file.filename)
        logger.info(f"Processing XML file: {filename}")
        
        # Process the file directly without saving
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            # Parse and process the XML file
            remotes = parse_remotes_xml(temp_path)
            if not remotes or len(remotes) == 0:
                raise ValueError("No valid remotes found in XML file")
                
            logger.info(f"Found {len(remotes)} remotes in XML file '{filename}'")
            
            # Log summary of found remotes
            logger.info("Remote summary:")
            for idx, remote in enumerate(remotes, 1):
                signal_count = len(remote['signals']) if 'signals' in remote else 0
                logger.info(f"  {idx}. {remote['name']} - {signal_count} signals")
                
            # Extract basic info from first remote for DB record
            first_remote = remotes[0]
            device_type = first_remote.get('device_type', '')
            manufacturer = first_remote.get('manufacturer', '')
            
            if not manufacturer:
                manufacturer = "Unknown"
            if not device_type:
                device_type = "Generic"
                
            if db:
                # Import the remotes to the database
                imported_count = import_remotes_to_db(remotes, user_id)
                logger.info(f"Successfully imported {imported_count} remotes from '{filename}'")
            
            logger.info(f"Completed processing of remote XML file: {filename}")
            return temp_path
        except Exception as e:
            logger.error(f"Error processing XML file: {str(e)}")
            raise
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Removed temporary file: {temp_path}")

    @staticmethod
    def get_remote_files():
        """Get all remote files with summary information
        
        This method retrieves all remote files and includes
        summary information about associated remotes and templates.
        """
        if not db:
            return []
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get all remote files
            cursor.execute("""
                SELECT rf.*, 
                       COUNT(DISTINCT ct.id) as template_count,
                       COUNT(DISTINCT JSON_EXTRACT(ct.template_data, '$.remote_id')) as remote_count
                FROM remote_files rf
                LEFT JOIN command_templates ct ON ct.file_id = rf.id
                GROUP BY rf.id
                ORDER BY rf.uploaded_at DESC
            """)
            
            return cursor.fetchall()
    
    @staticmethod
    def get_remote_file(file_id):
        """Get a specific remote file by ID with related remote information
        
        This method retrieves the remote file details and includes
        information about all associated remotes and command templates.
        """
        if not db:
            return None
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get the base remote file information
            cursor.execute("SELECT * FROM remote_files WHERE id = %s", (file_id,))
            remote_file = cursor.fetchone()
            
            if not remote_file:
                return None
                
            # Get associated remotes
            cursor.execute("""
                SELECT r.* FROM remotes r 
                JOIN command_templates ct ON ct.template_data->>'$.remote_id' = CONVERT(r.id, CHAR)
                WHERE ct.file_id = %s
                GROUP BY r.id
            """, (file_id,))
            associated_remotes = cursor.fetchall()
            
            # Get command templates count
            cursor.execute("SELECT COUNT(*) as template_count FROM command_templates WHERE file_id = %s", (file_id,))
            template_count = cursor.fetchone()['template_count']
            
            # Add the related information to the result
            remote_file['associated_remotes'] = associated_remotes
            remote_file['template_count'] = template_count
            
            return remote_file

    @staticmethod
    def process_xml_data(xml_data, filename, user_id):
        """Process XML data directly from memory without saving to disk
        
        Args:
            xml_data: The XML content as a string
            filename: Original filename for reference
            user_id: ID of the user uploading the data
            
        Returns:
            Number of remotes imported
        """
        logger.info(f"Processing XML data with reference name: {filename}")
        
        try:
            # Create an ElementTree from the XML string
            root = ET.fromstring(xml_data)
            
            # Create a temporary in-memory structure to hold the XML
            from io import BytesIO
            xml_buffer = BytesIO(xml_data.encode('utf-8'))
            
            # Parse the XML directly from the buffer
            remotes = []
            try:
                tree = ET.parse(xml_buffer)
                xml_root = tree.getroot()
                
                # Get namespace from root if exists
                namespaces = {}
                for prefix, uri in xml_root.attrib.items():
                    if prefix.startswith('xmlns:'):
                        ns_prefix = prefix.split(':', 1)[1]
                        namespaces[ns_prefix] = uri
                
                # Process XML using the same logic as parse_remotes_xml
                # This is a simplified implementation for direct XML content
                # that calls the main parser
                
                # Create a temporary file in memory
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
                temp_path = temp_file.name
                
                try:
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.write(xml_data)
                    
                    # Use the existing parser
                    remotes = parse_remotes_xml(temp_path)
                finally:
                    # Clean up
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
            except Exception as e:
                logger.error(f"Error parsing XML data: {str(e)}")
                raise ValueError(f"Invalid XML format: {str(e)}")
            
            if not remotes or len(remotes) == 0:
                raise ValueError("No valid remotes found in XML data")
            
            logger.info(f"Found {len(remotes)} remotes in XML data")
            
            # Import the remotes to the database
            imported_count = import_remotes_to_db(remotes, user_id)
            logger.info(f"Successfully imported {imported_count} remotes")
            
            return imported_count
            
        except Exception as e:
            logger.error(f"Error processing XML data: {str(e)}")
            raise


def parse_remotes_xml(xml_path):
    """Parse the remotes XML file and return a list of remote devices with their commands
    
    This enhanced parser is capable of handling various XML formats used for
    IR remote definition files, including RedRat, LIRC, Pronto, and others.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"Error parsing XML file: {e}")
        return []
    
    remotes = []
    
    # Get namespace from root if exists
    namespaces = {}
    for prefix, uri in root.attrib.items():
        if prefix.startswith('xmlns:'):
            ns_prefix = prefix.split(':', 1)[1]
            namespaces[ns_prefix] = uri
    
    # Try to identify the XML type
    xml_type = "unknown"
    if root.tag == "remotes":
        xml_type = "redrat"
    elif root.tag == "irplus":
        xml_type = "irplus"
    elif root.tag.endswith("config"):
        xml_type = "lircd"
    elif root.tag == "device-command-table":
        xml_type = "harmony"
        
    logger.info(f"Processing XML of detected type: {xml_type}")
    
    # Define the device elements to search for based on common XML formats
    device_elements = [
        './/AVDevice',         # RedRat format
        './/Device',           # Standard format
        './/Remote',           # LIRC and other formats
        './/device',           # lowercase format
        './/remote',           # lowercase format
        '.'                    # Root as fallback if it contains direct device data
    ]
    
    # Find all device elements across different possible XML structures
    devices = []
    for device_path in device_elements:
        found_devices = root.findall(device_path)
        if found_devices:
            devices.extend(found_devices)
            logger.debug(f"Found {len(found_devices)} devices using path '{device_path}'")
    
    # If no devices found through standard paths, try the root itself
    if not devices and xml_type != "unknown":
        devices = [root]
        logger.debug("Using root element as the device container")
    
    # Remove duplicates while preserving order
    unique_devices = []
    device_tags = set()
    for device in devices:
        # Use a combination of tag and available identifiers to de-duplicate
        device_id = f"{device.tag}_{device.get('id', '')}_{device.get('name', '')}"
        if device_id not in device_tags:
            device_tags.add(device_id)
            unique_devices.append(device)
    
    logger.info(f"Found {len(unique_devices)} unique device elements to process")
    
    # Process each device
    for device in unique_devices:
        # Extract device name with extensive fallbacks
        remote_name = extract_element_text(device, [
            'Name', 'n', 'DeviceName', 'RemoteName', 'name', 'device-name', 'remoteName', 
            'deviceName', 'DisplayName', 'displayName', 'Label', 'label'
        ])
        
        # Also check attributes if no element found
        if not remote_name:
            for attr in ['name', 'id', 'label', 'displayName']:
                if attr in device.attrib:
                    remote_name = device.attrib[attr]
                    break
        
        # As a last resort, try to extract name from the filename
        if not remote_name and xml_path:
            basename = os.path.basename(xml_path)
            if basename.endswith('.xml'):
                remote_name = basename[:-4].replace('_', ' ').title()
        
        # Skip if still no name found
        if not remote_name:
            logger.warning("Skipping device element with no identifiable name")
            continue
            
        # Extract manufacturer with fallbacks
        manufacturer = extract_element_text(device, [
            'Manufacturer', 'Make', 'Brand', 'maker', 'mfg', 'manufacturer',
            'vendor', 'Vendor', 'Company', 'company'
        ])
        
        # Extract model numbers
        device_model = extract_element_text(device, [
            'DeviceModelNumber', 'DeviceModel', 'ModelNumber', 'Model', 'model',
            'deviceModel', 'productNumber', 'ProductNumber', 'ProductCode', 'productCode'
        ])
                
        remote_model = extract_element_text(device, [
            'RemoteModelNumber', 'RemoteModel', 'ControllerModel', 'RemoteType',
            'remoteModel', 'controllerModel', 'remoteType'
        ])
                
        # Extract device type and category
        device_type = extract_element_text(device, [
            'DeviceType', 'Type', 'Category', 'deviceType', 'type', 'category',
            'deviceCategory', 'DeviceCategory', 'class', 'Class'
        ])
        
        # Default to "Unknown" for critical fields if not found
        if not manufacturer:
            manufacturer = "Unknown"
        if not device_type:
            device_type = "Unknown"
                
        # Extract decoder information
        decoder_class = extract_element_text(device, [
            'DecoderClass', 'Decoder', 'Protocol', 'protocol', 'decoderClass',
            'irProtocol', 'IRProtocol', 'signalFormat', 'SignalFormat'
        ])
        
        # Extract extensive metadata
        metadata = {}
        meta_fields = [
            'Notes', 'Description', 'Comment', 'Protocol', 'Version', 'Brand', 'Region',
            'Source', 'CreatedBy', 'CreatedDate', 'ModifiedBy', 'ModifiedDate',
            'SoftwareVersion', 'HardwareVersion', 'FirmwareVersion', 'Author',
            'notes', 'description', 'comment', 'protocol', 'version', 'brand', 'region'
        ]
        
        # Look for metadata both in direct child elements and attributes
        for meta_field in meta_fields:
            # Check for element
            value = extract_element_text(device, [meta_field])
            if value:
                metadata[meta_field.lower()] = value
            # Also check attributes
            elif meta_field in device.attrib:
                metadata[meta_field.lower()] = device.attrib[meta_field]
        
        # Extract custom attributes and add to metadata
        for attr_name, attr_value in device.attrib.items():
            if attr_name not in ['Name', 'ID', 'Type'] and attr_value and attr_name.lower() not in metadata:
                metadata[attr_name.lower()] = attr_value
        
        # Process image data and path
        image_path = None
        image_data = None
        
        # Try multiple methods to find image data
        
        # Method 1: Direct path reference
        for img_field in ['Image', 'ImagePath', 'RemoteImage', 'image', 'imagePath', 'remoteImage', 'icon', 'Icon']:
            img_elem = device.find(img_field)
            if img_elem is not None and img_elem.text:
                image_path = img_elem.text
                break
            if img_field in device.attrib:
                image_path = device.attrib[img_field]
                break
        
        # Method 2: Base64 encoded image
        for img_field in ['ImageData', 'imageData', 'base64Image', 'Base64Image', 'EncodedImage']:
            img_elem = device.find(img_field)
            if img_elem is not None and img_elem.text:
                try:
                    image_data = img_elem.text
                    # Save image data for later processing
                    break
                except Exception as e:
                    logger.warning(f"Failed to decode base64 image: {e}")
            
        # Method 3: Look for image tags with src attributes
        for img_tag in device.findall('.//img'):
            if 'src' in img_tag.attrib:
                image_path = img_tag.attrib['src']
                break
                
        # Extract button layout information with enhanced detail
        button_layout = {}
        layout_paths = [
            'ButtonLayout', 'Layout', 'Buttons', 'buttons', 'buttonLayout', 'keyMapping', 'KeyMapping'
        ]
        
        for path in layout_paths:
            layout_element = device.find(path)
            if layout_element is not None:
                # Method 1: Standard button elements
                for button in layout_element.findall('./Button') or layout_element.findall('./button'):
                    extract_button_info(button, button_layout)
                    
                # Method 2: Key elements (common in some formats)
                for button in layout_element.findall('./Key') or layout_element.findall('./key'):
                    extract_button_info(button, button_layout)
                    
                # Method 3: Direct child elements as buttons (fallback)
                if not button_layout:
                    for button in layout_element:
                        if button.tag not in ['Button', 'button', 'Key', 'key']:
                            extract_button_info(button, button_layout)
                
                if button_layout:
                    break
        
        # Extract configuration data with enhanced structure
        config = {}
        config_elements = [
            'RCCorrection', 'CreateDelta', 'DecodeDelta', 'DoubleSignals', 
            'KeyboardSignals', 'XMP1Signals', 'Config', 'Settings', 'Timing',
            'config', 'settings', 'parameters', 'Parameters', 'options', 'Options',
            'preferences', 'Preferences', 'timing'
        ]
        
        for config_elem in config_elements:
            elem = device.find(config_elem)
            if elem is not None:
                # Try to extract structured data from config elements
                config[config_elem] = {}
                for child in elem:
                    if child.tag:
                        # Process text content if available
                        if child.text and child.text.strip():
                            config[config_elem][child.tag] = child.text.strip()
                        # Process attributes
                        elif child.attrib:
                            config[config_elem][child.tag] = child.attrib
                        # Process nested elements
                        elif len(list(child)) > 0:
                            config[config_elem][child.tag] = {subchild.tag: subchild.text for subchild in child if subchild.tag and subchild.text}
                
                # If no structured data, store the XML string
                if not config[config_elem]:
                    config[config_elem] = ET.tostring(elem, encoding='unicode')
        
        # Process all signals/commands with enhanced detection
        signals = []
        
        # Define all possible signal container paths
        signal_container_paths = [
            './/IRPacket', './/Signal', './/Command', './/IRCommand', './/IRSignal',
            './/code', './/Code', './/function', './/Function', './/Button', './/Key',
            './Signals/*', './Commands/*', './signals/*', './commands/*', './codes/*',
            './functions/*', './Codes/*', './Functions/*', './Buttons/*', './Keys/*'
        ]
        
        # Find all signal elements across different XML structures
        all_signals = []
        for path in signal_container_paths:
            try:
                if path.endswith('/*'):
                    container = device.find(path[:-2])
                    if container is not None:
                        all_signals.extend(list(container))
                else:
                    found = device.findall(path)
                    if found:
                        all_signals.extend(found)
            except Exception as e:
                logger.warning(f"Error finding signals with path {path}: {e}")
        
        # Process each signal
        for signal in all_signals:
            # Skip if this is a container element that we've already processed its children
            if signal.tag in ['Signals', 'Commands', 'signals', 'commands', 'Codes', 'codes',
                             'Functions', 'functions', 'Buttons', 'Keys', 'buttons', 'keys']:
                continue
                
            # Get signal name with extensive fallbacks
            name = extract_element_text(signal, [
                'Name', 'n', 'CommandName', 'Key', 'name', 'commandName', 'key',
                'label', 'Label', 'function', 'Function', 'code', 'Code'
            ])
            
            # Check attributes if no element found
            if not name:
                for name_attr in ['name', 'label', 'id', 'key', 'function', 'code']:
                    if name_attr in signal.attrib:
                        name = signal.attrib[name_attr]
                        break
            
            # Use tag name as fallback if it's likely a command name
            if not name and signal.tag not in ['IRPacket', 'Signal', 'Command', 'IRCommand', 'IRSignal']:
                name = signal.tag
            
            # Get UID with fallbacks
            uid = extract_element_text(signal, ['UID', 'ID', 'Id', 'uid', 'id'])
            
            # Check attributes if no element found
            if not uid:
                for uid_attr in ['uid', 'id', 'code', 'key']:
                    if uid_attr in signal.attrib:
                        uid = signal.attrib[uid_attr]
                        break
            
            # Generate a UUID if none exists
            if not uid:
                uid = str(uuid.uuid4())
            
            # Get signal data with extensive fallbacks
            sig_data = extract_element_text(signal, [
                'SigData', 'Data', 'Code', 'IRCode', 'Pattern', 'Value', 'Raw',
                'sigData', 'data', 'code', 'irCode', 'pattern', 'value', 'raw',
                'pulses', 'Pulses', 'pronto', 'Pronto', 'hex', 'Hex'
            ])
            
            # Check attributes if no element found
            if not sig_data:
                for data_attr in ['data', 'code', 'value', 'pattern', 'pronto', 'hex']:
                    if data_attr in signal.attrib:
                        sig_data = signal.attrib[data_attr]
                        break
            
            # Use signal element's text content if no specific data found
            if not sig_data and signal.text and signal.text.strip():
                sig_data = signal.text.strip()
            
            # Process IR code format if needed
            if sig_data:
                # Clean up common formatting issues
                sig_data = sig_data.strip()
                # Convert comma-separated values to space-separated
                if ',' in sig_data and ' ' not in sig_data:
                    sig_data = sig_data.replace(',', ' ')
                # Remove unnecessary prefixes like "0x" from hex codes
                sig_data = re.sub(r'(^|\s)0x', r'\1', sig_data)
                # Strip whitespace and other common characters
                sig_data = sig_data.strip('[](){}<>')
            
            # Get modulation frequency with fallbacks
            mod_freq = extract_element_text(signal, [
                'ModulationFreq', 'Frequency', 'Freq', 'CarrierFrequency',
                'modulationFreq', 'frequency', 'freq', 'carrierFrequency', 'carrier'
            ])
            
            # Check attributes if no element found
            if not mod_freq:
                for freq_attr in ['freq', 'frequency', 'modulation', 'carrier']:
                    if freq_attr in signal.attrib:
                        mod_freq = signal.attrib[freq_attr]
                        break
            
            # Set default if still not found
            if not mod_freq:
                mod_freq = "38000"  # Most common default
            else:
                # Clean up frequency value
                mod_freq = mod_freq.strip().replace('Hz', '').replace('hz', '').replace('kHz', '000').replace('khz', '000')
                # Handle common case where frequency is given in kHz without units
                if mod_freq.isdigit() and len(mod_freq) <= 2:
                    mod_freq = str(int(mod_freq) * 1000)
            
            # Only add signals with name and data
            if name and sig_data:
                # Extract signal metadata
                signal_metadata = {}
                
                # Process all attributes
                for attr_name, attr_value in signal.attrib.items():
                    if attr_name.lower() not in ['name', 'uid', 'id', 'modulationfreq', 'frequency'] and attr_value:
                        signal_metadata[attr_name] = attr_value
                
                # Look for additional metadata elements
                for meta_field in ['Toggle', 'Repeat', 'RepeatCount', 'Duration', 'BitCount']:
                    value = extract_element_text(signal, [meta_field, meta_field.lower()])
                    if value:
                        signal_metadata[meta_field.lower()] = value
                
                # Extract protocol information
                protocol = extract_element_text(signal, [
                    'Protocol', 'Type', 'Format', 'protocol', 'type', 'format'
                ])
                
                # Check attributes if no element found
                if not protocol:
                    for proto_attr in ['protocol', 'type', 'format']:
                        if proto_attr in signal.attrib:
                            protocol = signal.attrib[proto_attr]
                            break
                
                # If a button has visual coordinates, include them
                visual_info = {}
                for coord in ['x', 'y', 'X', 'Y', 'width', 'height', 'Width', 'Height']:
                    if coord.lower() in signal.attrib:
                        visual_info[coord.lower()] = signal.attrib[coord.lower()]
                
                if visual_info:
                    signal_metadata['visual'] = visual_info
                
                # Add to signals list
                signals.append({
                    'name': name,
                    'uid': uid,
                    'modulation_freq': mod_freq,
                    'sig_data': sig_data,
                    'protocol': protocol,
                    'metadata': signal_metadata
                })
        
        # Sort signals alphabetically by name for better organization
        signals.sort(key=lambda x: x['name'])
        
        # Compile all information into a complete remote definition
        remote_info = {
            'name': remote_name,
            'manufacturer': manufacturer,
            'device_model_number': device_model,
            'remote_model_number': remote_model,
            'device_type': device_type,
            'decoder_class': decoder_class,
            'image_path': image_path,
            'image_data': image_data,
            'metadata': metadata,
            'button_layout': button_layout,
            'config_data': config,
            'signals': signals,
            'signal_count': len(signals)
        }
        
        remotes.append(remote_info)
    
    return remotes

def extract_element_text(element, field_names):
    """Helper function to extract text from various possible element names"""
    for field in field_names:
        # Try direct child element
        elem = element.find(field)
        if elem is not None and elem.text:
            return elem.text.strip()
        
        # Try deeper path with dot notation
        if '.' in field:
            try:
                elem = element.find(field)
                if elem is not None and elem.text:
                    return elem.text.strip()
            except:
                pass
    return None

def extract_button_info(button, button_layout):
    """Extract button information from a button element"""
    # Get button ID from various possible attributes
    button_id = None
    for id_attr in ['id', 'name', 'key', 'code', 'label']:
        if id_attr in button.attrib:
            button_id = button.attrib[id_attr]
            break
    
    # If no ID in attributes, try child elements
    if not button_id:
        id_elem = button.find('id') or button.find('name') or button.find('key')
        if id_elem is not None and id_elem.text:
            button_id = id_elem.text
    
    # If still no ID, use tag if it's not a generic button tag
    if not button_id and button.tag not in ['Button', 'button', 'Key', 'key']:
        button_id = button.tag
    
    # Skip if still no ID
    if not button_id:
        return
    
    # Get button coordinates and dimensions
    coords = {}
    for attr in ['x', 'y', 'width', 'height', 'X', 'Y', 'Width', 'Height']:
        if attr in button.attrib:
            coords[attr.lower()] = button.attrib[attr]
    
    # Get label from attribute or element content
    label = button.get('label')
    if not label:
        label_elem = button.find('label') or button.find('text')
        if label_elem is not None and label_elem.text:
            label = label_elem.text
        elif button.text and button.text.strip():
            label = button.text.strip()
    
    # Get any additional visual attributes
    visual_attrs = {}
    for attr in ['shape', 'color', 'bgcolor', 'textColor', 'fontSize', 'fontFamily']:
        if attr in button.attrib:
            visual_attrs[attr] = button.attrib[attr]
    
    # Store button info
    button_layout[button_id] = {
        **coords,
        'label': label,
        **visual_attrs
    }

def import_remotes_to_db(remotes, user_id=None):
    """Import the remotes into the database with enhanced data handling
    
    This function handles all aspects of importing remote data:
    - Creates/updates remote records
    - Processes images
    - Creates command templates
    - Stores metadata
    """
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
            logger.warning("Skipping remote with no name")
            continue
            
        # Save the remote
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if remote already exists
            cursor.execute("SELECT id FROM remotes WHERE name = %s", (remote['name'],))
            result = cursor.fetchone()
            
            # Prepare config data JSON
            config_json = json.dumps(remote['config_data']) if remote['config_data'] else None
            
            # Create a richer description from available metadata
            description_parts = []
            if remote['manufacturer']:
                description_parts.append(f"Manufacturer: {remote['manufacturer']}")
            if remote['device_type']:
                description_parts.append(f"Type: {remote['device_type']}")
            if remote['device_model_number']:
                description_parts.append(f"Model: {remote['device_model_number']}")
            
            # Add any additional metadata to the description
            if remote['metadata']:
                for key, value in remote['metadata'].items():
                    if key in ['description', 'notes', 'comment'] and value:
                        description_parts.append(f"{key.capitalize()}: {value}")
            
            description = ", ".join(description_parts)
            
            # Process image if available
            image_path = None
            if remote['image_data']:
                try:
                    # Extract image data (could be base64 or raw data)
                    image_data = remote['image_data']
                    
                    # Check if it's a base64 encoded image
                    if ';base64,' in image_data:
                        # Extract the actual base64 data
                        image_data = image_data.split(';base64,')[1]
                    
                    try:
                        # Try to decode base64
                        image_bytes = base64.b64decode(image_data)
                        
                        # Create filename based on remote name
                        safe_name = remote['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                        image_filename = f"{safe_name}_image.png"
                        image_path = f"static/images/remotes/{image_filename}"
                        
                        # Make sure the directory exists
                        os.makedirs("app/static/images/remotes", exist_ok=True)
                        
                        # Write the image file
                        with open(f"app/{image_path}", 'wb') as f:
                            f.write(image_bytes)
                        
                        logger.info(f"Saved remote image to {image_path}")
                    except Exception as e:
                        logger.warning(f"Failed to decode base64 image: {e}")
                except Exception as e:
                    logger.warning(f"Error processing image data: {e}")
            # If image path was provided directly, use that
            elif remote['image_path']:
                image_path = remote['image_path']
            
            if result:
                remote_id = result[0]
                logger.info(f"Remote '{remote['name']}' already exists with ID {remote_id}, updating...")
                # Update the remote with new data
                update_query = """
                    UPDATE remotes SET 
                    manufacturer = %s, 
                    device_model_number = %s, 
                    remote_model_number = %s, 
                    device_type = %s, 
                    decoder_class = %s, 
                    description = %s, 
                    config_data = %s
                """
                params = [
                    remote['manufacturer'],
                    remote['device_model_number'],
                    remote['remote_model_number'],
                    remote['device_type'],
                    remote['decoder_class'],
                    description,
                    config_json
                ]
                
                # Add image path if available
                if image_path:
                    update_query += ", image_path = %s"
                    params.append(image_path)
                
                # Add WHERE clause
                update_query += " WHERE id = %s"
                params.append(remote_id)
                
                cursor.execute(update_query, tuple(params))
            else:
                # Create the remote
                insert_query = """
                    INSERT INTO remotes (
                        name, manufacturer, device_model_number, remote_model_number, 
                        device_type, decoder_class, description, config_data
                """
                params = [
                    remote['name'], 
                    remote['manufacturer'],
                    remote['device_model_number'],
                    remote['remote_model_number'],
                    remote['device_type'],
                    remote['decoder_class'],
                    description,
                    config_json
                ]
                
                # Add image path if available
                if image_path:
                    insert_query += ", image_path"
                    params.append(image_path)
                
                # Close the columns part
                insert_query += ") VALUES (" + ", ".join(["%s"] * len(params)) + ")"
                
                cursor.execute(insert_query, tuple(params))
                remote_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created new remote '{remote['name']}' with ID {remote_id}")
                imported_count += 1
            
            # Store the button layout as part of the config data if available
            if remote['button_layout']:
                button_layout_json = json.dumps(remote['button_layout'])
                try:
                    cursor.execute(
                        "UPDATE remotes SET config_data = JSON_SET(COALESCE(config_data, '{}'), '$.button_layout', CAST(%s AS JSON)) WHERE id = %s",
                        (button_layout_json, remote_id)
                    )
                    conn.commit()
                    logger.info(f"Stored button layout for remote '{remote['name']}'")
                except Exception as e:
                    logger.warning(f"Failed to store button layout: {e}")
            
            # Create a structure to hold the remote data including signals
            # Use XML format for compatibility and future parsing
            remote_xml = ET.Element("AVDevice")
            
            # Add basic remote info
            for key, value in {
                'Name': remote['name'],
                'Manufacturer': remote['manufacturer'],
                'DeviceType': remote['device_type'],
                'DecoderClass': remote['decoder_class'],
                'DeviceModelNumber': remote['device_model_number'],
                'RemoteModelNumber': remote['remote_model_number']
            }.items():
                if value:
                    elem = ET.SubElement(remote_xml, key)
                    elem.text = value
            
            # Add metadata elements
            if remote['metadata']:
                metadata_elem = ET.SubElement(remote_xml, "Metadata")
                for key, value in remote['metadata'].items():
                    if value:
                        meta_elem = ET.SubElement(metadata_elem, key.capitalize())
                        meta_elem.text = str(value)
            
            # Add signals
            signals_elem = ET.SubElement(remote_xml, "Signals")
            for signal in remote['signals']:
                sig_elem = ET.SubElement(signals_elem, "Signal")
                
                # Add basic signal info
                name_elem = ET.SubElement(sig_elem, "Name")
                name_elem.text = signal['name']
                
                uid_elem = ET.SubElement(sig_elem, "UID")
                uid_elem.text = signal['uid']
                
                data_elem = ET.SubElement(sig_elem, "Data")
                data_elem.text = signal['sig_data']
                
                freq_elem = ET.SubElement(sig_elem, "ModulationFreq")
                freq_elem.text = signal['modulation_freq']
                
                if signal['protocol']:
                    protocol_elem = ET.SubElement(sig_elem, "Protocol")
                    protocol_elem.text = signal['protocol']
                
                # Add signal metadata if available
                if signal['metadata']:
                    meta_elem = ET.SubElement(sig_elem, "Metadata")
                    for key, value in signal['metadata'].items():
                        if value:
                            item_elem = ET.SubElement(meta_elem, key.capitalize())
                            item_elem.text = str(value)
            
            # Create a filename based on the remote name
            safe_name = remote['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_name}.xml"
            filepath = f"static/remote_files/{filename}"
            
            # Make sure the directory exists
            os.makedirs("app/static/remote_files", exist_ok=True)
            
            # Create the XML file with proper formatting
            tree = ET.ElementTree(remote_xml)
            
            # Use proper XML formatting with indentation
            ET.indent(tree, space="  ")
            
            # Write the XML to a file
            tree.write(f"app/{filepath}", encoding="utf-8", xml_declaration=True)
            
            # Add the remote file to the database
            cursor.execute("SELECT id FROM remote_files WHERE filename = %s", (filename,))
            result = cursor.fetchone()
            
            if result:
                file_id = result[0]
                logger.info(f"Remote file '{filename}' already exists with ID {file_id}")
            else:
                cursor.execute(
                    "INSERT INTO remote_files (name, filename, filepath, device_type, manufacturer, uploaded_by) VALUES (%s, %s, %s, %s, %s, %s)",
                    (remote['name'], filename, filepath, remote['device_type'], remote['manufacturer'], user_id)
                )
                file_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created new remote file '{filename}' with ID {file_id}")
            
            # Create command templates from the signals
            for signal in remote['signals']:
                if not signal['name']:
                    continue
                
                # Create enhanced template data with all available information
                template_data = {
                    'remote_id': remote_id,
                    'command': signal['name'],
                    'signal_data': signal['sig_data'],
                    'uid': signal['uid'],
                    'modulation_freq': signal['modulation_freq']
                }
                
                # Add protocol if available
                if signal['protocol']:
                    template_data['protocol'] = signal['protocol']
                
                # Add metadata if available
                if signal['metadata']:
                    template_data['metadata'] = signal['metadata']
                
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
                    logger.debug(f"Updated command template '{signal['name']}' for remote '{remote['name']}'")
                else:
                    # Create new template
                    cursor.execute(
                        """INSERT INTO command_templates 
                           (file_id, name, device_type, template_data, created_by) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (file_id, signal['name'], remote['device_type'], json.dumps(template_data), user_id)
                    )
                    logger.debug(f"Created command template '{signal['name']}' for remote '{remote['name']}'")
                
                conn.commit()
            
            logger.info(f"Successfully imported remote '{remote['name']}' with {len(remote['signals'])} signals")
                
    return imported_count

def import_remotes_from_xml(xml_path, user_id):
    """Import remotes from an XML file
    
    This function is used for command-line or script-based imports.
    It handles initializing the database if needed.
    
    Args:
        xml_path: Path to the XML file to import
        user_id: User ID to associate with the import
        
    Returns:
        Number of imported remotes
    """
    # Initialize database
    db.init_db()
    
    logger.info(f"Importing remotes from XML file: {xml_path}")
    
    # Check if file exists
    if not os.path.exists(xml_path):
        logger.error(f"XML file not found: {xml_path}")
        return 0
    
    try:
        # Parse the XML file
        remotes = parse_remotes_xml(xml_path)
        logger.info(f"Found {len(remotes)} remotes in XML file")
        
        if not remotes:
            logger.warning(f"No remotes found in XML file: {xml_path}")
            return 0
        
        # Import the remotes to the database
        imported = import_remotes_to_db(remotes, user_id)
        
        logger.info(f"Successfully imported {imported} remotes from {xml_path}")
        return imported
        
    except Exception as e:
        logger.error(f"Error importing remotes from XML: {str(e)}")
        return 0


