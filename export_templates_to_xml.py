#!/usr/bin/env python3
"""
Export database signal templates back to RedRat XML format.
This allows the GUI/tools to work with the complete signal data from the database.
"""

import sys
import json
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
import mysql.connector
from typing import Dict, List, Optional

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'redrat_user',
    'password': 'redrat_password',
    'database': 'redrat_db'
}

class DatabaseToXMLExporter:
    """Export database signal templates to RedRat XML format."""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        
    def connect_db(self):
        """Connect to the database."""
        return mysql.connector.connect(**self.db_config)
    
    def get_remotes_and_templates(self) -> Dict:
        """Get all remotes and their signal templates from the database."""
        with self.connect_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get all remotes
            cursor.execute("SELECT * FROM remotes ORDER BY name")
            remotes = cursor.fetchall()
            
            result = {}
            
            for remote in remotes:
                remote_id = remote['id']
                remote_name = remote['name']
                
                # Get all command templates for this remote
                cursor.execute("""
                    SELECT name, template_data 
                    FROM command_templates 
                    WHERE remote_id = %s 
                    ORDER BY name
                """, (remote_id,))
                
                templates = cursor.fetchall()
                
                if templates:  # Only include remotes that have templates
                    result[remote_name] = {
                        'remote_info': remote,
                        'templates': templates
                    }
            
            return result
    
    def parse_template_data(self, template_data: str) -> Optional[Dict]:
        """Parse the JSON template data."""
        try:
            return json.loads(template_data)
        except Exception as e:
            print(f"Warning: Failed to parse template data: {e}")
            return None
    
    def create_xml_device(self, remote_name: str, remote_info: Dict, templates: List[Dict]) -> ET.Element:
        """Create an AVDevice XML element from database data."""
        
        device = ET.Element('AVDevice')
        
        # Device information
        ET.SubElement(device, 'Name').text = remote_name
        ET.SubElement(device, 'Manufacturer').text = remote_info.get('manufacturer', 'Unknown')
        ET.SubElement(device, 'DeviceModelNumber').text = remote_info.get('device_model', 'Unknown')
        ET.SubElement(device, 'RemoteModelNumber').text = remote_info.get('remote_model', 'Unknown')
        ET.SubElement(device, 'DeviceType').text = remote_info.get('device_type', 'STB')
        
        # IR Packets container
        ir_packets = ET.SubElement(device, 'IRPackets')
        
        # Process templates - group signal1/signal2 variants
        signal_groups = {}
        
        for template in templates:
            template_name = template['name']
            template_data = self.parse_template_data(template['template_data'])
            
            if not template_data:
                continue
            
            # Check if this is a signal variant (ends with _signal1 or _signal2)
            base_name = template_name
            if template_name.endswith('_signal1') or template_name.endswith('_signal2'):
                base_name = template_name.rsplit('_signal', 1)[0]
            
            if base_name not in signal_groups:
                signal_groups[base_name] = {}
            
            signal_groups[base_name][template_name] = template_data
        
        # Create XML elements for each signal group
        for base_name, variants in signal_groups.items():
            if len(variants) == 2 and any('_signal1' in name for name in variants) and any('_signal2' in name for name in variants):
                # Create DoubleSignal
                self.create_double_signal(ir_packets, base_name, variants)
            else:
                # Create regular signal(s)
                for variant_name, template_data in variants.items():
                    self.create_single_signal(ir_packets, variant_name, template_data)
        
        return device
    
    def create_double_signal(self, parent: ET.Element, base_name: str, variants: Dict):
        """Create a DoubleSignal XML element."""
        
        # Find signal1 and signal2 data
        signal1_data = None
        signal2_data = None
        
        for name, data in variants.items():
            if '_signal1' in name:
                signal1_data = data
            elif '_signal2' in name:
                signal2_data = data
        
        if not signal1_data or not signal2_data:
            return
        
        # Create DoubleSignal element
        double_signal = ET.SubElement(parent, 'IRPacket')
        double_signal.set('{http://www.w3.org/2001/XMLSchema-instance}type', 'DoubleSignal')
        
        # Main signal properties
        ET.SubElement(double_signal, 'Name').text = base_name
        ET.SubElement(double_signal, 'UID').text = signal1_data.get('uid', f'{base_name}_uid')
        
        # Create Signal1
        signal1_elem = ET.SubElement(double_signal, 'Signal1')
        self.populate_signal_data(signal1_elem, signal1_data)
        
        # Create Signal2
        signal2_elem = ET.SubElement(double_signal, 'Signal2')
        self.populate_signal_data(signal2_elem, signal2_data)
    
    def create_single_signal(self, parent: ET.Element, signal_name: str, template_data: Dict):
        """Create a single IRPacket XML element."""
        
        signal = ET.SubElement(parent, 'IRPacket')
        
        ET.SubElement(signal, 'Name').text = signal_name
        ET.SubElement(signal, 'UID').text = template_data.get('uid', f'{signal_name}_uid')
        
        self.populate_signal_data(signal, template_data)
    
    def populate_signal_data(self, signal_elem: ET.Element, template_data: Dict):
        """Populate signal element with template data."""
        
        # Core signal properties
        ET.SubElement(signal_elem, 'ModulationFreq').text = str(template_data.get('modulation_freq', 38000))
        ET.SubElement(signal_elem, 'NoRepeats').text = str(template_data.get('no_repeats', 1))
        ET.SubElement(signal_elem, 'IntraSigPause').text = str(template_data.get('intra_sig_pause', 0.0))
        
        # Signal data (hex string to base64)
        signal_data_hex = template_data.get('signal_data', '')
        if signal_data_hex:
            try:
                # Convert hex string to bytes, then to base64
                signal_bytes = bytes.fromhex(signal_data_hex)
                signal_b64 = base64.b64encode(signal_bytes).decode('ascii')
                ET.SubElement(signal_elem, 'SigData').text = signal_b64
            except Exception as e:
                print(f"Warning: Failed to convert signal data: {e}")
                ET.SubElement(signal_elem, 'SigData').text = ""
        
        # Lengths array
        lengths = template_data.get('lengths', [])
        if lengths:
            lengths_elem = ET.SubElement(signal_elem, 'Lengths')
            for length in lengths:
                ET.SubElement(lengths_elem, 'double').text = str(length)
        
        # Toggle data
        toggle_data = template_data.get('toggle_data')
        if toggle_data:
            toggle_elem = ET.SubElement(signal_elem, 'ToggleData')
            for bit_no, (len1, len2) in toggle_data.items():
                toggle_bit = ET.SubElement(toggle_elem, 'ToggleBit')
                ET.SubElement(toggle_bit, 'bitNo').text = str(bit_no)
                ET.SubElement(toggle_bit, 'len1').text = str(len1)
                ET.SubElement(toggle_bit, 'len2').text = str(len2)
    
    def export_to_xml(self, output_file: str = 'exported_remotes.xml'):
        """Export all database templates to XML file."""
        
        print(f"🔄 Exporting database templates to {output_file}...")
        
        # Get data from database
        remotes_data = self.get_remotes_and_templates()
        
        if not remotes_data:
            print("❌ No remotes with templates found in database")
            return False
        
        # Create root XML structure
        root = ET.Element('SignalDatabase')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        
        devices_elem = ET.SubElement(root, 'AVDevices')
        
        # Process each remote
        for remote_name, data in remotes_data.items():
            print(f"  📡 Processing remote: {remote_name} ({len(data['templates'])} templates)")
            
            device_elem = self.create_xml_device(
                remote_name, 
                data['remote_info'], 
                data['templates']
            )
            devices_elem.append(device_elem)
        
        # Write XML file with pretty formatting
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ')
        
        # Remove empty lines
        pretty_lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(pretty_lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"✅ Successfully exported {len(remotes_data)} remotes to {output_file}")
        return True
    
    def export_specific_remote(self, remote_name: str, output_file: str = None):
        """Export a specific remote to XML file."""
        
        if output_file is None:
            output_file = f'{remote_name.lower().replace(" ", "_")}_signals.xml'
        
        print(f"🔄 Exporting remote '{remote_name}' to {output_file}...")
        
        with self.connect_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get specific remote
            cursor.execute("SELECT * FROM remotes WHERE name = %s", (remote_name,))
            remote = cursor.fetchone()
            
            if not remote:
                print(f"❌ Remote '{remote_name}' not found")
                return False
            
            # Get templates for this remote
            cursor.execute("""
                SELECT name, template_data 
                FROM command_templates 
                WHERE remote_id = %s 
                ORDER BY name
            """, (remote['id'],))
            
            templates = cursor.fetchall()
            
            if not templates:
                print(f"❌ No templates found for remote '{remote_name}'")
                return False
        
        # Create XML
        root = ET.Element('SignalDatabase')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        
        devices_elem = ET.SubElement(root, 'AVDevices')
        device_elem = self.create_xml_device(remote_name, remote, templates)
        devices_elem.append(device_elem)
        
        # Write file
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ')
        pretty_lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(pretty_lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"✅ Successfully exported remote '{remote_name}' with {len(templates)} signals to {output_file}")
        return True

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 export_templates_to_xml.py all [output_file]")
        print("  python3 export_templates_to_xml.py remote <remote_name> [output_file]")
        print("")
        print("Examples:")
        print("  python3 export_templates_to_xml.py all exported_remotes.xml")
        print("  python3 export_templates_to_xml.py remote Humax humax_signals.xml")
        return 1
    
    exporter = DatabaseToXMLExporter(DB_CONFIG)
    
    mode = sys.argv[1].lower()
    
    if mode == 'all':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'exported_remotes.xml'
        success = exporter.export_to_xml(output_file)
    elif mode == 'remote':
        if len(sys.argv) < 3:
            print("❌ Remote name required")
            return 1
        remote_name = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        success = exporter.export_specific_remote(remote_name, output_file)
    else:
        print("❌ Unknown mode. Use 'all' or 'remote'")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())