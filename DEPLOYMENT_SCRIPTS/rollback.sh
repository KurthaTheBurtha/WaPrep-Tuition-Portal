#!/bin/bash

# WaPrep Tuition Portal - Rollback Script v2.1.0
# Safe rollback script for reverting to previous application versions

set -e

# Configuration
APP_NAME="waprep-tuition-portal"
BACKUP_DIR="/app/backups"
ROLLBACK_TIMEOUT=300
HEALTH_CHECK_ENABLED=true
NOTIFY_ON_ROLLBACK=true

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
    log "Validating rollback prerequisites..."
    
    # Check required commands
    local required_commands=("psql" "tar" "docker-compose")
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
    
    # Check if backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    success "Prerequisites validation completed."
}

# Function to list available backups
list_backups() {
    log "Available backups:"
    echo ""
    
    local backups=()
    while IFS= read -r -d '' file; do
        backups+=("$file")
    done < <(find "$BACKUP_DIR" -name "*.sql" -print0 | sort -z)
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        error "No database backups found in $BACKUP_DIR"
        exit 1
    fi
    
    echo "Database Backups:"
    for i in "${!backups[@]}"; do
        local filename=$(basename "${backups[$i]}")
        local timestamp=$(echo "$filename" | sed 's/database_backup_\(.*\)\.sql/\1/')
        local size=$(du -h "${backups[$i]}" | cut -f1)
        echo "  $((i+1)). $filename ($size) - $timestamp"
    done
    
    echo ""
    echo "File Backups:"
    local file_backups=()
    while IFS= read -r -d '' file; do
        file_backups+=("$file")
    done < <(find "$BACKUP_DIR" -name "files_backup_*.tar.gz" -print0 | sort -z)
    
    for i in "${!file_backups[@]}"; do
        local filename=$(basename "${file_backups[$i]}")
        local timestamp=$(echo "$filename" | sed 's/files_backup_\(.*\)\.tar\.gz/\1/')
        local size=$(du -h "${file_backups[$i]}" | cut -f1)
        echo "  $((i+1)). $filename ($size) - $timestamp"
    done
}

# Function to select backup
select_backup() {
    local backup_type="$1"
    
    if [[ -z "$BACKUP_SELECTION" ]]; then
        log "Please select a $backup_type backup to rollback to:"
        read -p "Enter backup number: " backup_number
        
        if [[ ! "$backup_number" =~ ^[0-9]+$ ]]; then
            error "Invalid backup number"
            exit 1
        fi
    else
        backup_number="$BACKUP_SELECTION"
    fi
    
    local backups=()
    if [[ "$backup_type" == "database" ]]; then
        while IFS= read -r -d '' file; do
            backups+=("$file")
        done < <(find "$BACKUP_DIR" -name "*.sql" -print0 | sort -z)
    else
        while IFS= read -r -d '' file; do
            backups+=("$file")
        done < <(find "$BACKUP_DIR" -name "files_backup_*.tar.gz" -print0 | sort -z)
    fi
    
    if [[ $backup_number -lt 1 || $backup_number -gt ${#backups[@]} ]]; then
        error "Invalid backup number. Please select between 1 and ${#backups[@]}"
        exit 1
    fi
    
    echo "${backups[$((backup_number-1))]}"
}

# Function to create pre-rollback backup
create_pre_rollback_backup() {
    log "Creating pre-rollback backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local pre_rollback_dir="$BACKUP_DIR/pre_rollback_$timestamp"
    mkdir -p "$pre_rollback_dir"
    
    # Database backup
    if command_exists "pg_dump"; then
        local db_backup_file="$pre_rollback_dir/current_database.sql"
        pg_dump "$DATABASE_URL" > "$db_backup_file"
        success "Pre-rollback database backup created: $db_backup_file"
    fi
    
    # File backup
    local file_backup_file="$pre_rollback_dir/current_files.tar.gz"
    tar -czf "$file_backup_file" --exclude='venv' --exclude='.git' --exclude='logs' --exclude='backups' .
    success "Pre-rollback file backup created: $file_backup_file"
    
    echo "$pre_rollback_dir"
}

# Function to stop services
stop_services() {
    log "Stopping application services..."
    
    # Stop using docker-compose if available
    if [[ -f "docker-compose.yml" ]]; then
        docker-compose down
        success "Services stopped via docker-compose"
    else
        # Stop using systemd if available
        if command_exists "systemctl"; then
            sudo systemctl stop waprep-tuition || true
            success "Services stopped via systemd"
        else
            warning "No service manager found. Please stop services manually."
        fi
    fi
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    log "Restoring database from backup: $backup_file"
    
    # Extract database connection details
    local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    local db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    local db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    local db_password=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    
    # Set password for psql
    export PGPASSWORD="$db_password"
    
    # Restore database
    psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" < "$backup_file"
    
    if [[ $? -eq 0 ]]; then
        success "Database restored successfully"
    else
        error "Database restoration failed"
        return 1
    fi
}

# Function to restore files
restore_files() {
    local backup_file="$1"
    
    log "Restoring files from backup: $backup_file"
    
    # Create temporary directory for extraction
    local temp_dir=$(mktemp -d)
    
    # Extract backup
    tar -xzf "$backup_file" -C "$temp_dir"
    
    if [[ $? -eq 0 ]]; then
        # Copy files back to application directory
        cp -r "$temp_dir"/* .
        success "Files restored successfully"
    else
        error "File restoration failed"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Clean up temporary directory
    rm -rf "$temp_dir"
}

# Function to start services
start_services() {
    log "Starting application services..."
    
    # Start using docker-compose if available
    if [[ -f "docker-compose.yml" ]]; then
        docker-compose up -d
        success "Services started via docker-compose"
    else
        # Start using systemd if available
        if command_exists "systemctl"; then
            sudo systemctl start waprep-tuition || true
            success "Services started via systemd"
        else
            warning "No service manager found. Please start services manually."
        fi
    fi
}

# Function to perform health check
perform_health_check() {
    if [[ "$HEALTH_CHECK_ENABLED" == "true" ]]; then
        log "Performing health check..."
        
        # Wait for services to start
        sleep 10
        
        # Check if application is responding
        local max_attempts=30
        local attempt=1
        
        while [[ $attempt -le $max_attempts ]]; do
            if curl -f -s http://localhost:8000/health/ > /dev/null 2>&1; then
                success "Health check passed. Application is responding."
                return 0
            fi
            
            log "Health check attempt $attempt/$max_attempts failed. Retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        done
        
        error "Health check failed after $max_attempts attempts."
        return 1
    fi
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # Run migrations
    python manage.py migrate --noinput
    
    if [[ $? -eq 0 ]]; then
        success "Database migrations completed"
    else
        error "Database migrations failed"
        return 1
    fi
}

# Function to collect static files
collect_static() {
    log "Collecting static files..."
    
    # Activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # Collect static files
    python manage.py collectstatic --noinput --clear
    
    if [[ $? -eq 0 ]]; then
        success "Static files collected successfully"
    else
        error "Static file collection failed"
        return 1
    fi
}

# Function to send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification if configured
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        echo "Rollback $status: $message" | mail -s "WaPrep Tuition Portal Rollback $status" "$NOTIFICATION_EMAIL"
    fi
    
    # Send Slack notification if configured
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Rollback $status: $message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
}

# Function to confirm rollback
confirm_rollback() {
    local db_backup="$1"
    local file_backup="$2"
    
    echo ""
    echo "=== Rollback Confirmation ==="
    echo "Database Backup: $(basename "$db_backup")"
    echo "File Backup: $(basename "$file_backup")"
    echo ""
    echo "WARNING: This will restore the application to a previous state."
    echo "All current data and changes will be lost."
    echo ""
    
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -p "Are you sure you want to proceed with the rollback? (yes/no): " confirmation
        
        if [[ "$confirmation" != "yes" ]]; then
            log "Rollback cancelled by user"
            exit 0
        fi
    fi
}

# Main rollback function
main() {
    log "Starting rollback process for $APP_NAME..."
    
    # Start timer
    local start_time=$(date +%s)
    
    # Validate prerequisites
    validate_prerequisites
    
    # List available backups
    list_backups
    
    # Select backups
    local db_backup=$(select_backup "database")
    local file_backup=$(select_backup "files")
    
    # Confirm rollback
    confirm_rollback "$db_backup" "$file_backup"
    
    # Create pre-rollback backup
    local pre_rollback_dir=$(create_pre_rollback_backup)
    
    # Stop services
    stop_services
    
    # Restore database
    if ! restore_database "$db_backup"; then
        error "Database rollback failed"
        send_notification "FAILED" "Database rollback failed"
        exit 1
    fi
    
    # Restore files
    if ! restore_files "$file_backup"; then
        error "File rollback failed"
        send_notification "FAILED" "File rollback failed"
        exit 1
    fi
    
    # Run migrations
    if ! run_migrations; then
        error "Migration failed after rollback"
        send_notification "FAILED" "Migration failed after rollback"
        exit 1
    fi
    
    # Collect static files
    if ! collect_static; then
        error "Static file collection failed after rollback"
        send_notification "FAILED" "Static file collection failed after rollback"
        exit 1
    fi
    
    # Start services
    start_services
    
    # Perform health check
    if ! perform_health_check; then
        error "Health check failed after rollback"
        send_notification "FAILED" "Health check failed after rollback"
        exit 1
    fi
    
    # Calculate rollback time
    local end_time=$(date +%s)
    local rollback_time=$((end_time - start_time))
    
    success "Rollback completed successfully in ${rollback_time} seconds!"
    
    # Send success notification
    send_notification "SUCCESS" "Rollback completed successfully in ${rollback_time} seconds"
    
    # Display rollback summary
    echo ""
    echo "=== Rollback Summary ==="
    echo "Application: $APP_NAME"
    echo "Duration: ${rollback_time} seconds"
    echo "Database Backup: $(basename "$db_backup")"
    echo "File Backup: $(basename "$file_backup")"
    echo "Pre-rollback Backup: $(basename "$pre_rollback_dir")"
    echo "Status: SUCCESS"
    echo "======================="
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --backup NUMBER     Specify backup number to rollback to"
        echo "  --no-health-check   Skip health check after rollback"
        echo "  --auto-confirm      Skip confirmation prompt"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL        Database connection string"
        echo "  NOTIFICATION_EMAIL  Email for rollback notifications"
        echo "  SLACK_WEBHOOK_URL   Slack webhook URL for notifications"
        exit 0
        ;;
    --backup)
        BACKUP_SELECTION="$2"
        shift 2
        ;;
    --no-health-check)
        HEALTH_CHECK_ENABLED=false
        shift
        ;;
    --auto-confirm)
        AUTO_CONFIRM=true
        shift
        ;;
esac

# Run main rollback
main "$@"
