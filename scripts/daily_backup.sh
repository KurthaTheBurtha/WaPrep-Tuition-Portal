#!/bin/bash

# WAPrep Tuition Portal - Daily Backup Script
# This script performs daily backups of the database and critical files

set -e  # Exit on any error

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/daily"
DB_URL="${DATABASE_URL}"
S3_BUCKET="your-waprep-backup-bucket"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Create backup directories
log "Creating backup directories..."
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/files"
mkdir -p "$BACKUP_DIR/config"

# Database backup
log "Starting database backup..."
if [ -n "$DB_URL" ]; then
    # PostgreSQL backup
    pg_dump "$DB_URL" > "$BACKUP_DIR/database/waprep_backup_$DATE.sql"
    
    # Compress the backup
    gzip "$BACKUP_DIR/database/waprep_backup_$DATE.sql"
    
    # Check backup size
    BACKUP_SIZE=$(stat -c%s "$BACKUP_DIR/database/waprep_backup_$DATE.sql.gz")
    if [ "$BACKUP_SIZE" -lt 1000 ]; then
        error "Database backup file is suspiciously small: ${BACKUP_SIZE} bytes"
        exit 1
    fi
    
    log "Database backup completed: ${BACKUP_SIZE} bytes"
else
    error "DATABASE_URL not set"
    exit 1
fi

# File backups
log "Starting file backups..."

# Backup receipts directory if it exists
if [ -d "/app/receipts" ]; then
    tar -czf "$BACKUP_DIR/files/receipts_$DATE.tar.gz" -C /app receipts/
    log "Receipts backup completed"
else
    warning "Receipts directory not found"
fi

# Backup static files if they exist
if [ -d "/app/staticfiles" ]; then
    tar -czf "$BACKUP_DIR/files/static_$DATE.tar.gz" -C /app staticfiles/
    log "Static files backup completed"
else
    warning "Static files directory not found"
fi

# Configuration backup
log "Starting configuration backup..."

# Backup environment variables (if .env exists)
if [ -f "/app/.env" ]; then
    cp /app/.env "$BACKUP_DIR/config/env_$DATE"
    log "Environment variables backed up"
else
    warning ".env file not found"
fi

# Backup Django settings
if [ -f "/app/tuition/settings_production.py" ]; then
    cp /app/tuition/settings_production.py "$BACKUP_DIR/config/settings_production_$DATE.py"
    log "Django settings backed up"
fi

# Upload to cloud storage (if AWS CLI is available)
if command -v aws &> /dev/null; then
    log "Uploading backups to S3..."
    
    # Upload database backup
    aws s3 cp "$BACKUP_DIR/database/waprep_backup_$DATE.sql.gz" "s3://$S3_BUCKET/database/" --quiet
    
    # Upload file backups
    if [ -f "$BACKUP_DIR/files/receipts_$DATE.tar.gz" ]; then
        aws s3 cp "$BACKUP_DIR/files/receipts_$DATE.tar.gz" "s3://$S3_BUCKET/files/" --quiet
    fi
    
    if [ -f "$BACKUP_DIR/files/static_$DATE.tar.gz" ]; then
        aws s3 cp "$BACKUP_DIR/files/static_$DATE.tar.gz" "s3://$S3_BUCKET/files/" --quiet
    fi
    
    # Upload config backups
    if [ -f "$BACKUP_DIR/config/env_$DATE" ]; then
        aws s3 cp "$BACKUP_DIR/config/env_$DATE" "s3://$S3_BUCKET/config/" --quiet
    fi
    
    if [ -f "$BACKUP_DIR/config/settings_production_$DATE.py" ]; then
        aws s3 cp "$BACKUP_DIR/config/settings_production_$DATE.py" "s3://$S3_BUCKET/config/" --quiet
    fi
    
    log "Upload to S3 completed"
else
    warning "AWS CLI not available, skipping cloud upload"
fi

# Cleanup old backups
log "Cleaning up old backups..."
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.py" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "env_*" -mtime +$RETENTION_DAYS -delete

# Cleanup S3 old backups (if AWS CLI available)
if command -v aws &> /dev/null; then
    # Delete old database backups from S3
    aws s3 ls "s3://$S3_BUCKET/database/" | awk '{print $4}' | grep -E "waprep_backup_.*\.sql\.gz$" | while read file; do
        # Extract date from filename
        file_date=$(echo "$file" | sed 's/waprep_backup_\([0-9]\{8\}\)_.*\.sql\.gz/\1/')
        if [ -n "$file_date" ]; then
            # Check if file is older than retention period
            file_timestamp=$(date -d "$file_date" +%s)
            cutoff_timestamp=$(date -d "$RETENTION_DAYS days ago" +%s)
            if [ "$file_timestamp" -lt "$cutoff_timestamp" ]; then
                aws s3 rm "s3://$S3_BUCKET/database/$file" --quiet
                log "Deleted old S3 backup: $file"
            fi
        fi
    done
fi

log "Daily backup completed successfully!"

# Send success notification (if email is configured)
if [ -n "$BACKUP_NOTIFICATION_EMAIL" ]; then
    echo "Daily backup completed successfully at $(date)" | mail -s "WAPrep Backup Success" "$BACKUP_NOTIFICATION_EMAIL"
fi 