# Quick Deployment Checklist

Use this checklist while deploying to ensure you don't miss any steps. Check off each item as you complete it.

## Pre-Deployment (Local)
- [x] Updated settings.py with environment variables
- [x] Created requirements.txt with all dependencies
- [x] Created .env.example file
- [x] Committed and pushed to GitHub
- [ ] Made GitHub repository private

## Server Setup (Ionos)

### System & Software Installation
- [ ] SSH into server
- [ ] Run: `sudo apt update && sudo apt upgrade -y`
- [ ] Install Python: `sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential libpq-dev git`
- [ ] Install PostgreSQL: `sudo apt install -y postgresql postgresql-contrib`
- [ ] Install Nginx: `sudo apt install -y nginx`

### Database Configuration
- [ ] Access PostgreSQL: `sudo -u postgres psql`
- [ ] Create database: `CREATE DATABASE recordered_db;`
- [ ] Create user: `CREATE USER recordered_user WITH PASSWORD 'your_password';`
- [ ] Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE recordered_db TO recordered_user;`
- [ ] Set encoding: `ALTER ROLE recordered_user SET client_encoding TO 'utf8';`
- [ ] Set isolation: `ALTER ROLE recordered_user SET default_transaction_isolation TO 'read committed';`
- [ ] Set timezone: `ALTER ROLE recordered_user SET timezone TO 'UTC';`
- [ ] Exit PostgreSQL: `\q`

### Application Deployment
- [ ] Create directory: `sudo mkdir -p /var/www && cd /var/www`
- [ ] Clone repo: `sudo git clone https://github.com/polyphonica/recorder_ed.git`
- [ ] Set ownership: `sudo chown -R $USER:$USER recorder_ed && cd recorder_ed`
- [ ] Create venv: `python3 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Upgrade pip: `pip install --upgrade pip`
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Copy env file: `cp .env.example .env`
- [ ] Edit .env: `nano .env` (Set all production values!)
- [ ] Generate SECRET_KEY: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Collect static: `python manage.py collectstatic --noinput`
- [ ] Create media dir: `mkdir -p media && chmod 755 media`

### Gunicorn Configuration
- [ ] Test Gunicorn: `gunicorn --bind 0.0.0.0:8000 recordered.wsgi` (Ctrl+C to stop)
- [ ] Create socket: `sudo nano /etc/systemd/system/gunicorn.socket`
- [ ] Create service: `sudo nano /etc/systemd/system/gunicorn.service`
- [ ] Set permissions: `sudo chown -R www-data:www-data /var/www/recorder_ed`
- [ ] Set file mode: `sudo chmod -R 755 /var/www/recorder_ed`
- [ ] Start socket: `sudo systemctl start gunicorn.socket`
- [ ] Enable socket: `sudo systemctl enable gunicorn.socket`
- [ ] Check status: `sudo systemctl status gunicorn.socket`

### Nginx Configuration
- [ ] Create site config: `sudo nano /etc/nginx/sites-available/recordered`
- [ ] Enable site: `sudo ln -s /etc/nginx/sites-available/recordered /etc/nginx/sites-enabled/`
- [ ] Test config: `sudo nginx -t`
- [ ] Restart Nginx: `sudo systemctl restart nginx`

### Testing
- [ ] Visit `http://your-domain.com` in browser
- [ ] Visit `http://your-server-ip` in browser
- [ ] Test admin login at `/admin`
- [ ] Check static files are loading (CSS/JS)
- [ ] Test image uploads in media

### SSL Setup (Recommended)
- [ ] Install Certbot: `sudo apt install -y certbot python3-certbot-nginx`
- [ ] Get certificate: `sudo certbot --nginx -d your-domain.com -d www.your-domain.com`
- [ ] Choose redirect option (2)
- [ ] Test renewal: `sudo certbot renew --dry-run`

### Firewall Setup (Optional)
- [ ] Install UFW: `sudo apt install -y ufw`
- [ ] Allow SSH: `sudo ufw allow OpenSSH`
- [ ] Allow Nginx: `sudo ufw allow 'Nginx Full'`
- [ ] Enable firewall: `sudo ufw enable`
- [ ] Check status: `sudo ufw status`

### Post-Deployment
- [ ] Test all three domains (Workshops, Courses, Private Teaching)
- [ ] Create test teacher account
- [ ] Create test student account
- [ ] Create test guardian account with child profile
- [ ] Test workshop registration
- [ ] Test course enrollment
- [ ] Test private teaching application workflow
- [ ] Test messaging features
- [ ] Verify email sending works
- [ ] Set up database backup cron job
- [ ] Document admin credentials securely
- [ ] Monitor server resources
- [ ] Set up log rotation

## Important Files to Keep Secure
- `/var/www/recorder_ed/.env` - Never commit to git!
- Database backup files
- SSL certificates (auto-managed by Certbot)
- Admin credentials

## Quick Commands Reference

### Update Application After Changes
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
# Gunicorn
sudo journalctl -u gunicorn -f

# Nginx errors
sudo tail -f /var/log/nginx/error.log

# Nginx access
sudo tail -f /var/log/nginx/access.log
```

### Restart Services
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl restart postgresql
```

### Database Backup
```bash
sudo -u postgres pg_dump recordered_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Environment Variables Checklist

Make sure your `.env` file contains:
- [ ] SECRET_KEY (newly generated, not the default)
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS (your domain and IP)
- [ ] DATABASE_URL
- [ ] DB_NAME
- [ ] DB_USER
- [ ] DB_PASSWORD
- [ ] DB_HOST
- [ ] DB_PORT
- [ ] EMAIL_HOST
- [ ] EMAIL_PORT
- [ ] EMAIL_USE_TLS
- [ ] EMAIL_HOST_USER
- [ ] EMAIL_HOST_PASSWORD
- [ ] DEFAULT_FROM_EMAIL

## Common Issues & Quick Fixes

**502 Bad Gateway**
→ Check: `sudo systemctl status gunicorn`
→ Restart: `sudo systemctl restart gunicorn`

**Static files not loading**
→ Run: `python manage.py collectstatic --noinput`
→ Check permissions: `sudo chown -R www-data:www-data /var/www/recorder_ed/staticfiles`

**Database connection error**
→ Check PostgreSQL: `sudo systemctl status postgresql`
→ Verify credentials in `.env`

**Permission denied errors**
→ Fix ownership: `sudo chown -R www-data:www-data /var/www/recorder_ed`
→ Fix permissions: `sudo chmod -R 755 /var/www/recorder_ed`

---

**Note**: This is a living document. Update it as you discover additional steps or issues during deployment.
