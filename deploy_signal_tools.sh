#!/bin/bash
# Deploy RedRat Signal Comparison Tools to Remote Server
# Run this from your local machine

set -e

# Configuration
REMOTE_SERVER="access-engineering.nl"
SSH_PORT="65001"
SSH_USER="svdleer"
REMOTE_DIR="/tmp/redrat_signal_tools"

echo "🚀 Deploying RedRat Signal Comparison Tools"
echo "Target: $SSH_USER@$REMOTE_SERVER:$SSH_PORT"
echo

# Create remote directory
echo "📁 Creating remote directory..."
ssh -p $SSH_PORT $SSH_USER@$REMOTE_SERVER "mkdir -p $REMOTE_DIR"

# Upload tools
echo "📤 Uploading signal comparison tools..."
scp -P $SSH_PORT signal_comparison.sh $SSH_USER@$REMOTE_SERVER:$REMOTE_DIR/
scp -P $SSH_PORT analyze_redrat_signals.py $SSH_USER@$REMOTE_SERVER:$REMOTE_DIR/

# Make scripts executable
echo "🔧 Setting up permissions..."
ssh -p $SSH_PORT $SSH_USER@$REMOTE_SERVER "chmod +x $REMOTE_DIR/*.sh $REMOTE_DIR/*.py"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
ssh -p $SSH_PORT $SSH_USER@$REMOTE_SERVER "
    python3 -m pip install --user scapy 2>/dev/null || pip3 install --user scapy 2>/dev/null || echo 'Scapy installation may need manual setup'
"

# Display usage instructions
echo
echo "✅ Deployment complete!"
echo
echo "🎯 Next steps on the remote server:"
echo "1. SSH to server: ssh -p $SSH_PORT $SSH_USER@$REMOTE_SERVER"
echo "2. Go to tools directory: cd $REMOTE_DIR"
echo "3. Run signal comparison: ./signal_comparison.sh compare"
echo
echo "📋 Available tools:"
echo "- signal_comparison.sh: Interactive signal capture and comparison"
echo "- analyze_redrat_signals.py: Detailed PCAP analysis"
echo
echo "🔍 Manual analysis example:"
echo "python3 analyze_redrat_signals.py capture1.pcap capture2.pcap --compare"
echo
echo "💡 Tips:"
echo "- Ensure ERSPAN is capturing RedRat device traffic"
echo "- Use same IR command for both proxy and official tool tests"
echo "- Check RedRat device IP and port (usually :10001)"
echo "- Have both RedRat Proxy (Docker) and Official RedRat tool ready"
