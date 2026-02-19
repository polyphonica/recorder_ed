#!/bin/bash
# Sync Stripe fees for platform finance tracking
# Run via cron: 0 2 * * * /var/www/recorder_ed/scripts/sync_stripe_fees.sh

PROJECT_DIR="/var/www/recorder_ed"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/stripe_sync.log"

mkdir -p "$LOG_DIR"

echo "" >> "$LOG_FILE"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG_FILE"

cd "$PROJECT_DIR" || {
    echo "Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

source venv/bin/activate || {
    echo "Failed to activate virtual environment" >> "$LOG_FILE"
    exit 1
}

python manage.py sync_stripe_fees --days=7 >> "$LOG_FILE" 2>&1

echo "Sync completed with exit code: $?" >> "$LOG_FILE"
