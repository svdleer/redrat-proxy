#!/bin/bash
# Script to set up and activate Python virtual environment for RedRat project

echo "Setting up Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created!"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Virtual environment is ready!"
echo "To manually activate the environment, run: source venv/bin/activate"
echo ""
