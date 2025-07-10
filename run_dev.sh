#!/bin/bash
# Simple script to run RedRat locally for development

echo "Starting RedRat application..."
# Use the top-level app.py instead of app.app module directly
# This ensures correct imports
python app.py
