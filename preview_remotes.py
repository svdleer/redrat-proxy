#!/usr/bin/env python3

# Local script to preview the parsed XML without importing to database
# This is useful for testing the XML parsing without affecting the database

import sys
import os
import xml.etree.ElementTree as ET
import json

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

def main():
    """Main function to preview XML parsing"""
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    else:
        xml_path = "remotes.xml"
    
    print(f"Parsing remotes from {xml_path}")
    
    # Parse the XML file
    remotes = parse_remotes_xml(xml_path)
    print(f"Found {len(remotes)} remotes in XML file")
    
    # Print summary of each remote
    for i, remote in enumerate(remotes):
        print(f"\nRemote #{i+1}: {remote['name']}")
        print(f"  Manufacturer: {remote['manufacturer']}")
        print(f"  Device Model: {remote['device_model_number']}")
        print(f"  Remote Model: {remote['remote_model_number']}")
        print(f"  Device Type: {remote['device_type']}")
        print(f"  Decoder Class: {remote['decoder_class']}")
        print(f"  Commands ({len(remote['signals'])}):")
        
        # Group commands into rows of 4 for cleaner output
        row = []
        for signal in remote['signals']:
            row.append(signal['name'])
            if len(row) == 4:
                print(f"    {', '.join(row)}")
                row = []
        
        if row:
            print(f"    {', '.join(row)}")
    
    # Save the parsed data to a JSON file for inspection
    output_file = "parsed_remotes.json"
    with open(output_file, 'w') as f:
        json.dump(remotes, f, indent=2)
    
    print(f"\nParsed data saved to {output_file} for detailed inspection")

if __name__ == "__main__":
    main()
