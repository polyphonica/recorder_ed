#!/bin/bash

# Deployment script for Recorder Ed
# Run this on the server after pushing changes to GitHub

echo "🚀 Starting deployment..."

# Navigate to project directory
cd /var/www/recorder_ed || exit

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "💾 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Restart the app and the Celery worker (so background tasks run the new code)
echo "🔄 Restarting Gunicorn and Celery..."
sudo systemctl restart gunicorn_recordered
sudo systemctl restart celery_recordered

# Restart Nginx (optional, usually not needed)
# sudo systemctl restart nginx

echo "✅ Deployment complete!"
echo ""
echo "📊 Checking service status..."
sudo systemctl status gunicorn_recordered celery_recordered --no-pager -l

echo ""
echo "🎉 Deployment finished successfully!"
echo "Visit your site to verify everything is working."
