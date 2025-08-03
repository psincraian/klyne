#!/bin/bash

set -euo pipefail

# Configuration
SERVERS="${SERVERS:-}"
CHECK_INTERVAL=30
MAX_FAILURES=3
LOG_FILE="/opt/klyne/logs/health-check.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}${message}${NC}"
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

warn() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}${message}${NC}"
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

error() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}${message}${NC}"
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

# Check single server health
check_server() {
    local server=$1
    local endpoint="http://$server/health"
    
    if curl -f -s --max-time 10 "$endpoint" | grep -q "healthy"; then
        return 0
    else
        return 1
    fi
}

# Check all servers
check_all_servers() {
    local servers_array=($SERVERS)
    local failed_servers=()
    
    for server in "${servers_array[@]}"; do
        if check_server "$server"; then
            log "✓ Server $server is healthy"
        else
            warn "✗ Server $server health check failed"
            failed_servers+=($server)
        fi
    done
    
    if [[ ${#failed_servers[@]} -eq 0 ]]; then
        log "All servers are healthy"
        return 0
    else
        error "Failed servers: ${failed_servers[*]}"
        return 1
    fi
}

# Send simple notification (can be enhanced)
send_notification() {
    local message="$1"
    local severity="${2:-info}"
    
    # Log to file
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$severity] $message" >> "$LOG_FILE" 2>/dev/null || true
    
    # You can add email/webhook notifications here if needed
    # Example: curl -X POST "your-webhook-url" -d "{\"text\":\"$message\"}"
}

# Main monitoring loop
monitor() {
    local failure_count=0
    
    log "Starting health monitoring for servers: $SERVERS"
    log "Check interval: ${CHECK_INTERVAL}s, Max failures: $MAX_FAILURES"
    
    while true; do
        if check_all_servers; then
            if [[ $failure_count -gt 0 ]]; then
                log "Services recovered after $failure_count failures"
                send_notification "Klyne services recovered" "info"
                failure_count=0
            fi
        else
            ((failure_count++))
            
            if [[ $failure_count -ge $MAX_FAILURES ]]; then
                error "Health check failed $failure_count consecutive times!"
                send_notification "Klyne services unhealthy - $failure_count consecutive failures" "critical"
                
                # Reset counter to avoid spam
                failure_count=0
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# One-time check
check_once() {
    log "Performing one-time health check..."
    
    if check_all_servers; then
        log "✅ All services are healthy"
        exit 0
    else
        error "❌ Some services are unhealthy"
        exit 1
    fi
}

# Usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --servers SERVERS    Comma-separated list of server IPs"
    echo "  -c, --check              Perform one-time health check"
    echo "  -m, --monitor            Start continuous monitoring (default)"
    echo "  -i, --interval SECONDS   Check interval in seconds (default: 30)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  SERVERS                  Server IPs (can be set instead of -s)"
    echo ""
    echo "Examples:"
    echo "  $0 -s '1.2.3.4,1.2.3.5' -c"
    echo "  SERVERS='1.2.3.4 1.2.3.5' $0 --monitor"
}

# Parse arguments
MODE="monitor"

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--servers)
            SERVERS="$2"
            shift 2
            ;;
        -c|--check)
            MODE="check"
            shift
            ;;
        -m|--monitor)
            MODE="monitor"
            shift
            ;;
        -i|--interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate
if [[ -z "$SERVERS" ]]; then
    error "SERVERS must be specified. Use -s option or set SERVERS environment variable."
    exit 1
fi

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# Execute based on mode
case $MODE in
    check)
        check_once
        ;;
    monitor)
        monitor
        ;;
    *)
        error "Invalid mode: $MODE"
        exit 1
        ;;
esac