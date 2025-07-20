#!/bin/bash

echo "================================================"
echo "Debug IR Format for MK3 Protocol - Understanding Error 51"
echo "================================================"

# Copy the debug script
scp -o StrictHostKeyChecking=no debug_ir_format_mk3.py silvester@access-engineering.nl:/tmp/

# Run the debug script
ssh -o StrictHostKeyChecking=no silvester@access-engineering.nl << 'EOF'
cd /tmp
python3 debug_ir_format_mk3.py
EOF

echo ""
echo "================================================"
echo "Debug complete - analyzing format requirements"
echo "================================================"
