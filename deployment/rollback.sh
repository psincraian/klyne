#!/bin/bash

set -euo pipefail

# Configuration
SERVERS="${SERVERS:-}"
ROLLBACK_TAG="${ROLLBACK_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --servers SERVERS    Comma-separated list of server IPs"
    echo "  -t, --tag TAG           Docker image tag to rollback to"
    echo "  -l, --list              List available image tags"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  SERVERS                 Server IPs (can be set instead of -s)"
    echo "  ROLLBACK_TAG           Image tag (can be set instead of -t)"
    echo ""
    echo "Examples:"
    echo "  $0 -s '1.2.3.4,1.2.3.5' -t 'v1.0.0'"
    echo "  SERVERS='1.2.3.4 1.2.3.5' $0 --tag latest"
}

# List available Docker image tags
list_tags() {
    log "Available image tags in registry:"
    
    if command -v gh &> /dev/null; then
        gh api repos/$(gh repo view --json name,owner -q '.owner.login + "/" + .name')/packages/container/klyne-backoffice/versions \
            --jq '.[] | select(.metadata.container.tags | length > 0) | .metadata.container.tags[]' | head -20
    else
        warn "GitHub CLI not available. Please check your container registry manually."
        echo "Example tags: latest, main-abc123, v1.0.0"
    fi
}

# Rollback a single server
rollback_server() {
    local server=$1
    local tag=$2
    
    log "Rolling back server $server to tag: $tag"
    
    # Check if server is reachable
    if ! ssh -o ConnectTimeout=5 deploy@$server "echo 'Server reachable'" &>/dev/null; then
        error "Cannot connect to server $server"
    fi
    
    # Get current running tag for comparison
    local current_tag=$(ssh deploy@$server "cd /opt/klyne && docker compose -f docker-compose.prod.yml images app" | grep app | awk '{print $2}' | cut -d: -f2 || echo "unknown")
    
    log "Current tag: $current_tag"
    log "Rolling back to: $tag"
    
    if [[ "$current_tag" == "$tag" ]]; then
        warn "Server $server is already running tag $tag"
        return 0
    fi
    
    # Create backup before rollback
    log "Creating backup on $server..."
    ssh deploy@$server "
        cd /opt/klyne
        if docker compose -f docker-compose.prod.yml ps postgres | grep -q 'Up'; then
            docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres klyne > backups/rollback_backup_\$(date +%Y%m%d_%H%M%S).sql || true
        fi
    "
    
    # Update environment with new tag
    ssh deploy@$server "
        cd /opt/klyne
        sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=$tag/' .env || echo 'IMAGE_TAG=$tag' >> .env
    "
    
    # Pull the rollback image
    log "Pulling rollback image on $server..."
    ssh deploy@$server "
        cd /opt/klyne
        export IMAGE_TAG=$tag
        docker compose -f docker-compose.prod.yml pull app
    "
    
    # Perform rollback
    log "Performing rollback on $server..."
    ssh deploy@$server "
        cd /opt/klyne
        export IMAGE_TAG=$tag
        docker compose -f docker-compose.prod.yml up -d app
        
        # Clean up old images
        docker image prune -f || true
    "
    
    # Wait for service to start
    sleep 15
    
    # Verify rollback
    if curl -f -s "http://$server/health" > /dev/null 2>&1; then
        log "✓ Rollback successful on $server"
    else
        error "✗ Rollback verification failed on $server"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--servers)
            SERVERS="$2"
            shift 2
            ;;
        -t|--tag)
            ROLLBACK_TAG="$2"
            shift 2
            ;;
        -l|--list)
            list_tags
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate inputs
if [[ -z "$SERVERS" ]]; then
    error "SERVERS must be specified. Use -s option or set SERVERS environment variable."
fi

if [[ -z "$ROLLBACK_TAG" ]]; then
    error "ROLLBACK_TAG must be specified. Use -t option or set ROLLBACK_TAG environment variable."
fi

# Confirm rollback
echo ""
warn "⚠️  ROLLBACK CONFIRMATION ⚠️"
echo "Servers: $SERVERS"
echo "Rollback to tag: $ROLLBACK_TAG"
echo ""
read -p "Are you sure you want to proceed? (yes/NO): " confirm

if [[ "$confirm" != "yes" ]]; then
    log "Rollback cancelled"
    exit 0
fi

# Convert servers string to array
IFS=' ,' read -ra servers_array <<< "$SERVERS"

log "Starting rollback process..."
log "Servers: ${servers_array[*]}"
log "Target tag: $ROLLBACK_TAG"

# Rollback each server
failed_servers=()

for server in "${servers_array[@]}"; do
    if rollback_server "$server" "$ROLLBACK_TAG"; then
        log "✓ Rollback completed on $server"
    else
        error "✗ Rollback failed on $server"
        failed_servers+=($server)
    fi
    
    # Add delay between servers
    if [[ "$server" != "${servers_array[-1]}" ]]; then
        log "Waiting 30 seconds before rolling back next server..."
        sleep 30
    fi
done

# Final status
echo ""
if [[ ${#failed_servers[@]} -eq 0 ]]; then
    log "🎉 Rollback completed successfully on all servers!"
    log "All servers are now running tag: $ROLLBACK_TAG"
else
    error "Rollback failed on servers: ${failed_servers[*]}"
fi