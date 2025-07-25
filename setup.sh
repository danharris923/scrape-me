#!/bin/bash

# Setup script for the Affiliate Scraper on Ubuntu 22.04 GCP VM
# This script installs all dependencies and configures the environment

set -e  # Exit on any error

echo "🚀 Starting Affiliate Scraper Setup on GCP VM..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python 3.10+ and pip..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install system dependencies for Playwright
echo "🌐 Installing system dependencies..."
sudo apt install -y \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    wget \
    curl \
    unzip

# Install Google Cloud SDK (if not already installed)
echo "☁️ Installing Google Cloud SDK..."
if ! command -v gcloud &> /dev/null; then
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    sudo apt update && sudo apt install -y google-cloud-cli
else
    echo "Google Cloud SDK already installed"
fi

# Create project directory
echo "📁 Setting up project directory..."
PROJECT_DIR="/home/ubuntu/scraper"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, installing core dependencies..."
    pip install \
        pydantic-ai==0.0.14 \
        playwright==1.48.0 \
        pydantic==2.10.3 \
        pydantic-settings==2.6.1 \
        google-cloud-storage==2.18.0 \
        httpx==0.27.2 \
        python-dotenv==1.0.1 \
        pytest==8.3.4 \
        pytest-asyncio==0.24.0 \
        Pillow==10.4.0 \
        loguru==0.7.2
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

# Create necessary directories
echo "📂 Creating application directories..."
mkdir -p output state config/sites

# Set up environment file template
echo "⚙️ Creating environment file template..."
cat > .env.example << 'EOF'
# LLM Configuration
SCRAPER_LLM_PROVIDER=anthropic
SCRAPER_LLM_MODEL=claude-3-5-sonnet-latest
SCRAPER_LLM_API_KEY=your_api_key_here

# Google Cloud Storage
SCRAPER_GCS_CREDENTIALS_PATH=/home/ubuntu/scraper/credentials/gcs-service-account.json
SCRAPER_GCS_BUCKET_NAME=your-bucket-name

# Scraping Configuration
SCRAPER_SCRAPING_DELAY_SECONDS=2.0
SCRAPER_MAX_RETRIES=3
SCRAPER_QUALITY_THRESHOLD=0.7
SCRAPER_BROWSER_HEADLESS=false

# Directories
SCRAPER_OUTPUT_DIRECTORY=./output
SCRAPER_STATE_DIRECTORY=./state
SCRAPER_CONFIG_DIRECTORY=./config/sites

# Logging
SCRAPER_LOG_LEVEL=INFO
SCRAPER_LOG_FILE=./scraper.log
EOF

# Create credentials directory
echo "🔐 Creating credentials directory..."
mkdir -p credentials
chmod 700 credentials

# Set up systemd service for cron-like scheduling
echo "⏰ Setting up systemd service..."
sudo tee /etc/systemd/system/affiliate-scraper.service > /dev/null << 'EOF'
[Unit]
Description=Affiliate Scraper Service
After=network.target

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/scraper
Environment=PATH=/home/ubuntu/scraper/venv/bin
ExecStart=/home/ubuntu/scraper/venv/bin/python main.py --all-sites
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set up systemd timer for daily execution
sudo tee /etc/systemd/system/affiliate-scraper.timer > /dev/null << 'EOF'
[Unit]
Description=Run Affiliate Scraper Daily
Requires=affiliate-scraper.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable the timer
sudo systemctl daemon-reload
sudo systemctl enable affiliate-scraper.timer

# Set proper permissions
echo "🔒 Setting file permissions..."
chown -R ubuntu:ubuntu /home/ubuntu/scraper
chmod +x /home/ubuntu/scraper/main.py

# Test installation
echo "🧪 Testing installation..."
source venv/bin/activate

echo "Testing Python imports..."
python3 -c "
import pydantic_ai
import playwright
import google.cloud.storage
import httpx
print('✅ All imports successful')
"

echo "Testing Playwright browser..."
python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await browser.close()
        print('✅ Playwright browser test successful')

asyncio.run(test())
"

# Set up API server service
echo "🌐 Setting up API server service..."
sudo tee /etc/systemd/system/affiliate-scraper-api.service > /dev/null << 'EOF'
[Unit]
Description=Affiliate Scraper API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/scrape-me
Environment="PATH=/home/ubuntu/scrape-me/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/scrape-me/venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy your code files to /home/ubuntu/scraper/"
echo "2. Copy your GCS service account JSON to /home/ubuntu/scraper/credentials/"
echo "3. Copy .env.example to .env and configure your API keys"
echo "4. Add your site configurations to /home/ubuntu/scraper/config/sites/"
echo "5. Test the scraper: python main.py --status"
echo "6. Start the daily timer: sudo systemctl start affiliate-scraper.timer"
echo "7. Start API server: sudo systemctl enable affiliate-scraper-api && sudo systemctl start affiliate-scraper-api"
echo ""
echo "🔧 Configuration files:"
echo "  - Environment: /home/ubuntu/scraper/.env"
echo "  - Site configs: /home/ubuntu/scraper/config/sites/"
echo "  - Credentials: /home/ubuntu/scraper/credentials/"
echo ""
echo "🌐 API Server endpoints:"
echo "  - http://YOUR_VM_IP:8000/products - Get all products"
echo "  - http://YOUR_VM_IP:8000/products/outdoor-gear-site - Get specific site"
echo "  - http://YOUR_VM_IP:8000/sites - List all sites"
echo ""
echo "🔍 Monitor logs:"
echo "  - Scraper: journalctl -u affiliate-scraper.service -f"
echo "  - API: journalctl -u affiliate-scraper-api.service -f"
echo "📊 Check timer status: systemctl status affiliate-scraper.timer"