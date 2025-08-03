#!/bin/bash

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check if gh CLI is installed
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed. Please install it first: https://cli.github.com/"
    fi
    
    if ! gh auth status &> /dev/null; then
        error "Not authenticated with GitHub CLI. Run 'gh auth login' first."
    fi
}

# Generate secure random password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Set GitHub repository secret
set_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gh secret set "$secret_name" --body "$secret_value"; then
        log "✓ Set secret: $secret_name"
    else
        error "✗ Failed to set secret: $secret_name"
    fi
}

# Main setup function
main() {
    log "Setting up GitHub repository secrets for Klyne deployment"
    
    check_gh_cli
    
    # Generate secure passwords if not provided
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(generate_password 32)}
    SECRET_KEY=${SECRET_KEY:-$(generate_password 64)}
    
    # Required secrets
    log "Setting up required secrets..."
    
    echo -n "Enter your Hetzner Cloud API token: "
    read -s HCLOUD_TOKEN
    echo
    
    echo -n "Enter your SSH private key (paste the entire key): "
    read -s SSH_PRIVATE_KEY
    echo
    
    echo -n "Enter your domain name (optional, press enter to skip): "
    read DOMAIN_NAME
    
    # Set secrets in GitHub
    set_secret "HCLOUD_TOKEN" "$HCLOUD_TOKEN"
    set_secret "SSH_PRIVATE_KEY" "$SSH_PRIVATE_KEY"
    set_secret "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
    set_secret "SECRET_KEY" "$SECRET_KEY"
    
    if [[ -n "$DOMAIN_NAME" ]]; then
        set_secret "DOMAIN_NAME" "$DOMAIN_NAME"
    fi
    
    
    log "🎉 GitHub secrets setup completed!"
    log ""
    log "Generated passwords (save these securely):"
    log "POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
    log "SECRET_KEY: $SECRET_KEY"
    log ""
    log "Next steps:"
    log "1. Copy deployment/terraform.tfvars.example to deployment/terraform.tfvars"
    log "2. Fill in your values in terraform.tfvars"
    log "3. Run 'terraform init && terraform plan && terraform apply' in the deployment/ directory"
    log "4. Commit and push your code to trigger the deployment pipeline"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi