#!/bin/bash
# Test RedRat Proxy Docker Container
# Run this on the remote server to test your Docker RedRat proxy

set -e

DOCKER_CONTAINER="redrat-proxy"  # Adjust container name as needed
REDRAT_HOST="localhost"
REDRAT_PORT="5000"

echo "🐳 RedRat Proxy Docker Test Script"
echo "=================================="

# Check Docker status
echo "📋 Checking Docker container status..."
if ! sudo docker ps | grep -q "$DOCKER_CONTAINER"; then
    echo "❌ RedRat Proxy container not running"
    echo "Available containers:"
    sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Try to find any redrat-related containers
    echo
    echo "Searching for RedRat-related containers..."
    sudo docker ps -a | grep -i redrat || echo "No RedRat containers found"
    
    exit 1
fi

echo "✅ Container '$DOCKER_CONTAINER' is running"

# Test API connectivity
echo
echo "🌐 Testing API connectivity..."
if curl -s "http://$REDRAT_HOST:$REDRAT_PORT/api/health" > /dev/null 2>&1; then
    echo "✅ API is accessible at http://$REDRAT_HOST:$REDRAT_PORT"
else
    echo "⚠️  API health check failed, trying main endpoint..."
    if curl -s "http://$REDRAT_HOST:$REDRAT_PORT/" > /dev/null 2>&1; then
        echo "✅ Main endpoint accessible"
    else
        echo "❌ API not accessible - check port mapping and container status"
        echo "Container details:"
        sudo docker inspect "$DOCKER_CONTAINER" | jq '.[0].NetworkSettings.Ports' 2>/dev/null || echo "No port mapping info available"
        exit 1
    fi
fi

# Function to test a specific IR command
test_ir_command() {
    local remote_id=$1
    local command_name=$2
    local ir_port=${3:-1}
    local power=${4:-50}
    
    echo
    echo "🎯 Testing IR command: $command_name (Remote: $remote_id, Port: $ir_port, Power: $power)"
    
    # Login first (if authentication required)
    echo "🔐 Authenticating..."
    login_response=$(curl -s -c /tmp/cookies.txt -X POST "http://$REDRAT_HOST:$REDRAT_PORT/api/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin"}' 2>/dev/null)
    
    if echo "$login_response" | grep -q '"success":true'; then
        echo "✅ Authentication successful"
    else
        echo "⚠️  Authentication failed, trying without auth..."
    fi
    
    # Send IR command
    echo "📡 Sending IR command..."
    command_payload=$(cat <<EOF
{
    "remote_id": $remote_id,
    "command": "$command_name",
    "redrat_device_id": 1,
    "ir_port": $ir_port,
    "power": $power
}
EOF
)
    
    echo "Payload: $command_payload"
    
    command_response=$(curl -s -b /tmp/cookies.txt -X POST "http://$REDRAT_HOST:$REDRAT_PORT/api/commands" \
        -H "Content-Type: application/json" \
        -d "$command_payload" 2>/dev/null)
    
    echo "Response: $command_response"
    
    if echo "$command_response" | grep -q '"success":true'; then
        echo "✅ IR command sent successfully"
        
        # Extract command ID for status checking
        command_id=$(echo "$command_response" | grep -o '"id":[0-9]*' | cut -d: -f2)
        if [[ -n "$command_id" ]]; then
            echo "📋 Command ID: $command_id"
            
            # Check command status
            sleep 2
            status_response=$(curl -s -b /tmp/cookies.txt "http://$REDRAT_HOST:$REDRAT_PORT/api/commands/$command_id" 2>/dev/null)
            echo "Status: $status_response"
        fi
    else
        echo "❌ IR command failed"
        echo "Response: $command_response"
    fi
}

# Function to list available remotes and commands
list_available_commands() {
    echo
    echo "📋 Listing available remotes and commands..."
    
    # Get remotes
    remotes_response=$(curl -s -b /tmp/cookies.txt "http://$REDRAT_HOST:$REDRAT_PORT/api/remotes" 2>/dev/null)
    
    if echo "$remotes_response" | grep -q "remotes"; then
        echo "Available remotes:"
        echo "$remotes_response" | jq '.remotes[] | {id: .id, name: .name}' 2>/dev/null || echo "$remotes_response"
    else
        echo "⚠️  Could not retrieve remotes list"
        echo "Response: $remotes_response"
    fi
    
    # Get RedRat devices
    echo
    devices_response=$(curl -s -b /tmp/cookies.txt "http://$REDRAT_HOST:$REDRAT_PORT/api/redrat/devices" 2>/dev/null)
    
    if echo "$devices_response" | grep -q "devices"; then
        echo "Available RedRat devices:"
        echo "$devices_response" | jq '.devices[] | {id: .id, name: .name, ip: .ip_address, port: .port}' 2>/dev/null || echo "$devices_response"
    else
        echo "⚠️  Could not retrieve devices list"
        echo "Response: $devices_response"
    fi
}

# Main test flow
main() {
    echo
    echo "🔍 Running comprehensive RedRat proxy test..."
    
    # List available commands
    list_available_commands
    
    echo
    echo "📝 Manual test options:"
    echo "1. Use the list above to identify remote_id and command names"
    echo "2. Run: test_ir_command <remote_id> <command_name> [ir_port] [power]"
    echo
    echo "Example tests you can run:"
    echo "./redrat_docker_test.sh test 1 power_on 1 50"
    echo "./redrat_docker_test.sh test 1 power_off 2 75"
    echo
    
    # Interactive mode
    if [[ "$1" == "test" ]] && [[ -n "$2" ]] && [[ -n "$3" ]]; then
        test_ir_command "$2" "$3" "${4:-1}" "${5:-50}"
    elif [[ "$1" == "interactive" ]]; then
        echo "🎮 Interactive mode"
        read -p "Enter remote ID: " remote_id
        read -p "Enter command name: " command_name
        read -p "Enter IR port (default 1): " ir_port
        read -p "Enter power level (default 50): " power
        
        test_ir_command "${remote_id}" "${command_name}" "${ir_port:-1}" "${power:-50}"
    else
        echo "💡 Usage:"
        echo "$0                           # Show available remotes/commands"
        echo "$0 test <remote_id> <cmd>    # Test specific command"
        echo "$0 interactive               # Interactive test mode"
    fi
    
    # Clean up
    rm -f /tmp/cookies.txt
}

# If script is sourced, don't run main automatically
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

echo
echo "🎯 Ready for signal comparison testing!"
echo "Use this script to generate controlled IR signals for ERSPAN capture."
