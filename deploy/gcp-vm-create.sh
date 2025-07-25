#!/bin/bash

# GCP VM Creation Script for Affiliate Scraper
# This script creates a VM instance optimized for web scraping with Playwright

set -e

echo "🚀 Creating GCP VM for Affiliate Scraper..."

# Configuration
PROJECT_ID="${1:-your-project-id}"
VM_NAME="affiliate-scraper"
ZONE="us-central1-b"
MACHINE_TYPE="e2-standard-2"  # 2 vCPUs, 8GB RAM
BOOT_DISK_SIZE="50GB"
BOOT_DISK_TYPE="pd-standard"

echo "📋 VM Configuration:"
echo "  Project: $PROJECT_ID"
echo "  VM Name: $VM_NAME"
echo "  Zone: $ZONE"
echo "  Machine Type: $MACHINE_TYPE"
echo "  Boot Disk: $BOOT_DISK_SIZE ($BOOT_DISK_TYPE)"

# Create the VM instance
gcloud compute instances create $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=$PROJECT_ID-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/devstorage.read_write,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append \
    --tags=http-server,https-server,scraper \
    --create-disk=auto-delete=yes,boot=yes,device-name=$VM_NAME,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20241119,mode=rw,size=$BOOT_DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/$BOOT_DISK_TYPE \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=environment=production,application=affiliate-scraper \
    --reservation-affinity=any

echo "✅ VM '$VM_NAME' created successfully!"

# Get the external IP
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "🌐 External IP: $EXTERNAL_IP"
echo ""
echo "🔑 To connect via SSH:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID"
echo ""
echo "🌐 Or use browser SSH:"
echo "  https://console.cloud.google.com/compute/instances"
echo ""
echo "📝 Next steps:"
echo "  1. SSH into the VM"
echo "  2. Clone the repository: git clone https://github.com/danharris923/scrape-me.git"
echo "  3. Run the setup script: cd scrape-me && chmod +x setup.sh && ./setup.sh"