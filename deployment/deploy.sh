#!/bin/bash

set -euo pipefail

# Configuration
SERVERS="${SERVERS:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
SECRET_KEY="${SECRET_KEY:-}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
HEALTH_CHECK_TIMEOUT=60
HEALTH_CHECK_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
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

# Check if required variables are set
check_requirements() {
    if [[ -z "$SERVERS" ]]; then
        error "SERVERS environment variable is required"
    fi
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        error "POSTGRES_PASSWORD environment variable is required"
    fi
    
    if [[ -z "$SECRET_KEY" ]]; then
        error "SECRET_KEY environment variable is required"
    fi
}

# Check if server is healthy
check_health() {
    local server=$1
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=1
    
    log "Checking health of $server..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://$server/health" > /dev/null 2>&1; then
            log "✓ Server $server is healthy"
            return 0
        fi
        
        warn "Health check $attempt/$max_attempts failed for $server, retrying in ${HEALTH_CHECK_INTERVAL}s..."
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
    
    error "✗ Server $server failed health checks after $max_attempts attempts"
}

# Deploy to a single server
deploy_to_server() {
    local server=$1
    local is_first_server=$2
    
    log "Starting deployment to $server (image: $IMAGE_TAG)"
    
    # Create deployment directory structure
    ssh deploy@$server "mkdir -p /opt/klyne/{ssl,backups,logs,config}"
    
    # Copy docker-compose configuration
    scp deployment/docker-compose.prod.yml deploy@$server:/opt/klyne/
    scp deployment/nginx.conf deploy@$server:/opt/klyne/
    
    # Create environment file
    ssh deploy@$server "cat > /opt/klyne/.env << EOF
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
POSTGRES_DB=klyne
POSTGRES_USER=postgres
IMAGE_TAG=$IMAGE_TAG
EOF"
    
    # Setup PostgreSQL data directory and SSL on first server only
    if [[ "$is_first_server" == "true" ]]; then
        log "Setting up PostgreSQL and SSL on primary server $server"
        
        # Mount PostgreSQL volume if not already mounted
        ssh deploy@$server "
            if ! mountpoint -q /opt/klyne/postgres_data; then
                sudo mkdir -p /opt/klyne/postgres_data
                if lsblk | grep -q 'sdb'; then
                    sudo mkfs.ext4 -F /dev/sdb || true
                    echo '/dev/sdb /opt/klyne/postgres_data ext4 defaults 0 2' | sudo tee -a /etc/fstab
                    sudo mount /dev/sdb /opt/klyne/postgres_data
                    sudo chown -R 999:999 /opt/klyne/postgres_data
                fi
            fi
        "
        
        # Setup SSL certificates if domain is provided
        if [[ -n "$DOMAIN_NAME" ]]; then
            log "Setting up SSL certificate for $DOMAIN_NAME"
            ssh deploy@$server "
                if [[ ! -f /opt/klyne/ssl/cert.pem ]]; then
                    sudo certbot certonly --standalone --agree-tos --no-eff-email \
                        --email admin@$DOMAIN_NAME -d $DOMAIN_NAME \
                        --cert-path /opt/klyne/ssl/cert.pem \
                        --key-path /opt/klyne/ssl/key.pem || {
                        # If certbot fails, create self-signed certificate
                        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                            -keyout /opt/klyne/ssl/key.pem \
                            -out /opt/klyne/ssl/cert.pem \
                            -subj '/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_NAME'
                    }
                fi
            "
        else
            # Create self-signed certificate
            ssh deploy@$server "
                if [[ ! -f /opt/klyne/ssl/cert.pem ]]; then
                    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                        -keyout /opt/klyne/ssl/key.pem \
                        -out /opt/klyne/ssl/cert.pem \
                        -subj '/C=US/ST=State/L=City/O=Organization/CN=localhost'
                fi
            "
        fi
    fi
    
    # Pull the new image
    log "Pulling Docker image on $server..."
    ssh deploy@$server "
        cd /opt/klyne
        echo '${GITHUB_TOKEN}' | docker login ghcr.io -u '${GITHUB_ACTOR}' --password-stdin
        docker compose -f docker-compose.prod.yml pull app
    "
    
    # Backup database if this is the primary server
    if [[ "$is_first_server" == "true" ]]; then
        log "Creating database backup on $server..."
        ssh deploy@$server "
            cd /opt/klyne
            if docker compose -f docker-compose.prod.yml ps postgres | grep -q 'Up'; then
                docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres klyne > backups/backup_\$(date +%Y%m%d_%H%M%S).sql || true
                find backups/ -name '*.sql' -mtime +7 -delete || true
            fi
        "
    fi
    
    # Deploy with rolling restart
    log "Deploying application on $server..."
    ssh deploy@$server "
        cd /opt/klyne
        
        # Start services (PostgreSQL only on first server)
        if [[ '$is_first_server' == 'true' ]]; then
            docker compose -f docker-compose.prod.yml up -d postgres
            sleep 10
        fi
        
        # Update and restart app
        docker compose -f docker-compose.prod.yml up -d app nginx
        
        # Clean up old images
        docker image prune -f || true
    "
    
    # Wait a moment for services to start
    sleep 10
    
    # Verify deployment
    check_health $server
    
    log "✓ Deployment to $server completed successfully"
}

# Rollback deployment
rollback_server() {
    local server=$1
    local previous_tag=${PREVIOUS_IMAGE_TAG:-}
    
    if [[ -z "$previous_tag" ]]; then
        warn "No previous image tag specified, cannot rollback $server"
        return 1
    fi
    
    warn "Rolling back $server to $previous_tag..."
    
    ssh deploy@$server "
        cd /opt/klyne
        export IMAGE_TAG=$previous_tag
        docker compose -f docker-compose.prod.yml up -d app
    "
    
    if check_health $server; then
        log "✓ Rollback of $server completed successfully"
    else
        error "✗ Rollback of $server failed"
    fi
}

# Main deployment function
main() {
    check_requirements
    
    local servers_array=($SERVERS)
    local failed_servers=()
    
    log "Starting rolling deployment to servers: ${servers_array[*]}"
    log "Image tag: $IMAGE_TAG"
    
    # Deploy to each server one by one
    for i in "${!servers_array[@]}"; do
        local server=${servers_array[$i]}
        local is_first_server="false"
        
        # First server handles PostgreSQL
        if [[ $i -eq 0 ]]; then
            is_first_server="true"
        fi
        
        if deploy_to_server "$server" "$is_first_server"; then
            log "✓ Successfully deployed to $server"
        else
            error "✗ Failed to deploy to $server"
            failed_servers+=($server)
        fi
        
        # Add delay between deployments for rolling update
        if [[ $((i + 1)) -lt ${#servers_array[@]} ]]; then
            log "Waiting 30 seconds before deploying to next server..."
            sleep 30
        fi
    done
    
    # Check final status
    if [[ ${#failed_servers[@]} -eq 0 ]]; then
        log "🎉 Rolling deployment completed successfully on all servers!"
        log "Application is now running with image: $IMAGE_TAG"
    else
        error "Deployment failed on servers: ${failed_servers[*]}"
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi