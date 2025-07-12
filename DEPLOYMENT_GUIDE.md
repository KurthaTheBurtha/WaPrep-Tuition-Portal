# WAPrep Tuition Portal - Backup & Recovery Deployment Guide

## Overview
This guide will help you implement the comprehensive backup and recovery plan for your WAPrep Tuition Portal deployment.

## Prerequisites

### 1. Cloud Storage Setup
Choose one of the following cloud storage providers:

#### Option A: AWS S3 (Recommended)
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region

# Create S3 bucket for backups
aws s3 mb s3://waprep-backup-bucket
aws s3api put-bucket-encryption --bucket waprep-backup-bucket --server-side-encryption-configuration '{
    "Rules": [
        {
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }
    ]
}'
```

#### Option B: Google Cloud Storage
```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Create storage bucket
gsutil mb gs://waprep-backup-bucket
gsutil iam ch allUsers:objectViewer gs://waprep-backup-bucket
```

#### Option C: Azure Blob Storage
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login

# Create storage account and container
az storage account create --name waprepbackup --resource-group your-rg --location westus2 --sku Standard_LRS
az storage container create --name backups --account-name waprepbackup
```

### 2. Environment Variables
Add these to your production environment:

```bash
# Backup Configuration
S3_BACKUP_BUCKET=waprep-backup-bucket
BACKUP_NOTIFICATION_EMAIL=admin@waprep.com
ADMIN_EMAIL=admin@waprep.com

# AWS Credentials (if using S3)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

### 3. Install Required Packages
Add to your `requirements.txt`:

```txt
boto3>=1.26.0
botocore>=1.29.0
```

## Deployment Steps

### Step 1: Upload Backup Scripts

1. **Upload the backup script to your deployment platform:**

For Railway:
```bash
# Add to your repository
git add scripts/daily_backup.sh
git commit -m "Add backup script"
git push
```

For Render:
```bash
# Add to your repository and configure in Render dashboard
```

For Heroku:
```bash
# Add to your repository
git add scripts/daily_backup.sh
git commit -m "Add backup script"
git push heroku main
```

2. **Make the script executable:**
```bash
chmod +x scripts/daily_backup.sh
```

### Step 2: Configure Automated Backups

#### For Railway:
1. Go to your Railway project dashboard
2. Navigate to Settings → Variables
3. Add the environment variables listed above
4. Go to Settings → Cron Jobs
5. Add a new cron job:
   - **Command:** `./scripts/daily_backup.sh`
   - **Schedule:** `0 2 * * *` (daily at 2 AM)

#### For Render:
1. Go to your Render dashboard
2. Navigate to your service → Environment
3. Add the environment variables
4. Go to Settings → Cron Jobs
5. Add a new cron job:
   - **Command:** `./scripts/daily_backup.sh`
   - **Schedule:** `0 2 * * *`

#### For Heroku:
1. Install Heroku Scheduler addon:
```bash
heroku addons:create scheduler:standard
```

2. Configure the scheduler:
```bash
heroku scheduler:add "./scripts/daily_backup.sh" --dyno=basic --frequency=daily
```

### Step 3: Test Backup System

1. **Run a manual backup:**
```bash
./scripts/daily_backup.sh
```

2. **Verify backup files:**
```bash
# Check local backups
ls -la /backups/daily/database/

# Check S3 backups (if using AWS)
aws s3 ls s3://waprep-backup-bucket/database/
```

3. **Test recovery script:**
```bash
# List available backups
python scripts/recovery.py --list

# Test data integrity
python manage.py health_check --check-backups
```

### Step 4: Configure Monitoring

1. **Set up health checks:**
```bash
# Add to your deployment platform's health check endpoint
python manage.py health_check --send-alerts
```

2. **Configure monitoring schedule:**
   - **Daily health checks:** Run every 6 hours
   - **Backup verification:** Run after each backup
   - **Alert notifications:** Configure email alerts

### Step 5: Test Recovery Procedures

1. **Create a staging environment** for testing recovery
2. **Test database recovery:**
```bash
python scripts/recovery.py --recover local:latest_backup.sql.gz
```

3. **Test file recovery:**
```bash
python scripts/recovery.py --recover local:receipts_backup.tar.gz --type files
```

## Platform-Specific Configurations

### Railway Deployment
```yaml
# railway.json (if using Railway)
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn tuition.wsgi --log-file -",
    "healthcheckPath": "/health/",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Render Deployment
```yaml
# render.yaml
services:
  - type: web
    name: waprep-tuition
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn tuition.wsgi --log-file -
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.11
      - key: DATABASE_URL
        sync: false
```

### Heroku Deployment
```bash
# Procfile (already exists)
web: gunicorn tuition.wsgi --log-file -

# Add buildpacks if needed
heroku buildpacks:add heroku/python
```

## Security Considerations

### 1. Encrypt Sensitive Data
```bash
# Encrypt environment variables before backup
gpg --encrypt --recipient admin@waprep.com .env
```

### 2. Access Control
```bash
# Set up IAM roles for S3 access (AWS)
aws iam create-role --role-name WAPrepBackupRole --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
```

### 3. Backup Retention Policy
```bash
# Configure automatic cleanup in backup script
RETENTION_DAYS=30  # Keep backups for 30 days
```

## Monitoring and Alerting

### 1. Set up Email Alerts
Configure your email settings in Django:

```python
# settings_production.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.office365.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
```

### 2. Health Check Endpoint
Add to your `urls.py`:

```python
from django.http import JsonResponse
from django.core.management import call_command
from io import StringIO

def health_check(request):
    """Health check endpoint for monitoring"""
    output = StringIO()
    call_command('health_check', stdout=output)
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': output.getvalue()
    })
```

## Maintenance Schedule

### Daily Tasks
- [ ] Monitor backup completion
- [ ] Check health status
- [ ] Review error logs

### Weekly Tasks
- [ ] Test recovery procedures
- [ ] Verify backup integrity
- [ ] Update documentation

### Monthly Tasks
- [ ] Review backup retention
- [ ] Test disaster recovery
- [ ] Update security policies

## Troubleshooting

### Common Issues

1. **Backup fails with permission error:**
```bash
# Fix permissions
chmod +x scripts/daily_backup.sh
chmod 755 /backups
```

2. **S3 upload fails:**
```bash
# Check AWS credentials
aws sts get-caller-identity
```

3. **Database connection fails:**
```bash
# Check DATABASE_URL
echo $DATABASE_URL
```

4. **Recovery script fails:**
```bash
# Check Django settings
python manage.py check --deploy
```

### Emergency Procedures

1. **Immediate Response:**
   - Stop the application
   - Assess the damage
   - Notify stakeholders

2. **Recovery Steps:**
   - Restore from latest backup
   - Verify data integrity
   - Restart application

3. **Post-Recovery:**
   - Document the incident
   - Update procedures
   - Schedule review

## Support and Resources

### Documentation
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)

### Emergency Contacts
- **Primary Admin:** [Your Name] - [Phone] - [Email]
- **Backup Admin:** [Backup Admin Name] - [Phone] - [Email]
- **Cloud Provider Support:** [Provider] - [Support Number]

---

**Last Updated:** [Date]
**Next Review:** [Date + 3 months]
**Version:** 1.0 