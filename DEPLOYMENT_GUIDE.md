# Deployment Guide for Ionos Server

This guide walks through deploying the Recorder Ed Django application to an Ionos virtual server.

## Prerequisites
- SSH access to your Ionos server
- Domain name configured to point to your server's IP
- Root or sudo access

---

## Part 1: Server Preparation

### 1. Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python and Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential libpq-dev git
```

### 3. Install and Configure PostgreSQL
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 4. Create PostgreSQL Database and User
```bash
# Switch to postgres user
sudo -u postgres psql

# Inside PostgreSQL shell, run these commands:
CREATE DATABASE recordered_db;
CREATE USER recordered_user WITH PASSWORD 'your_secure_password';
ALTER ROLE recordered_user SET client_encoding TO 'utf8';
ALTER ROLE recordered_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE recordered_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE recordered_db TO recordered_user;
\q
```

### 5. Install Nginx
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## Part 2: Application Setup

### 6. Clone Repository
```bash
# Create application directory
sudo mkdir -p /var/www
cd /var/www

# Clone your repository
sudo git clone https://github.com/polyphonica/recorder_ed.git
sudo chown -R $USER:$USER recorder_ed
cd recorder_ed
```

### 7. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 8. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 9. Create Environment File
```bash
# Copy example env file
cp .env.example .env

# Edit with your production settings
nano .env
```

**Important environment variables to set in `.env`:**
```bash
SECRET_KEY=generate-a-new-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

DATABASE_URL=postgresql://recordered_user:your_secure_password@localhost:5432/recordered_db
DB_NAME=recordered_db
DB_USER=recordered_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Email settings (configure based on your email provider)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com
```

**Generate a new SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 10. Run Database Migrations
```bash
python manage.py migrate
```

### 11. Create Django Superuser
```bash
python manage.py createsuperuser
```

### 12. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 13. Set Up Media Directory
```bash
mkdir -p media
chmod 755 media
```

---

## Part 3: Gunicorn Configuration

### 14. Test Gunicorn (should already be installed from requirements.txt)
```bash
gunicorn --bind 0.0.0.0:8000 recordered.wsgi
```
Press Ctrl+C to stop after testing.

### 15. Create Gunicorn Socket File
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```

Add this content:
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 16. Create Gunicorn Service File
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add this content (adjust paths and user as needed):
```ini
[Unit]
Description=gunicorn daemon for recordered
Requires=gunicorn.socket
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/recorder_ed
EnvironmentFile=/var/www/recorder_ed/.env
ExecStart=/var/www/recorder_ed/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          recordered.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 17. Set Correct Permissions
```bash
# Change ownership to www-data
sudo chown -R www-data:www-data /var/www/recorder_ed

# Ensure www-data can access the files
sudo chmod -R 755 /var/www/recorder_ed
```

### 18. Start and Enable Gunicorn
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl status gunicorn.socket

# Test the socket
sudo systemctl status gunicorn
```

---

## Part 4: Nginx Configuration

### 19. Create Nginx Site Configuration
```bash
sudo nano /etc/nginx/sites-available/recordered
```

Add this content (replace `your-domain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 100M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/recorder_ed/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/recorder_ed/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
    }
}
```

### 20. Enable Nginx Site
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/recordered /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# If test passes, restart Nginx
sudo systemctl restart nginx
```

---

## Part 5: Testing and SSL Setup

### 21. Test Application Access
Open your browser and visit:
- `http://your-domain.com`
- `http://your-server-ip`

Check that:
- Application loads correctly
- Admin panel is accessible at `/admin`
- Static files (CSS/JS) are loading
- Images and media uploads work

### 22. Set Up SSL with Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow the prompts:
# - Enter your email
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (option 2)

# Test automatic renewal
sudo certbot renew --dry-run
```

### 23. Configure Firewall (Optional but Recommended)
```bash
# Install UFW if not already installed
sudo apt install -y ufw

# Allow SSH (IMPORTANT: do this first!)
sudo ufw allow OpenSSH

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## Part 6: Maintenance Commands

### Restart Services After Code Updates
```bash
cd /var/www/recorder_ed
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

### View Logs
```bash
# Gunicorn logs
sudo journalctl -u gunicorn -f

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### Database Backup
```bash
# Create backup
sudo -u postgres pg_dump recordered_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
sudo -u postgres psql recordered_db < backup_file.sql
```

---

## Troubleshooting

### Gunicorn Not Starting
```bash
# Check Gunicorn logs
sudo journalctl -u gunicorn -n 50

# Check socket status
sudo systemctl status gunicorn.socket

# Restart Gunicorn
sudo systemctl restart gunicorn
```

### 502 Bad Gateway
- Check Gunicorn is running: `sudo systemctl status gunicorn`
- Check socket permissions: `ls -l /run/gunicorn.sock`
- Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### Static Files Not Loading
```bash
# Recollect static files
cd /var/www/recorder_ed
source venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
sudo chown -R www-data:www-data /var/www/recorder_ed/staticfiles
```

### Database Connection Errors
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check `.env` file has correct database credentials
- Test database connection: `sudo -u postgres psql recordered_db`

---

## Security Best Practices

1. **Never commit `.env` file to git** - Already configured in .gitignore
2. **Use strong passwords** for database and Django admin
3. **Keep software updated**: Run `sudo apt update && sudo apt upgrade` regularly
4. **Monitor logs** for suspicious activity
5. **Regular backups** of database and media files
6. **Use HTTPS only** in production (Let's Encrypt SSL)
7. **Restrict SSH access** - Consider using SSH keys instead of passwords

---

## Next Steps After Deployment

1. Test all functionality thoroughly
2. Create test user accounts for each role (teacher, student, guardian)
3. Create sample workshops and courses
4. Test the private teaching application workflow
5. Monitor server resources (CPU, memory, disk space)
6. Set up automated backups
7. Plan for Stripe payment integration (after testing phase)

---

## Support

For issues specific to:
- **Django**: Check application logs and Django documentation
- **Nginx**: Check `/var/log/nginx/error.log`
- **PostgreSQL**: Check `/var/log/postgresql/`
- **Gunicorn**: Check `sudo journalctl -u gunicorn`
