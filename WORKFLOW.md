# Development and Deployment Workflow

## FileZilla vs Git Comparison

### ❌ FileZilla Approach (Not Recommended)

**What gets transferred:**
- ✅ Source code (.py files, templates, etc.)
- ❌ `venv/` - Your entire virtual environment (unnecessary, takes forever)
- ❌ `__pycache__/` - Python cache files (regenerated automatically)
- ❌ `*.pyc` - Compiled Python files (regenerated automatically)
- ❌ `db.sqlite3` - Your local database (should use PostgreSQL on server)
- ❌ `.env` - **DANGEROUS!** Contains secrets, should be server-specific
- ❌ `staticfiles/` - Should be regenerated on server
- ❌ Local `media/` uploads - Pollutes production with test data
- ❌ `.git/` folder - If transferred, wastes space

**Problems:**
- Very slow (transfers 100MB+ of unnecessary files)
- Risk of overwriting production `.env` with local settings
- Risk of overwriting production database
- Can't easily see what changed
- Can't roll back mistakes
- Manual process prone to human error

### ✅ Git Approach (Recommended - Industry Standard)

**What gets transferred:**
- ✅ Source code only (respects .gitignore)
- ✅ Templates and static source files
- ✅ Requirements.txt
- ✅ Migration files
- ❌ Everything else is excluded by .gitignore

**Benefits:**
- Lightning fast (only transfers changed files)
- Version control on server
- Easy rollback: `git checkout previous-commit`
- See what changed: `git log` or `git diff`
- Automatic exclusion of sensitive files
- Industry best practice
- Foundation for CI/CD automation

---

## Recommended Workflow for Ongoing Work

### One-Time Server Setup

**1. Install Git on server (if not already installed):**
```bash
ssh user@your-ionos-server
sudo apt update
sudo apt install -y git
```

**2. Clone repository:**
```bash
cd /var/www
git clone https://github.com/polyphonica/recorder_ed.git
cd recorder_ed
```

**3. Follow DEPLOYMENT_GUIDE.md for initial setup:**
- Create venv
- Install requirements
- Create production .env file
- Run migrations
- Setup Gunicorn and Nginx
- etc.

---

### Daily Development Workflow

#### On Your Local Machine:

**1. Make your changes:**
```bash
# Edit files, add features, fix bugs
# Test locally with: python manage.py runserver
```

**2. Commit and push:**
```bash
git add .
git commit -m "Clear description of what you changed"
git push origin main
```

#### On Your Ionos Server:

**Option A: Manual deployment (good for learning):**
```bash
ssh user@your-ionos-server
cd /var/www/recorder_ed
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # If dependencies changed
python manage.py migrate         # If models changed
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

**Option B: Automated with script (recommended once comfortable):**
```bash
ssh user@your-ionos-server
cd /var/www/recorder_ed
./deploy.sh
```

That's it! The script does everything automatically.

---

## Comparison Table

| Task | FileZilla | Git |
|------|-----------|-----|
| **Transfer speed** | Slow (100MB+) | Fast (<1MB usually) |
| **Setup time** | Quick | One-time setup |
| **Update time** | 5-10 minutes | 30 seconds |
| **Risk of breaking site** | High | Low |
| **Version control** | None | Full history |
| **Rollback capability** | None | Easy |
| **Team collaboration** | Difficult | Easy |
| **Industry standard** | No | Yes |
| **Automation potential** | None | High |
| **Files transferred** | Everything | Source code only |

---

## What About Special Cases?

### "What if I need to transfer media files?"

**Development media:** Don't transfer to production
**Production media:** Lives on server, backed up separately

If you need to sync media between environments:
```bash
# On server, create backup
cd /var/www/recorder_ed
tar -czf media_backup.tar.gz media/

# Download to local (from local machine)
scp user@server:/var/www/recorder_ed/media_backup.tar.gz .
```

### "What if I change requirements.txt?"

The `deploy.sh` script automatically runs `pip install -r requirements.txt`

### "What if I change models?"

The `deploy.sh` script automatically runs `python manage.py migrate`

### "What about the .env file?"

- `.env` is in `.gitignore` - **never transferred**
- Each environment has its own `.env` file:
  - **Local:** DEBUG=True, SQLite database
  - **Production:** DEBUG=False, PostgreSQL database, real email credentials

---

## Example: Complete Update Workflow

Let's say you want to add a new field to a model:

**Local machine:**
```bash
# 1. Make the change
nano apps/courses/models.py  # Add new field

# 2. Create migration
python manage.py makemigrations

# 3. Test locally
python manage.py migrate
python manage.py runserver
# Test the change works

# 4. Commit and push
git add .
git commit -m "Add completion_percentage field to Course model"
git push origin main
```

**Production server:**
```bash
ssh user@your-ionos-server
cd /var/www/recorder_ed
./deploy.sh
```

Done! The script will:
- Pull your code
- Run the migration
- Restart the server

---

## Security Note

Your `.gitignore` already excludes:
- `.env` - Environment variables and secrets
- `db.sqlite3` - Local database
- `venv/` - Virtual environment
- `__pycache__/` - Python cache
- `*.pyc` - Compiled files
- `/media` - User uploads
- `/staticfiles` - Generated static files

This means sensitive information never gets pushed to GitHub.

---

## Troubleshooting

**"I pushed changes but site not updating"**
→ Did you run `git pull` on the server?
→ Did you restart Gunicorn?

**"Git pull says 'Already up to date'"**
→ Did you push from local? Check with `git push origin main`

**"Permission denied on git pull"**
→ Check file ownership: `sudo chown -R $USER:$USER /var/www/recorder_ed`

**"Static files not updating"**
→ Run `python manage.py collectstatic --noinput`
→ Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

---

## Future: Automated Deployment (Optional Advanced)

Once comfortable with Git workflow, you can set up:

1. **Git Hooks** - Automatically deploy when you push
2. **GitHub Actions** - Run tests before deploying
3. **Webhooks** - Server pulls changes automatically

But for now, the `deploy.sh` script is perfect and gives you control.

---

## Summary

**Stop using FileZilla for code deployment.**

**Instead:**
1. ✅ Use Git for all code changes
2. ✅ Use `./deploy.sh` script for quick deployments
3. ✅ Keep `.env` files separate per environment
4. ✅ Use FileZilla only for:
   - One-time media file transfers
   - Database backups download
   - Log file downloads for debugging

This is how professional Django developers work, and it will save you tons of time and prevent many mistakes!
