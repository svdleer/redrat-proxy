#!/usr/bin/env python3

import sys
sys.path.append('/app')

from app.services.irnetbox_lib_new import IRSignalParser

try:
    # Parse the XML file
    devices = IRSignalParser.parse_xml_file('test_remote.xml')
    print(f'Parsed {len(devices)} devices from XML')
        
    # Try to convert to remotes format
    remotes = []
    for device in devices:
        remote_data = {
            'name': device.name,
            'manufacturer': device.manufacturer,
            'device_model': device.device_model,
            'remote_model': device.remote_model,
            'device_type': device.device_type,
            'config_data': '',
            'signals': []
        }
        print(f'Remote data keys: {list(remote_data.keys())}')
        remotes.append(remote_data)
        break  # Just test the first one
        
    print('✅ Remote creation successful')
    print(f'Sample remote: {remotes[0]}')
    
    # Now test the database import
    print('\n🔧 Testing database import...')
    from app.services.remote_service import import_remotes_to_db
    
    # This should cause the error
    result = import_remotes_to_db(remotes, 1)
    print(f'✅ Database import successful: {result}')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()