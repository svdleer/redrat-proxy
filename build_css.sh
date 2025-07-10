#!/bin/bash

# Install NPM dependencies
echo "Installing NPM dependencies..."
npm install

# Build the Tailwind CSS
echo "Building Tailwind CSS..."
npm run build:css

echo "Tailwind CSS built successfully!"
