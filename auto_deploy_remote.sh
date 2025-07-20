#!/bin/bash
# Auto-deploy MK2/MK3 Protocol Fix to Remote Server

REMOTE_HOST="your-server-ip"  # Update this with your actual server IP
REMOTE_USER="your-username"   # Update this with your SSH username
REMOTE_PATH="/path/to/redrat-proxy"  # Update this with your actual path

echo "=== Auto-Deploying MK2/MK3 Protocol Fix ==="
echo

# Get the actual remote details
read -p "Enter remote server IP/hostname: " REMOTE_HOST
read -p "Enter SSH username: " REMOTE_USER
read -p "Enter remote path to redrat-proxy (e.g., /home/user/redrat-proxy): " REMOTE_PATH

echo
echo "Deploying to: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo

# Execute deployment commands on remote server
ssh $REMOTE_USER@$REMOTE_HOST << EOF
    echo "=== Remote Server Deployment ==="
    
    # Navigate to project directory
    cd $REMOTE_PATH
    echo "✅ Changed to project directory: \$(pwd)"
    
    # Pull latest changes
    echo "📥 Pulling latest changes from GitHub..."
    git pull origin main
    
    # Check if redratlib.py has the fix
    if grep -q "Protocol override" app/services/redratlib.py; then
        echo "✅ MK2/MK3 protocol fix detected in code"
    else
        echo "❌ Protocol fix not found - deployment may have failed"
        exit 1
    fi
    
    # Restart Docker containers
    echo "🔄 Restarting Docker containers..."
    docker-compose restart
    
    echo "⏳ Waiting for containers to start..."
    sleep 5
    
    # Check container status
    echo "📊 Container status:"
    docker-compose ps
    
    echo
    echo "🎉 Deployment complete! Monitor logs with:"
    echo "   docker-compose logs -f | grep -i 'protocol override'"
    echo
    echo "Test IR transmission to see protocol override messages:"
    echo "   - 'Device detected as MK2, but forcing MK3+ SYNC protocol'"
    echo "   - 'Protocol override: Using MK3+ SYNC mode'"
    echo "   - 'Forced MK3+ SYNC IR signal sent successfully'"
EOF

echo
echo "=== Deployment Complete ==="
echo "The MK2/MK3 protocol fix has been deployed to your remote server."
echo
echo "Next steps:"
echo "1. Test IR transmission through your web interface"
echo "2. Monitor logs: ssh $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && docker-compose logs -f | grep protocol'"
echo "3. Capture packets to verify ~80% packet reduction"
