# GCP Deployment Guide for Affiliate Scraper

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** installed locally
3. **Project with required APIs enabled:**
   - Compute Engine API
   - Cloud Storage API
   - Cloud Logging API

## Step-by-Step Deployment

### 1. Set up Google Cloud Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable logging.googleapis.com
```

### 2. Create Storage Bucket for Images

```bash
# Create bucket for product images
gsutil mb gs://$PROJECT_ID-scraper-images

# Make bucket publicly readable
gsutil iam ch allUsers:objectViewer gs://$PROJECT_ID-scraper-images

# Set CORS policy for web access
echo '[{"origin":["*"],"method":["GET"],"responseHeader":["Content-Type"],"maxAgeSeconds":3600}]' > cors.json
gsutil cors set cors.json gs://$PROJECT_ID-scraper-images
```

### 3. Create Service Account

```bash
# Create service account for the scraper
gcloud iam service-accounts create scraper-service-account \
    --display-name="Affiliate Scraper Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:scraper-service-account@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create and download service account key
gcloud iam service-accounts keys create scraper-credentials.json \
    --iam-account=scraper-service-account@$PROJECT_ID.iam.gserviceaccount.com
```

### 4. Create VM Instance

```bash
# Make the script executable
chmod +x deploy/gcp-vm-create.sh

# Create VM (replace with your project ID)
./deploy/gcp-vm-create.sh your-project-id
```

### 5. Deploy Scraper System

**Option A: Browser SSH (Recommended)**
1. Go to https://console.cloud.google.com/compute/instances
2. Click "SSH" next to your VM instance
3. This opens a browser-based terminal

**Option B: Local SSH**
```bash
gcloud compute ssh affiliate-scraper --zone=us-central1-b --project=$PROJECT_ID
```

**In the VM terminal:**
```bash
# Clone the repository
git clone https://github.com/danharris923/scrape-me.git
cd scrape-me

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### 6. Configure Environment

Create the environment file:
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

Set these required variables:
```bash
# LLM Configuration
SCRAPER_LLM_PROVIDER=anthropic
SCRAPER_LLM_MODEL=claude-3-5-sonnet-latest
SCRAPER_LLM_API_KEY=your_anthropic_api_key

# Google Cloud Storage
SCRAPER_GCS_CREDENTIALS_PATH=/home/ubuntu/scraper/credentials/scraper-credentials.json
SCRAPER_GCS_BUCKET_NAME=your-project-id-scraper-images

# Scraping Configuration
SCRAPER_BROWSER_HEADLESS=true
SCRAPER_SCRAPING_DELAY_SECONDS=3.0
SCRAPER_MAX_RETRIES=3
SCRAPER_QUALITY_THRESHOLD=0.7
```

### 7. Upload Service Account Credentials

```bash
# Create credentials directory
mkdir -p credentials

# Upload your service account key (from local machine)
# You can copy-paste the content or use scp:
nano credentials/scraper-credentials.json
# Paste the content of scraper-credentials.json here
```

### 8. Configure Site Settings

Edit the site configuration files:
```bash
# Edit outdoor gear site config
nano config/sites/outdoor-gear-site.json

# Edit tech deals site config  
nano config/sites/tech-deals-site.json
```

Update the URLs to actual affiliate URLs you want to scrape.

### 9. Test the Deployment

```bash
# Activate virtual environment
source venv/bin/activate

# Test basic functionality
python main.py --status

# Run a test scrape
python main.py --site outdoor-gear-site --test-mode

# Check logs
tail -f scraper.log
```

### 10. Start Scheduled Scraping

```bash
# Enable and start the systemd timer for daily scraping
sudo systemctl enable affiliate-scraper.timer
sudo systemctl start affiliate-scraper.timer

# Check timer status
systemctl status affiliate-scraper.timer

# Check service logs
journalctl -u affiliate-scraper.service -f
```

## Configuration Files

### Site Configuration Example

```json
{
  "site_name": "outdoor-gear-site",
  "output_path": "./output/outdoor-gear-products.json",
  "gcs_bucket": "your-project-id-scraper-images",
  "image_folder": "outdoor-gear",
  "urls_to_scrape": [
    {
      "url": "https://amazon.com/s?k=hiking+boots",
      "platform": "amazon",
      "category": "footwear",
      "expected_count": 20
    }
  ],
  "refresh_interval_hours": 24
}
```

## Monitoring & Maintenance

### Check System Status
```bash
# Check scraper status
python main.py --status

# View recent logs
journalctl -u affiliate-scraper.service --since "1 hour ago"

# Check disk usage
df -h

# Check memory usage
free -h
```

### Manual Operations
```bash
# Force refresh all sites
python main.py --all-sites --force-refresh

# Clean up old data
python main.py --cleanup --days 30

# Create backup
python main.py --backup
```

### Scaling Considerations

- **VM Size**: Start with e2-standard-2, scale up if needed
- **Storage**: Monitor disk usage, clean up old files regularly
- **Network**: Consider regional placement near your users
- **Costs**: Set up billing alerts and resource monitoring

## Troubleshooting

### Common Issues

1. **Playwright browser errors**: Ensure all dependencies are installed
2. **GCS upload failures**: Check service account permissions
3. **Memory issues**: Increase VM memory or reduce concurrent scraping
4. **Rate limiting**: Increase delays between requests

### Useful Commands

```bash
# Restart the scraper service
sudo systemctl restart affiliate-scraper.service

# View detailed error logs
journalctl -u affiliate-scraper.service -n 50

# Check Python package versions
pip list

# Update the scraper code
git pull origin main
sudo systemctl restart affiliate-scraper.service
```