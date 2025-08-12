#!/bin/bash

# WaPrep Tuition Portal - Monitoring Script v2.1.0
# Comprehensive monitoring script for system health, performance, and alerting

set -e

# Configuration
APP_NAME="waprep-tuition-portal"
MONITORING_INTERVAL=300  # 5 minutes
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=85
ALERT_THRESHOLD_DISK=90
ALERT_THRESHOLD_RESPONSE_TIME=5
HEALTH_CHECK_URL="http://localhost:8000/health/"
LOG_FILE="/app/logs/monitoring.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # CPU Usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        warning "High CPU usage: ${cpu_usage}%"
        send_alert "HIGH_CPU" "CPU usage is ${cpu_usage}% (threshold: ${ALERT_THRESHOLD_CPU}%)"
    else
        log "CPU usage: ${cpu_usage}% (OK)"
    fi
    
    # Memory Usage
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        warning "High memory usage: ${memory_usage}%"
        send_alert "HIGH_MEMORY" "Memory usage is ${memory_usage}% (threshold: ${ALERT_THRESHOLD_MEMORY}%)"
    else
        log "Memory usage: ${memory_usage}% (OK)"
    fi
    
    # Disk Usage
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    if (( disk_usage > ALERT_THRESHOLD_DISK )); then
        warning "High disk usage: ${disk_usage}%"
        send_alert "HIGH_DISK" "Disk usage is ${disk_usage}% (threshold: ${ALERT_THRESHOLD_DISK}%)"
    else
        log "Disk usage: ${disk_usage}% (OK)"
    fi
    
    # Load Average
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local load_threshold=$(echo "$cpu_cores * 0.8" | bc -l)
    
    if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
        warning "High load average: ${load_avg} (threshold: ${load_threshold})"
        send_alert "HIGH_LOAD" "Load average is ${load_avg} (threshold: ${load_threshold})"
    else
        log "Load average: ${load_avg} (OK)"
    fi
}

# Function to check application health
check_application_health() {
    log "Checking application health..."
    
    # Check if application is responding
    local start_time=$(date +%s.%N)
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" --max-time 10)
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc -l)
    
    if [[ "$response_code" == "200" ]]; then
        log "Application health check: OK (Response time: ${response_time}s)"
        
        # Check response time threshold
        if (( $(echo "$response_time > $ALERT_THRESHOLD_RESPONSE_TIME" | bc -l) )); then
            warning "Slow response time: ${response_time}s"
            send_alert "SLOW_RESPONSE" "Response time is ${response_time}s (threshold: ${ALERT_THRESHOLD_RESPONSE_TIME}s)"
        fi
    else
        error "Application health check failed: HTTP $response_code"
        send_alert "HEALTH_CHECK_FAILED" "Application health check failed with HTTP $response_code"
        return 1
    fi
}

# Function to check database connectivity
check_database_connectivity() {
    log "Checking database connectivity..."
    
    if [[ -z "$DATABASE_URL" ]]; then
        warning "DATABASE_URL not set, skipping database check"
        return 0
    fi
    
    # Extract database connection details
    local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    local db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    local db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    local db_password=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    
    # Set password for psql
    export PGPASSWORD="$db_password"
    
    # Test database connection
    if psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "SELECT 1;" > /dev/null 2>&1; then
        log "Database connectivity: OK"
    else
        error "Database connectivity failed"
        send_alert "DATABASE_CONNECTION_FAILED" "Database connection failed"
        return 1
    fi
}

# Function to check service status
check_service_status() {
    log "Checking service status..."
    
    # Check Docker containers if using Docker
    if command_exists "docker" && [[ -f "docker-compose.yml" ]]; then
        local containers=("waprep-tuition-web" "waprep-tuition-db" "waprep-tuition-redis" "waprep-tuition-nginx")
        
        for container in "${containers[@]}"; do
            if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container"; then
                local status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "$container" | awk '{print $2}')
                log "Container $container: $status"
            else
                error "Container $container is not running"
                send_alert "CONTAINER_DOWN" "Container $container is not running"
            fi
        done
    else
        # Check systemd services
        if command_exists "systemctl"; then
            local services=("waprep-tuition" "nginx" "postgresql")
            
            for service in "${services[@]}"; do
                if systemctl is-active --quiet "$service"; then
                    log "Service $service: Active"
                else
                    error "Service $service is not running"
                    send_alert "SERVICE_DOWN" "Service $service is not running"
                fi
            done
        fi
    fi
}

# Function to check log files
check_log_files() {
    log "Checking log files..."
    
    local log_files=("/app/logs/error.log" "/app/logs/access.log" "/var/log/nginx/error.log")
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            # Check for recent errors (last 5 minutes)
            local recent_errors=$(find "$log_file" -mmin -5 -exec grep -i "error\|exception\|traceback" {} \; | wc -l)
            
            if [[ $recent_errors -gt 0 ]]; then
                warning "Recent errors in $log_file: $recent_errors"
                send_alert "LOG_ERRORS" "Found $recent_errors recent errors in $log_file"
            else
                log "Log file $log_file: No recent errors"
            fi
        else
            warning "Log file not found: $log_file"
        fi
    done
}

# Function to check disk space
check_disk_space() {
    log "Checking disk space..."
    
    # Check main disk
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    local available_space=$(df / | tail -1 | awk '{print $4}')
    
    log "Available disk space: ${available_space}KB"
    
    # Check backup directory
    if [[ -d "/app/backups" ]]; then
        local backup_usage=$(du -sh /app/backups | cut -f1)
        log "Backup directory size: $backup_usage"
        
        # Check if backup directory is getting full
        local backup_percentage=$(df /app/backups | tail -1 | awk '{print $5}' | cut -d'%' -f1)
        if (( backup_percentage > 80 )); then
            warning "Backup directory is getting full: ${backup_percentage}%"
            send_alert "BACKUP_SPACE_LOW" "Backup directory is ${backup_percentage}% full"
        fi
    fi
}

# Function to check network connectivity
check_network_connectivity() {
    log "Checking network connectivity..."
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        log "Internet connectivity: OK"
    else
        error "Internet connectivity failed"
        send_alert "NETWORK_DOWN" "Internet connectivity failed"
    fi
    
    # Check DNS resolution
    if nslookup google.com > /dev/null 2>&1; then
        log "DNS resolution: OK"
    else
        error "DNS resolution failed"
        send_alert "DNS_FAILED" "DNS resolution failed"
    fi
}

# Function to check SSL certificate
check_ssl_certificate() {
    log "Checking SSL certificate..."
    
    if command_exists "openssl"; then
        local domain="waprep-tuition.com"
        local cert_info=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates)
        
        if [[ $? -eq 0 ]]; then
            local expiry_date=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
            local expiry_timestamp=$(date -d "$expiry_date" +%s)
            local current_timestamp=$(date +%s)
            local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [[ $days_until_expiry -lt 30 ]]; then
                warning "SSL certificate expires in $days_until_expiry days"
                send_alert "SSL_EXPIRING" "SSL certificate expires in $days_until_expiry days"
            else
                log "SSL certificate: Valid for $days_until_expiry days"
            fi
        else
            error "SSL certificate check failed"
            send_alert "SSL_CHECK_FAILED" "SSL certificate check failed"
        fi
    else
        warning "OpenSSL not available, skipping SSL check"
    fi
}

# Function to send alerts
send_alert() {
    local alert_type="$1"
    local message="$2"
    
    log "ALERT [$alert_type]: $message"
    
    # Send email alert if configured
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "Alert: $message" | mail -s "WaPrep Tuition Portal Alert: $alert_type" "$ALERT_EMAIL"
    fi
    
    # Send Slack alert if configured
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        local color="danger"
        if [[ "$alert_type" == "WARNING" ]]; then
            color="warning"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"WaPrep Tuition Portal Alert\",
                    \"text\": \"$message\",
                    \"fields\": [{
                        \"title\": \"Alert Type\",
                        \"value\": \"$alert_type\",
                        \"short\": true
                    }, {
                        \"title\": \"Timestamp\",
                        \"value\": \"$(date)\",
                        \"short\": true
                    }]
                }]
            }" \
            "$SLACK_WEBHOOK_URL"
    fi
}

# Function to generate monitoring report
generate_monitoring_report() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="/app/logs/monitoring_report_$timestamp.txt"
    
    cat > "$report_file" << EOF
WaPrep Tuition Portal - Monitoring Report
========================================
Generated: $(date)
Environment: ${ENVIRONMENT:-production}

System Resources:
- CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%
- Memory Usage: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%
- Disk Usage: $(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)%
- Load Average: $(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')

Application Status:
- Health Check: $(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" --max-time 10)
- Response Time: $(curl -s -w "%{time_total}" -o /dev/null "$HEALTH_CHECK_URL" --max-time 10)s

Service Status:
$(if command_exists "docker" && [[ -f "docker-compose.yml" ]]; then
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    echo "Docker not available or docker-compose.yml not found"
fi)

Recent Log Errors:
$(find /app/logs -name "*.log" -mmin -5 -exec grep -i "error\|exception\|traceback" {} \; | tail -10)

Network Status:
- Internet: $(ping -c 1 8.8.8.8 > /dev/null 2>&1 && echo "OK" || echo "FAILED")
- DNS: $(nslookup google.com > /dev/null 2>&1 && echo "OK" || echo "FAILED")
EOF
    
    log "Monitoring report generated: $report_file"
}

# Function to cleanup old reports
cleanup_old_reports() {
    log "Cleaning up old monitoring reports..."
    
    # Remove reports older than 7 days
    find /app/logs -name "monitoring_report_*.txt" -mtime +7 -delete
    
    # Remove old log files (keep last 30 days)
    find /app/logs -name "*.log" -mtime +30 -delete
    
    success "Old reports and logs cleaned up"
}

# Main monitoring function
main() {
    log "Starting monitoring for $APP_NAME..."
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Run all monitoring checks
    check_system_resources
    check_application_health
    check_database_connectivity
    check_service_status
    check_log_files
    check_disk_space
    check_network_connectivity
    check_ssl_certificate
    
    # Generate monitoring report
    generate_monitoring_report
    
    # Cleanup old reports
    cleanup_old_reports
    
    success "Monitoring completed successfully"
}

# Continuous monitoring function
continuous_monitoring() {
    log "Starting continuous monitoring (interval: ${MONITORING_INTERVAL}s)..."
    
    while true; do
        main
        sleep "$MONITORING_INTERVAL"
    done
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --continuous, -c    Run continuous monitoring"
        echo "  --interval SECONDS  Set monitoring interval (default: 300)"
        echo "  --report-only       Generate report only"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL        Database connection string"
        echo "  ALERT_EMAIL         Email for monitoring alerts"
        echo "  SLACK_WEBHOOK_URL   Slack webhook URL for alerts"
        exit 0
        ;;
    --continuous|-c)
        continuous_monitoring
        ;;
    --interval)
        MONITORING_INTERVAL="$2"
        shift 2
        continuous_monitoring
        ;;
    --report-only)
        generate_monitoring_report
        cleanup_old_reports
        exit 0
        ;;
esac

# Run main monitoring
main "$@"
