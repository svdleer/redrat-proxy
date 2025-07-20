#!/bin/bash

echo "================================================"
echo "Testing Multiple IR Data Formats for MK3 Protocol"
echo "================================================"

# Copy the test script to remote host
scp -P 65001 -o StrictHostKeyChecking=no mk3_format_test.py svdleer@access-engineering.nl:/tmp/

# Run the comprehensive format test
echo "Running comprehensive IR format test..."
ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'
cd /tmp
python3 mk3_format_test.py
EOF

echo ""
echo "Format testing complete! 🔍"
