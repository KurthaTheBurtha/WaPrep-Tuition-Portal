#!/bin/bash

# WaPrep Tuition Portal - Deployment Script v2.1.0
# This script automates the deployment process for the tuition management system

set -e  # Exit on any error

# Configuration
APP_NAME="waprep-tuition-portal"
APP_VERSION="2.1.0"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
BACKUP_BEFORE_DEPLOY=true
HEALTH_CHECK_ENABLED=true
ROLLBACK_ON_FAILURE=true

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
    log "Validating deployment prerequisites..."
    
    # Check required commands
    local required_commands=("python3" "pip" "git" "docker" "docker-compose")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            error "Required command '$cmd' not found. Please install it first."
            exit 1
        fi
    done
    
    # Check if we're in the correct directory
    if [[ ! -f "manage.py" ]]; then
        error "manage.py not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Check environment variables
    if [[ -z "$DATABASE_URL" ]]; then
        error "DATABASE_URL environment variable is required."
        exit 1
    fi
    
    if [[ -z "$SECRET_KEY" ]]; then
        error "SECRET_KEY environment variable is required."
        exit 1
    fi
    
    success "Prerequisites validation completed."
}

# Function to create backup
create_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" == "true" ]]; then
        log "Creating database backup before deployment..."
        
        local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Database backup
        if command_exists "pg_dump"; then
            pg_dump "$DATABASE_URL" > "$backup_dir/database_backup.sql"
            success "Database backup created: $backup_dir/database_backup.sql"
        else
            warning "pg_dump not found. Skipping database backup."
        fi
        
        # File backup
        tar -czf "$backup_dir/files_backup.tar.gz" --exclude='venv' --exclude='.git' --exclude='logs' .
        success "Files backup created: $backup_dir/files_backup.tar.gz"
        
        # Keep only last 5 backups
        find backups -maxdepth 1 -type d -name "*_*" | sort | head -n -5 | xargs -r rm -rf
    fi
}

# Function to update code
update_code() {
    log "Updating application code..."
    
    # Pull latest changes
    if [[ -d ".git" ]]; then
        git fetch origin
        git reset --hard origin/main
        success "Code updated from git repository."
    else
        warning "Not a git repository. Skipping code update."
    fi
}

# Function to install dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        success "Virtual environment created."
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    success "Dependencies installed successfully."
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    source venv/bin/activate
    
    # Check for pending migrations
    local pending_migrations=$(python manage.py showmigrations --list | grep -c "\[ \]" || true)
    
    if [[ $pending_migrations -gt 0 ]]; then
        log "Found $pending_migrations pending migration(s)."
        
        # Run migrations
        python manage.py migrate --noinput
        
        success "Database migrations completed."
    else
        log "No pending migrations found."
    fi
}

# Function to collect static files
collect_static() {
    log "Collecting static files..."
    
    source venv/bin/activate
    
    # Collect static files
    python manage.py collectstatic --noinput --clear
    
    success "Static files collected successfully."
}

# Function to restart services
restart_services() {
    log "Restarting application services..."
    
    # Restart using systemd if available
    if command_exists "systemctl"; then
        sudo systemctl restart waprep-tuition || true
        success "Services restarted via systemd."
    else
        # Restart using docker-compose if available
        if [[ -f "docker-compose.yml" ]]; then
            docker-compose down
            docker-compose up -d
            success "Services restarted via docker-compose."
        else
            warning "No service manager found. Please restart services manually."
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

# Function to rollback deployment
rollback_deployment() {
    if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
        warning "Rolling back deployment..."
        
        # Find the most recent backup
        local latest_backup=$(find backups -maxdepth 1 -type d -name "*_*" | sort | tail -n 1)
        
        if [[ -n "$latest_backup" ]]; then
            log "Rolling back to backup: $latest_backup"
            
            # Restore files
            tar -xzf "$latest_backup/files_backup.tar.gz" --strip-components=1
            
            # Restore database if backup exists
            if [[ -f "$latest_backup/database_backup.sql" ]]; then
                psql "$DATABASE_URL" < "$latest_backup/database_backup.sql"
            fi
            
            # Restart services
            restart_services
            
            success "Rollback completed successfully."
        else
            error "No backup found for rollback."
        fi
    fi
}

# Function to send deployment notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification if configured
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        echo "Deployment $status: $message" | mail -s "WaPrep Tuition Portal Deployment $status" "$NOTIFICATION_EMAIL"
    fi
    
    # Send Slack notification if configured
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Deployment $status: $message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
}

# Main deployment function
main() {
    log "Starting deployment of $APP_NAME v$APP_VERSION to $DEPLOYMENT_ENV environment..."
    
    # Start timer
    local start_time=$(date +%s)
    
    # Validate prerequisites
    validate_prerequisites
    
    # Create backup
    create_backup
    
    # Update code
    update_code
    
    # Install dependencies
    install_dependencies
    
    # Run migrations
    run_migrations
    
    # Collect static files
    collect_static
    
    # Restart services
    restart_services
    
    # Perform health check
    if ! perform_health_check; then
        error "Deployment failed during health check."
        rollback_deployment
        send_notification "FAILED" "Health check failed after deployment"
        exit 1
    fi
    
    # Calculate deployment time
    local end_time=$(date +%s)
    local deployment_time=$((end_time - start_time))
    
    success "Deployment completed successfully in ${deployment_time} seconds!"
    
    # Send success notification
    send_notification "SUCCESS" "Deployment completed successfully in ${deployment_time} seconds"
    
    # Display deployment summary
    echo ""
    echo "=== Deployment Summary ==="
    echo "Application: $APP_NAME"
    echo "Version: $APP_VERSION"
    echo "Environment: $DEPLOYMENT_ENV"
    echo "Duration: ${deployment_time} seconds"
    echo "Status: SUCCESS"
    echo "========================"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --no-backup         Skip database backup before deployment"
        echo "  --no-health-check   Skip health check after deployment"
        echo "  --no-rollback       Disable automatic rollback on failure"
        echo "  --env ENVIRONMENT   Set deployment environment (default: production)"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL        Database connection string"
        echo "  SECRET_KEY          Django secret key"
        echo "  NOTIFICATION_EMAIL  Email for deployment notifications"
        echo "  SLACK_WEBHOOK_URL   Slack webhook URL for notifications"
        exit 0
        ;;
    --no-backup)
        BACKUP_BEFORE_DEPLOY=false
        shift
        ;;
    --no-health-check)
        HEALTH_CHECK_ENABLED=false
        shift
        ;;
    --no-rollback)
        ROLLBACK_ON_FAILURE=false
        shift
        ;;
    --env)
        DEPLOYMENT_ENV="$2"
        shift 2
        ;;
esac

# Run main deployment
main "$@"
