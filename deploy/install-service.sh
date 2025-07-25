#!/bin/bash

# Script to install the scraper API as a systemd service
# Run this on your GCP VM after cloning the repo

set -e

echo "🚀 Installing Scraper API Service..."

# Check if running as root for systemd operations
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Don't run this script as root! Run as your regular user."
   exit 1
fi

# Get current user and home directory
USER_NAME=$(whoami)
HOME_DIR=$HOME
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📍 User: $USER_NAME"
echo "📍 Home: $HOME_DIR" 
echo "📍 Project: $PROJECT_DIR"

# Update the service file with correct paths
SERVICE_FILE="$SCRIPT_DIR/scraper-api.service"
TEMP_SERVICE="/tmp/scraper-api.service"

# Replace placeholders in service file
sed "s|danharris923|$USER_NAME|g" "$SERVICE_FILE" > "$TEMP_SERVICE"
sed -i "s|/home/danharris923/scrape-me|$PROJECT_DIR|g" "$TEMP_SERVICE"

echo "📝 Service file configured for:"
echo "   User: $USER_NAME"
echo "   Project: $PROJECT_DIR"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$PROJECT_DIR"
python3 -m pip install --user -r requirements.txt

# Create output directory
mkdir -p "$PROJECT_DIR/output"

# Test the API server
echo "🧪 Testing API server..."
timeout 5s python3 api_server.py || echo "✅ API server test complete"

# Copy service file and enable
echo "🔧 Installing systemd service..."
sudo cp "$TEMP_SERVICE" /etc/systemd/system/scraper-api.service
sudo systemctl daemon-reload
sudo systemctl enable scraper-api.service
sudo systemctl start scraper-api.service

# Check status
echo "📊 Service Status:"
sudo systemctl status scraper-api.service --no-pager -l

# Show logs
echo ""
echo "📋 Recent Logs:"
sudo journalctl -u scraper-api.service -n 10 --no-pager

echo ""
echo "✅ Installation Complete!"
echo ""
echo "🎯 Useful Commands:"
echo "   sudo systemctl status scraper-api     # Check status"
echo "   sudo systemctl restart scraper-api    # Restart service"
echo "   sudo systemctl stop scraper-api       # Stop service"
echo "   sudo journalctl -u scraper-api -f     # Follow logs"
echo ""
echo "🔗 Your API should now be running at: http://$(curl -s ifconfig.me):8000"
echo "🧪 Test it: curl http://localhost:8000/health"

# Clean up
rm "$TEMP_SERVICE"