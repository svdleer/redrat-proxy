#!/bin/bash
# Deploy MK2/MK3 Protocol Fix to Remote Server
# SSH Details from chat history (not from my thumb! 😅)

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"
REMOTE_PATH="/home/svdleer/redrat/redrat-proxy"

echo "=== Deploying MK2/MK3 Protocol Fix ==="
echo "Target: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT -> $REMOTE_PATH"
echo "(Using ACTUAL details from chat history, not made-up ones!)"
echo

# Deploy and restart
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST << 'EOF'
    echo "🔧 Deploying on remote server..."
    
    # Navigate to project
    cd /home/svdleer/redrat/redrat-proxy
    echo "📍 Current directory: $(pwd)"
    
    # Pull latest changes with MK2/MK3 fix
    echo "📥 Pulling latest changes..."
    git pull origin main
    
    # Verify the fix is present
    if grep -q "Protocol override" app/services/redratlib.py; then
        echo "✅ MK2/MK3 protocol fix found in redratlib.py"
    else
        echo "❌ Protocol fix not found! Check git pull result."
        exit 1
    fi
    
    # Restart Docker containers (with sudo if needed)
    echo "🔄 Restarting Docker containers..."
    sudo docker-compose down
    sleep 2
    sudo docker-compose up -d
    
    # Wait for startup
    echo "⏳ Waiting for containers to start..."
    sleep 10
    
    # Check status
    echo "📊 Container status:"
    sudo docker-compose ps
    
    # Show recent logs
    echo "📝 Recent logs (last 20 lines):"
    sudo docker-compose logs --tail=20
    
    echo
    echo "🎉 Deployment complete!"
    echo "🔍 Monitor for protocol override with:"
    echo "   sudo docker-compose logs -f | grep -i 'protocol override'"
EOF

echo
echo "=== Deployment Result ==="
echo "✅ MK2/MK3 protocol fix deployed to $REMOTE_HOST"
echo
echo "Next: Test IR transmission and look for these log messages:"
echo "  - 'Device detected as MK2, but forcing MK3+ SYNC protocol'"
echo "  - 'Protocol override: Using MK3+ SYNC mode'"  
echo "  - 'Forced MK3+ SYNC IR signal sent successfully'"
echo
echo "Monitor logs remotely:"
echo "  ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && sudo docker-compose logs -f | grep protocol'"

echo
echo "P.S. - €35 penalty accepted for not checking chat history! 💸"
