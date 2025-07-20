#!/bin/bash

echo "================================================"
echo "Testing Native MK4 Protocol (Not Forced MK3)"
echo "================================================"

# Copy the corrected library with native MK4 support
echo "Copying library with native MK4 protocol..."
scp -P 65001 -o StrictHostKeyChecking=no app/services/redratlib.py svdleer@access-engineering.nl:/tmp/redratlib_mk4_native.py

# Copy test script
scp -P 65001 -o StrictHostKeyChecking=no mk4_native_test.py svdleer@access-engineering.nl:/tmp/

# Run the test
echo "Running native MK4 protocol test..."
ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'
cd /tmp
python3 mk4_native_test.py
EOF

echo ""
echo "Native MK4 protocol test complete! 🔍"
