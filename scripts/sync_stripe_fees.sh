#!/bin/bash
# Sync Stripe fees for platform finance tracking
# Run via cron: 0 2 * * * /path/to/recorder_ed/scripts/sync_stripe_fees.sh
#
# Setup:
# 1. Update PROJECT_DIR below to match your server path
# 2. chmod +x scripts/sync_stripe_fees.sh
# 3. Add to crontab: crontab -e

# Configuration - UPDATE THIS PATH FOR YOUR SERVER
PROJECT_DIR="/home/yourusername/recorder_ed"

# Log file location
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/stripe_sync.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Add timestamp to log
echo "" >> "$LOG_FILE"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_DIR" || {
    echo "Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Activate virtual environment
source virtenv/bin/activate || {
    echo "Failed to activate virtual environment" >> "$LOG_FILE"
    exit 1
}

# Run the sync command (last 7 days to catch any missed transactions)
python manage.py sync_stripe_fees --days=7 >> "$LOG_FILE" 2>&1

# Log completion
echo "Sync completed with exit code: $?" >> "$LOG_FILE"
