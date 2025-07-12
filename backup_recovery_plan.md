# WAPrep Tuition Portal - Data Backup and Recovery Plan

## 1. Critical Data Components

### Database Data (PostgreSQL)
- **User accounts** (payers, admins)
- **Student records** (personal info, balances, status)
- **Payment records** (transactions, receipts, history)
- **Billing data** (payment breakdowns, due dates)
- **Bank account information** (encrypted tokens)
- **Payment methods** (cards, bank accounts)
- **Password history** (for security compliance)

### File Storage
- **Receipt PDFs** (`receipts/` directory)
- **Static files** (CSS, images, logos)
- **Uploaded documents** (if any)

### Configuration Data
- **Environment variables** (`.env` file)
- **Django settings** (production vs development)
- **Stripe configuration** (API keys, webhooks)

## 2. Backup Strategy

### 2.1 Database Backups

#### Automated Daily Backups
```bash
#!/bin/bash
# daily_backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
DB_URL="your_postgresql_connection_string"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create PostgreSQL dump
pg_dump $DB_URL > $BACKUP_DIR/waprep_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/waprep_backup_$DATE.sql

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (AWS S3, Google Cloud, etc.)
aws s3 cp $BACKUP_DIR/waprep_backup_$DATE.sql.gz s3://your-backup-bucket/database/
```

#### Weekly Full Backups
```bash
#!/bin/bash
# weekly_backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/weekly"

# Full database backup with custom format
pg_dump -Fc $DB_URL > $BACKUP_DIR/waprep_full_$DATE.dump

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/waprep_full_$DATE.dump s3://your-backup-bucket/weekly/
```

### 2.2 File Storage Backups

#### Receipt Files Backup
```bash
#!/bin/bash
# file_backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/files"
RECEIPTS_DIR="/app/receipts"
STATIC_DIR="/app/staticfiles"

# Backup receipts
tar -czf $BACKUP_DIR/receipts_$DATE.tar.gz -C $RECEIPTS_DIR .

# Backup static files
tar -czf $BACKUP_DIR/static_$DATE.tar.gz -C $STATIC_DIR .

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/receipts_$DATE.tar.gz s3://your-backup-bucket/files/
aws s3 cp $BACKUP_DIR/static_$DATE.tar.gz s3://your-backup-bucket/files/
```

### 2.3 Configuration Backup
```bash
#!/bin/bash
# config_backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/config"

# Backup environment variables (encrypted)
gpg --encrypt --recipient admin@waprep.com .env > $BACKUP_DIR/env_$DATE.gpg

# Backup Django settings
cp tuition/settings_production.py $BACKUP_DIR/settings_production_$DATE.py

# Upload to secure cloud storage
aws s3 cp $BACKUP_DIR/env_$DATE.gpg s3://your-backup-bucket/config/
aws s3 cp $BACKUP_DIR/settings_production_$DATE.py s3://your-backup-bucket/config/
```

## 3. Recovery Procedures

### 3.1 Database Recovery

#### Point-in-Time Recovery
```bash
#!/bin/bash
# database_recovery.sh
BACKUP_FILE=$1
DB_URL="your_postgresql_connection_string"

# Stop application
echo "Stopping application..."
# Add your platform-specific stop command

# Restore database
echo "Restoring database from $BACKUP_FILE..."
pg_restore -d $DB_URL $BACKUP_FILE

# Run migrations
python manage.py migrate

# Start application
echo "Starting application..."
# Add your platform-specific start command
```

#### Emergency Recovery Script
```python
# emergency_recovery.py
import os
import subprocess
from django.core.management import execute_from_command_line

def emergency_recovery():
    """Emergency database recovery procedure"""
    
    # 1. Stop all processes
    print("Stopping all processes...")
    
    # 2. Restore from latest backup
    backup_file = get_latest_backup()
    print(f"Restoring from {backup_file}")
    
    # 3. Restore database
    subprocess.run(['pg_restore', '-d', os.getenv('DATABASE_URL'), backup_file])
    
    # 4. Run migrations
    execute_from_command_line(['manage.py', 'migrate'])
    
    # 5. Verify data integrity
    verify_data_integrity()
    
    # 6. Restart application
    print("Restarting application...")

def verify_data_integrity():
    """Verify critical data after recovery"""
    from tuition.models import User, Student, Payment
    
    # Check user count
    user_count = User.objects.count()
    print(f"Users recovered: {user_count}")
    
    # Check student count
    student_count = Student.objects.count()
    print(f"Students recovered: {student_count}")
    
    # Check payment count
    payment_count = Payment.objects.count()
    print(f"Payments recovered: {payment_count}")
```

### 3.2 File Recovery
```bash
#!/bin/bash
# file_recovery.sh
BACKUP_FILE=$1
RESTORE_DIR="/app"

# Stop application
echo "Stopping application..."

# Restore files
echo "Restoring files from $BACKUP_FILE..."
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# Set proper permissions
chmod -R 755 $RESTORE_DIR/receipts
chmod -R 755 $RESTORE_DIR/staticfiles

# Start application
echo "Starting application..."
```

## 4. Monitoring and Alerting

### 4.1 Backup Monitoring
```python
# backup_monitor.py
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def check_backup_status():
    """Monitor backup success and alert on failures"""
    
    # Check if daily backup completed
    backup_file = f"/backups/database/waprep_backup_{datetime.now().strftime('%Y%m%d')}.sql.gz"
    
    if not os.path.exists(backup_file):
        send_alert("Backup failed", "Daily backup did not complete")
        return False
    
    # Check backup size (should be reasonable)
    file_size = os.path.getsize(backup_file)
    if file_size < 1000:  # Less than 1KB
        send_alert("Backup suspicious", f"Backup file too small: {file_size} bytes")
        return False
    
    return True

def send_alert(subject, message):
    """Send alert email to administrators"""
    msg = MIMEText(message)
    msg['Subject'] = f"WAPrep Backup Alert: {subject}"
    msg['From'] = os.getenv('ALERT_EMAIL_FROM')
    msg['To'] = os.getenv('ADMIN_EMAIL')
    
    # Send email
    with smtplib.SMTP(os.getenv('SMTP_HOST'), os.getenv('SMTP_PORT')) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
        server.send_message(msg)
```

### 4.2 Health Checks
```python
# health_check.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Perform system health checks'
    
    def handle(self, *args, **options):
        checks = [
            self.check_database_connection,
            self.check_database_size,
            self.check_backup_status,
            self.check_stripe_connection,
        ]
        
        for check in checks:
            try:
                check()
                self.stdout.write(f"✓ {check.__name__} passed")
            except Exception as e:
                self.stdout.write(f"✗ {check.__name__} failed: {e}")
    
    def check_database_connection(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    
    def check_database_size(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            size = cursor.fetchone()[0]
            self.stdout.write(f"Database size: {size}")
    
    def check_backup_status(self):
        # Check if recent backup exists
        pass
    
    def check_stripe_connection(self):
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        stripe.Account.retrieve()
```

## 5. Implementation Steps

### Phase 1: Setup Automated Backups (Week 1)
1. **Set up cloud storage** (AWS S3, Google Cloud Storage, or Azure Blob)
2. **Create backup scripts** and test locally
3. **Set up cron jobs** for automated execution
4. **Configure monitoring** and alerting

### Phase 2: Recovery Testing (Week 2)
1. **Test database recovery** in staging environment
2. **Test file recovery** procedures
3. **Document recovery times** and procedures
4. **Train administrators** on recovery procedures

### Phase 3: Production Deployment (Week 3)
1. **Deploy backup scripts** to production
2. **Set up monitoring** dashboards
3. **Create runbooks** for common scenarios
4. **Schedule regular recovery drills**

## 6. Security Considerations

### 6.1 Backup Encryption
```bash
# Encrypt backups before storage
gpg --encrypt --recipient admin@waprep.com backup_file.sql
```

### 6.2 Access Control
- **Limit backup access** to authorized personnel only
- **Use IAM roles** for cloud storage access
- **Audit backup access** regularly

### 6.3 Compliance
- **HIPAA considerations** for student data
- **PCI DSS compliance** for payment data
- **Data retention policies** (7 years for financial records)

## 7. Disaster Recovery Scenarios

### 7.1 Complete System Failure
1. **Restore from cloud backup**
2. **Recreate environment** on new platform
3. **Restore database** and files
4. **Verify functionality** and data integrity

### 7.2 Database Corruption
1. **Stop application**
2. **Restore from latest backup**
3. **Run data integrity checks**
4. **Resume operations**

### 7.3 Partial Data Loss
1. **Identify affected data**
2. **Restore specific tables/records**
3. **Reconcile with external systems** (Stripe)
4. **Notify affected users**

## 8. Maintenance Schedule

### Daily
- Automated database backup
- Backup verification
- Health check monitoring

### Weekly
- Full system backup
- Recovery testing
- Performance monitoring

### Monthly
- Disaster recovery drill
- Backup retention cleanup
- Security audit

### Quarterly
- Recovery procedure updates
- Staff training
- Compliance review

## 9. Contact Information

### Emergency Contacts
- **Primary Admin**: [Admin Name] - [Phone] - [Email]
- **Backup Admin**: [Backup Admin Name] - [Phone] - [Email]
- **Cloud Provider Support**: [Provider] - [Support Number]

### Escalation Procedures
1. **Level 1**: Automated alerts to primary admin
2. **Level 2**: Manual intervention by backup admin
3. **Level 3**: External support engagement
4. **Level 4**: Executive notification

---

**Last Updated**: [Date]
**Next Review**: [Date + 6 months]
**Approved By**: [Admin Name] 