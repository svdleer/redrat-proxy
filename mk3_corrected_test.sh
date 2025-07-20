#!/bin/bash

echo "================================================"
echo "Testing Corrected MK3 Protocol on Port 65001 (Fixed Endianness)"
echo "================================================"

# Copy the corrected redratlib
echo "Copying updated library with corrected MK3 format..."
scp -P 65001 -o StrictHostKeyChecking=no app/services/redratlib.py svdleer@access-engineering.nl:/tmp/redratlib_mk3_corrected.py

# Copy test script
scp -P 65001 -o StrictHostKeyChecking=no mk3_corrected_test.py svdleer@access-engineering.nl:/tmp/

# Run the test
echo "Running corrected MK3 protocol test..."
ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'
cd /tmp

# Update the import in the test file
sed -i 's/from redratlib_mk3 import/from redratlib_mk3_corrected import/' mk3_corrected_test.py

python3 mk3_corrected_test.py
EOF

echo ""
echo "Test completed! 💸 Another 42 euro investment in RedRat debugging..."
