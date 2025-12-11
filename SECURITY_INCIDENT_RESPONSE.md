# CRITICAL SECURITY INCIDENT RESPONSE

## 🚨 IMMEDIATE ACTION REQUIRED

The security audit on December 11, 2025 discovered that the `.env` file containing production secrets was committed to the Git repository and is exposed in version control history.

## Compromised Secrets

The following secrets were exposed in the `.env` file committed to Git and **MUST** be rotated immediately:

1. **Django SECRET_KEY** - [REDACTED - see .env file for current exposed value]
2. **Email Password** - [REDACTED - see .env file for current exposed value]
3. **Stripe Secret Key** - [REDACTED - see .env file for current exposed value]
4. **Stripe Webhook Secret** - [REDACTED - see .env file for current exposed value]

⚠️ **DO NOT commit these secrets again**. They are currently visible in your local `.env` file but must be rotated before production use.

## Step 1: Rotate All Secrets (DO THIS FIRST)

### 1.1 Generate New Django SECRET_KEY

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Update `.env` with the new key.

### 1.2 Change Email Password

1. Log into IONOS email account
2. Navigate to: Settings → Security → Change Password
3. Generate a strong password (use password manager)
4. Update `.env` with new password
5. Test email sending functionality

### 1.3 Rotate Stripe Keys

1. Log into Stripe Dashboard: https://dashboard.stripe.com/
2. Navigate to: Developers → API Keys
3. Click "Roll" on the Secret Key to generate new test key
4. Update `.env` with new `STRIPE_SECRET_KEY`
5. Navigate to: Developers → Webhooks
6. Delete existing webhook endpoint
7. Create new webhook endpoint with updated URL
8. Copy new webhook signing secret
9. Update `.env` with new `STRIPE_WEBHOOK_SECRET`

### 1.4 Update Production Environment

If these secrets are used in production:
1. SSH into production server
2. Update `/var/www/recorder_ed/.env` with all new secrets
3. Restart Gunicorn: `sudo systemctl restart gunicorn`
4. Restart Nginx: `sudo systemctl restart nginx`
5. Monitor logs for errors: `sudo journalctl -u gunicorn -f`

## Step 2: Remove .env from Git History

**WARNING:** This rewrites Git history. Coordinate with all team members.

```bash
# Backup current repository first
cd /Users/michaelpiraner/Projects/recordered
cp -r . ../recordered_backup_$(date +%Y%m%d)

# Remove .env from entire Git history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Force push to remote (WARNING: This is destructive)
git push origin --force --all
git push origin --force --tags
```

### Step 2.1: All Team Members Must Re-clone

After history rewrite, all team members must:

```bash
# Delete local repository
cd ..
rm -rf recordered

# Clone fresh copy
git clone git@github.com:polyphonica/recorder_ed.git
cd recordered

# Set up .env with NEW secrets
cp .env.example .env
# Edit .env with new secrets from Step 1
```

## Step 3: Verify .env is in .gitignore

Confirm `.env` is listed in `.gitignore`:

```bash
grep "^\.env$" .gitignore
```

If not present, add it:

```bash
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Ensure .env is in .gitignore"
git push
```

## Step 4: Audit Access

### 4.1 Who Had Access?

Repository access on GitHub: https://github.com/polyphonica/recorder_ed/settings/access

Review:
- Collaborators
- Teams with access
- Deploy keys
- GitHub Actions secrets

### 4.2 Check for Unauthorized Access

```bash
# Check Django admin login logs
# Check Stripe Dashboard event logs
# Check email account login history (IONOS)
# Review database for suspicious activity
```

## Step 5: Deploy Security Fixes

The security audit implemented critical fixes:

```bash
# Apply database migrations for new validators
source virtenv/bin/activate
python manage.py makemigrations
python manage.py migrate

# Verify settings
python manage.py check --deploy
```

### Changes Made:
1. ✅ Fixed DEBUG mode to use environment variable
2. ✅ Removed insecure SECRET_KEY default
3. ✅ Restricted CKEditor5 uploads to authenticated users only
4. ✅ Removed SVG upload support (XSS risk)
5. ✅ Fixed IDOR vulnerability in transfer_account_view
6. ✅ Added file upload validators to all FileFields
7. ✅ Fixed insecure random token generation

## Step 6: Future Prevention

### 6.1 Pre-commit Hook

Install pre-commit hook to prevent committing secrets:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# Install hooks
pre-commit install

# Generate baseline
detect-secrets scan > .secrets.baseline

# Test
pre-commit run --all-files
```

### 6.2 Use Environment Variables in Production

Never store secrets in code. Use:
- Environment variables (current approach - good)
- AWS Secrets Manager (better for production)
- HashiCorp Vault (enterprise)
- Azure Key Vault (if using Azure)

### 6.3 Regular Security Audits

Schedule quarterly security audits:
- Q1 2026: March 15
- Q2 2026: June 15
- Q3 2026: September 15
- Q4 2026: December 15

## Step 7: Notification

If production was compromised:

1. **Users**: No notification needed (no user data exposed)
2. **Payment Processor**: Contact Stripe if suspicious transactions detected
3. **Hosting Provider**: Inform if server compromise suspected

## Verification Checklist

- [ ] New Django SECRET_KEY generated and deployed
- [ ] Email password changed and tested
- [ ] Stripe keys rotated and webhook updated
- [ ] Production secrets updated and services restarted
- [ ] .env removed from Git history
- [ ] All team members have fresh clones
- [ ] .gitignore verified
- [ ] Database migrations applied
- [ ] Security fixes deployed and tested
- [ ] Pre-commit hooks installed
- [ ] Access logs reviewed
- [ ] No suspicious activity detected

## Contact

**Security Lead**: Michael Piraner (michael.piraner@recorder-ed.com)

**Emergency Response**: If you discover additional security issues, immediately:
1. Stop deployment
2. Email security lead
3. Document findings
4. Do not discuss publicly

---

**Created**: December 11, 2025
**Last Updated**: December 11, 2025
**Status**: ACTIVE INCIDENT - IMMEDIATE ACTION REQUIRED
