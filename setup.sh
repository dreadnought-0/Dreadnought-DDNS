#!/bin/bash

# DreadnoughtDDNS Setup Script
# This script prepares the environment for running DreadnoughtDDNS

echo "🚀 Setting up Dreadnought..."

# Create data directory if it doesn't exist
if [ ! -d "./data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p ./data
fi

# Set proper permissions for the data directory
# UID 1000 matches the appuser in the Docker containers
echo "🔐 Setting permissions on data directory..."
chmod 777 ./data

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your configuration."
    echo "You can copy .env.example if it exists."
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "You can now start DreadnoughtDDNS with:"
echo "  docker compose up -d"
echo ""
echo "Access the dashboard at: http://localhost:8082"
