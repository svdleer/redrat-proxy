#!/usr/bin/env python3

"""Test script for HUMAX POWER command using the web application service."""

import sys
import os
sys.path.append('/home/svdleer/redrat-proxy')

# Import the RedRat service
from app.services.redrat_service import create_redrat_service

def test_humax_power_via_service():
    """Test HUMAX POWER command via the RedRat service using database templates."""
    
    redrat_host = "172.16.6.62"  # RedRat device IP from database
    remote_id = 12               # HUMAX remote ID
    command_name = "POWER"       # POWER command
    ir_port = 9                  # HUMAX on port 9
    power = 50                   # Power level
    
    print(f"🎯 Testing HUMAX POWER via RedRat service")
    print(f"Remote ID: {remote_id} (HUMAX)")
    print(f"Command: {command_name}")
    print(f"Target: {redrat_host}, Port: {ir_port}, Power: {power}")
    
    try:
        service = create_redrat_service(redrat_host, 10001)
        
        # Send the command using the service (this will use database templates)
        result = service.send_command(
            command_id=999,           # Dummy command ID
            remote_id=remote_id,      # HUMAX remote
            command_name=command_name, # POWER command
            ir_port=ir_port,          # Port 9
            power=power               # Power level 50
        )
        
        if result['success']:
            print(f"🎉 HUMAX POWER sent successfully!")
            print(f"Message: {result['message']}")
            if 'executed_at' in result:
                print(f"Executed at: {result['executed_at']}")
        else:
            print(f"❌ Failed to send HUMAX POWER: {result['message']}")
            if 'error_details' in result:
                print(f"Error details: {result['error_details']}")
            
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_humax_power_via_service()