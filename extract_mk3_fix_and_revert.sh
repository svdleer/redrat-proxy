#!/bin/bash

# Extract MK3 Protocol Fix and Revert Repository
# This script safely extracts the MK3 fix and reverts to a clean state

echo "RedRat MK3 Fix Extraction and Repository Reset"
echo "============================================="
echo ""

# Step 1: Create backup of current MK3 fix
echo "Step 1: Backing up MK3 protocol fix..."
cp app/services/redratlib.py mk3_protocol_fix_redratlib.py
echo "✓ MK3 fix backed up to: mk3_protocol_fix_redratlib.py"
echo ""

# Step 2: Show what we're reverting
echo "Step 2: Current commit status..."
git log --oneline -5
echo ""

# Step 3: Ask for confirmation
read -p "Which commit do you want to revert to? (enter commit hash, e.g., 'fed2bbb'): " target_commit

if [ -z "$target_commit" ]; then
    echo "No commit specified. Aborting."
    exit 1
fi

echo ""
echo "You're about to:"
echo "  - Revert to commit: $target_commit"
echo "  - Lose all changes after that commit"
echo "  - Keep the MK3 fix in: mk3_protocol_fix_redratlib.py"
echo ""

read -p "Are you sure? (y/N): " confirm

if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Step 4: Revert to target commit
echo ""
echo "Step 3: Reverting to commit $target_commit..."
git reset --hard $target_commit

if [ $? -eq 0 ]; then
    echo "✓ Successfully reverted to commit $target_commit"
else
    echo "✗ Failed to revert. Check git status."
    exit 1
fi

# Step 5: Apply the MK3 fix
echo ""
echo "Step 4: Applying MK3 protocol fix to clean codebase..."
cp mk3_protocol_fix_redratlib.py app/services/redratlib.py
echo "✓ MK3 fix applied to app/services/redratlib.py"

# Step 6: Show the changes
echo ""
echo "Step 5: Verifying MK3 fix is applied..."
if grep -q "OUTPUT_IR_SYNC = 0x08" app/services/redratlib.py; then
    echo "✓ MK3 fix detected: OUTPUT_IR_SYNC message type found"
else
    echo "⚠ MK3 fix may not be applied correctly"
fi

if grep -q "Using MK3/MK4/RRX protocol" app/services/redratlib.py; then
    echo "✓ MK3 fix detected: Protocol selection logic found"
else
    echo "⚠ Protocol selection logic may not be applied correctly"  
fi

# Step 7: Clean up and prepare for commit
echo ""
echo "Step 6: Preparing for commit..."
git add app/services/redratlib.py

echo ""
echo "Repository reset completed!"
echo ""
echo "Next steps:"
echo "1. Test the MK3 fix: python3 -c \"from app.services.redratlib import MessageTypes; print('OUTPUT_IR_SYNC:', MessageTypes.OUTPUT_IR_SYNC)\""
echo "2. Commit the fix: git commit -m \"Apply MK3 protocol fix to clean codebase\""  
echo "3. Push if satisfied: git push --force-with-lease"
echo ""
echo "⚠️  Note: This is a destructive operation that rewrites history!"
echo "    Only push with --force-with-lease after verifying everything works."
