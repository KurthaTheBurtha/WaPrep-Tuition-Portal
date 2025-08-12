#!/bin/bash

# WaPrep Tuition Portal - Backup Script v2.1.0
# Automated backup script for database and files with cloud storage integration

set -e

# Configuration
APP_NAME="waprep-tuition-portal"
BACKUP_DIR="/app/backups"
RETENTION_DAYS=30
COMPRESSION=true
UPLOAD_TO_CLOUD=true
NOTIFY_ON_FAILURE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate prerequisites
validate_prerequisites() {
    log "Validating backup prerequisites..."
    
    # Check required commands
    local required_commands=("pg_dump" "tar" "gzip")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            error "Required command '$cmd' not found. Please install it first."
            exit 1
        fi
    done
    
    # Check environment variables
    if [[ -z "$DATABASE_URL" ]]; then
        error "DATABASE_URL environment variable is required."
        exit 1
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    success "Prerequisites validation completed."
}

# Function to create database backup
create_database_backup() {
    log "Creating database backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local db_backup_file="$BACKUP_DIR/database_backup_$timestamp.sql"
    
    # Extract database connection details from DATABASE_URL
    local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    local db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    local db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    local db_password=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    
    # Set password for pg_dump
    export PGPASSWORD="$db_password"
    
    # Create database backup
    pg_dump -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
        --verbose --clean --no-owner --no-privileges \
        --exclude-table-data='audit_log' \
        --exclude-table-data='system_health' \
        --exclude-table-data='security_event' \
        > "$db_backup_file"
    
    if [[ $? -eq 0 ]]; then
        success "Database backup created: $db_backup_file"
        echo "$db_backup_file"
    else
        error "Database backup failed"
        return 1
    fi
}

# Function to create file backup
create_file_backup() {
    log "Creating file backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local file_backup_file="$BACKUP_DIR/files_backup_$timestamp.tar.gz"
    
    # Create file backup excluding unnecessary directories
    tar -czf "$file_backup_file" \
        --exclude='venv' \
        --exclude='.git' \
        --exclude='logs' \
        --exclude='backups' \
        --exclude='node_modules' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        --exclude='.env' \
        --exclude='.env.local' \
        --exclude='.env.production' \
        .
    
    if [[ $? -eq 0 ]]; then
        success "File backup created: $file_backup_file"
        echo "$file_backup_file"
    else
        error "File backup failed"
        return 1
    fi
}

# Function to create media backup
create_media_backup() {
    log "Creating media backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local media_backup_file="$BACKUP_DIR/media_backup_$timestamp.tar.gz"
    
    # Check if media directory exists
    if [[ -d "media" ]]; then
        tar -czf "$media_backup_file" media/
        
        if [[ $? -eq 0 ]]; then
            success "Media backup created: $media_backup_file"
            echo "$media_backup_file"
        else
            error "Media backup failed"
            return 1
        fi
    else
        warning "Media directory not found, skipping media backup"
    fi
}

# Function to create static files backup
create_static_backup() {
    log "Creating static files backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local static_backup_file="$BACKUP_DIR/static_backup_$timestamp.tar.gz"
    
    # Check if staticfiles directory exists
    if [[ -d "staticfiles" ]]; then
        tar -czf "$static_backup_file" staticfiles/
        
        if [[ $? -eq 0 ]]; then
            success "Static files backup created: $static_backup_file"
            echo "$static_backup_file"
        else
            error "Static files backup failed"
            return 1
        fi
    else
        warning "Staticfiles directory not found, skipping static backup"
    fi
}

# Function to upload to cloud storage
upload_to_cloud() {
    local backup_file="$1"
    
    if [[ "$UPLOAD_TO_CLOUD" == "true" ]]; then
        log "Uploading backup to cloud storage..."
        
        # Check if AWS CLI is available
        if command_exists "aws"; then
            local s3_bucket="${AWS_STORAGE_BUCKET_NAME:-waprep-tuition-backups}"
            local s3_key="backups/$(basename "$backup_file")"
            
            aws s3 cp "$backup_file" "s3://$s3_bucket/$s3_key" \
                --region "${AWS_S3_REGION_NAME:-us-west-2}" \
                --storage-class STANDARD_IA
            
            if [[ $? -eq 0 ]]; then
                success "Backup uploaded to S3: s3://$s3_bucket/$s3_key"
            else
                error "Failed to upload backup to S3"
                return 1
            fi
        else
            warning "AWS CLI not found, skipping cloud upload"
        fi
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Remove backups older than retention period
    find "$BACKUP_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    # Remove empty directories
    find "$BACKUP_DIR" -type d -empty -delete
    
    success "Old backups cleaned up (retention: $RETENTION_DAYS days)"
}

# Function to verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    log "Verifying backup integrity: $backup_file"
    
    if [[ "$backup_file" == *.tar.gz ]]; then
        # Verify tar.gz file
        if tar -tzf "$backup_file" > /dev/null 2>&1; then
            success "Backup verification passed: $backup_file"
            return 0
        else
            error "Backup verification failed: $backup_file"
            return 1
        fi
    elif [[ "$backup_file" == *.sql ]]; then
        # Verify SQL file (basic check)
        if [[ -s "$backup_file" ]]; then
            success "Backup verification passed: $backup_file"
            return 0
        else
            error "Backup verification failed: $backup_file"
            return 1
        fi
    fi
}

# Function to send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification if configured
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        echo "Backup $status: $message" | mail -s "WaPrep Tuition Portal Backup $status" "$NOTIFICATION_EMAIL"
    fi
    
    # Send Slack notification if configured
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Backup $status: $message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
}

# Function to create backup summary
create_backup_summary() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local summary_file="$BACKUP_DIR/backup_summary_$timestamp.txt"
    
    cat > "$summary_file" << EOF
WaPrep Tuition Portal - Backup Summary
=====================================
Backup Date: $(date)
Backup Type: Full System Backup
Environment: ${ENVIRONMENT:-production}

Backup Files:
$(ls -la "$BACKUP_DIR"/*_$timestamp.* 2>/dev/null || echo "No backup files found")

Database Information:
- Database: $(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
- Host: $(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
- Port: $(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

Backup Configuration:
- Retention Period: $RETENTION_DAYS days
- Compression: $COMPRESSION
- Cloud Upload: $UPLOAD_TO_CLOUD
- Backup Directory: $BACKUP_DIR

System Information:
- Disk Usage: $(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}')
- Available Space: $(df -h "$BACKUP_DIR" | tail -1 | awk '{print $4}')
EOF
    
    success "Backup summary created: $summary_file"
}

# Main backup function
main() {
    log "Starting backup process for $APP_NAME..."
    
    # Start timer
    local start_time=$(date +%s)
    
    # Validate prerequisites
    validate_prerequisites
    
    # Initialize backup files array
    local backup_files=()
    
    # Create database backup
    if db_backup_file=$(create_database_backup); then
        backup_files+=("$db_backup_file")
    else
        error "Database backup failed"
        send_notification "FAILED" "Database backup failed"
        exit 1
    fi
    
    # Create file backup
    if file_backup_file=$(create_file_backup); then
        backup_files+=("$file_backup_file")
    else
        error "File backup failed"
        send_notification "FAILED" "File backup failed"
        exit 1
    fi
    
    # Create media backup
    if media_backup_file=$(create_media_backup); then
        backup_files+=("$media_backup_file")
    fi
    
    # Create static files backup
    if static_backup_file=$(create_static_backup); then
        backup_files+=("$static_backup_file")
    fi
    
    # Verify all backups
    local verification_failed=false
    for backup_file in "${backup_files[@]}"; do
        if ! verify_backup "$backup_file"; then
            verification_failed=true
        fi
    done
    
    if [[ "$verification_failed" == "true" ]]; then
        error "Backup verification failed"
        send_notification "FAILED" "Backup verification failed"
        exit 1
    fi
    
    # Upload backups to cloud storage
    for backup_file in "${backup_files[@]}"; do
        upload_to_cloud "$backup_file"
    done
    
    # Clean up old backups
    cleanup_old_backups
    
    # Create backup summary
    create_backup_summary
    
    # Calculate backup time
    local end_time=$(date +%s)
    local backup_time=$((end_time - start_time))
    
    success "Backup completed successfully in ${backup_time} seconds!"
    
    # Send success notification
    send_notification "SUCCESS" "Backup completed successfully in ${backup_time} seconds"
    
    # Display backup summary
    echo ""
    echo "=== Backup Summary ==="
    echo "Application: $APP_NAME"
    echo "Duration: ${backup_time} seconds"
    echo "Files Created: ${#backup_files[@]}"
    echo "Status: SUCCESS"
    echo "====================="
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --no-cloud          Skip cloud storage upload"
        echo "  --no-cleanup        Skip cleanup of old backups"
        echo "  --retention DAYS    Set retention period in days (default: 30)"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL        Database connection string"
        echo "  AWS_STORAGE_BUCKET_NAME  S3 bucket for backups"
        echo "  AWS_S3_REGION_NAME  AWS region for S3"
        echo "  NOTIFICATION_EMAIL  Email for backup notifications"
        echo "  SLACK_WEBHOOK_URL   Slack webhook URL for notifications"
        exit 0
        ;;
    --no-cloud)
        UPLOAD_TO_CLOUD=false
        shift
        ;;
    --no-cleanup)
        CLEANUP_OLD_BACKUPS=false
        shift
        ;;
    --retention)
        RETENTION_DAYS="$2"
        shift 2
        ;;
esac

# Run main backup
main "$@"
