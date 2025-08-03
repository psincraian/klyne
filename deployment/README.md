# Klyne Deployment Guide

This directory contains a frugal CI/CD pipeline and deployment configuration for Klyne on Hetzner Cloud.

## Overview

The deployment setup includes:

- **Infrastructure**: Terraform configuration for Hetzner Cloud
- **CI/CD**: GitHub Actions workflows for testing and deployment
- **Container Orchestration**: Docker Compose for application services
- **Load Balancing**: Nginx with SSL termination and basic health checks
- **Rolling Updates**: Zero-downtime deployment strategy
- **Backup & Recovery**: Automated database backups and rollback capabilities

## Architecture

```
Internet → Load Balancer → [Server 1, Server 2] → PostgreSQL (Server 1)
```

### Components

- **2x Hetzner Cloud servers** (CPX21: 3 vCPU, 4GB RAM, 80GB SSD)
- **Load Balancer** with health checks
- **PostgreSQL** with persistent volume storage
- **Nginx** for reverse proxy and SSL termination
- **Simple health monitoring** with basic HTTP checks

## Quick Start

### 1. Prerequisites

- [Terraform](https://terraform.io/) installed
- [GitHub CLI](https://cli.github.com/) installed and authenticated
- Hetzner Cloud account and API token
- SSH key pair generated

### 2. Setup Secrets

Run the secrets setup script:

```bash
cd deployment
./setup-secrets.sh
```

This will configure all required GitHub repository secrets.

### 3. Configure Infrastructure

Copy the Terraform variables template:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
hcloud_token = "your-hetzner-cloud-api-token"
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAA... your-email@example.com"
domain_name = "your-domain.com"  # Optional
```

### 4. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 5. Deploy Application

Push to the `main` branch to trigger the CI/CD pipeline:

```bash
git push origin main
```

## Manual Operations

### Deploy Application Manually

```bash
# Set environment variables
export SERVERS="server1_ip server2_ip"
export IMAGE_TAG="latest"
export POSTGRES_PASSWORD="your-password"
export SECRET_KEY="your-secret-key"

# Run deployment
./deploy.sh
```

### Rollback Deployment

```bash
# List available tags
./rollback.sh --list

# Rollback to specific tag
./rollback.sh -s "server1_ip,server2_ip" -t "v1.0.0"
```

### Health Monitoring

The deployment includes a simple health monitoring script:

```bash
# Check all servers once
./health-check.sh -s "server1_ip,server2_ip" --check

# Start continuous monitoring
./health-check.sh -s "server1_ip,server2_ip" --monitor
```

## File Structure

```
deployment/
├── README.md                 # This file
├── main.tf                   # Terraform infrastructure
├── cloud-init.yml           # Server initialization
├── terraform.tfvars.example # Infrastructure variables template
├── deploy.sh                # Deployment script
├── rollback.sh              # Rollback script
├── health-check.sh          # Simple health monitoring
├── setup-secrets.sh         # GitHub secrets setup
└── secrets.example.env      # Environment variables template
```

## GitHub Actions Workflows

### CI Workflow (`.github/workflows/ci.yml`)

Triggers on push/PR to main branches:

1. **Test**: Run pytest with PostgreSQL
2. **Build**: Build and push Docker image
3. **Security**: Scan image with Trivy

### CD Workflow (`.github/workflows/cd.yml`)

Triggers after successful CI on main branch:

1. **Deploy**: Rolling deployment to production servers
2. **Verify**: Health check verification
3. **Rollback**: Automatic rollback on failure

## Security Features

- **Non-root containers**: Application runs as non-privileged user
- **Firewall rules**: Restricted network access
- **SSH hardening**: Key-based authentication only
- **SSL/TLS**: HTTPS with Let's Encrypt or self-signed certificates
- **Image scanning**: Vulnerability scanning with Trivy
- **Secrets management**: GitHub secrets for sensitive data

## Health Monitoring

### Simple Health Checks

The deployment includes basic health monitoring:

- HTTP health endpoint checks (`/health`)
- Load balancer health probes
- Simple logging and failure detection
- Manual monitoring via `health-check.sh` script

### Health Check Features

- Configurable check intervals
- Failure threshold detection  
- Basic logging to `/opt/klyne/logs/health-check.log`
- Simple notification hooks (can be extended)

For advanced monitoring needs, you can integrate external services like:
- Uptime monitoring services (UptimeRobot, Pingdom)
- Application monitoring (Sentry, Rollbar)
- Log aggregation services

## Backup Strategy

### Automated Backups

- Daily PostgreSQL dumps during deployment
- 7-day retention policy
- Stored in `/opt/klyne/backups/` on primary server

### Manual Backup

```bash
# SSH to primary server
ssh deploy@server1_ip

# Create backup
cd /opt/klyne
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres klyne > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Troubleshooting

### Check Application Status

```bash
# Check service health
curl http://your-server-ip/health

# Use health check script
./health-check.sh -s "server_ip" --check

# Check container status
ssh deploy@server_ip "cd /opt/klyne && docker compose -f docker-compose.prod.yml ps"

# View logs
ssh deploy@server_ip "cd /opt/klyne && docker compose -f docker-compose.prod.yml logs -f app"

# Check nginx status
curl http://your-server-ip/nginx_status
```

### Common Issues

1. **Deployment fails**: Check GitHub Actions logs and server connectivity
2. **SSL certificate issues**: Verify domain DNS and Let's Encrypt limits  
3. **Database connection**: Check PostgreSQL logs and network connectivity
4. **Health checks failing**: Verify application is responding on `/health`
5. **High resource usage**: Monitor with `htop` or upgrade server type

### Emergency Procedures

1. **Complete failure**: Use rollback script to previous stable version
2. **Database corruption**: Restore from backup and restart services
3. **Server unavailable**: Remove from load balancer and investigate
4. **High load**: Check health logs and consider scaling server resources

## Configuration

### Environment Variables

Required secrets in GitHub repository:

- `HCLOUD_TOKEN`: Hetzner Cloud API token
- `SSH_PRIVATE_KEY`: SSH private key for server access
- `POSTGRES_PASSWORD`: Database password
- `SECRET_KEY`: Application secret key
- `DOMAIN_NAME`: Your domain (optional)

### Resource Limits

Current configuration:

- **Servers**: 2x CPX21 (3 vCPU, 4GB RAM, 80GB SSD)
- **PostgreSQL Volume**: 50GB persistent storage
- **Docker Memory**: 512MB limit per container

Scale up by modifying `main.tf` server type or adding more servers.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Check server logs via SSH
4. Use health check script for diagnostics

## Next Steps

Consider implementing:

- **Multi-region deployment** for high availability
- **CDN integration** for static asset delivery  
- **Database replication** for read scaling
- **Blue-green deployments** for zero-downtime updates
- **External monitoring** services (UptimeRobot, Pingdom)
- **Centralized logging** with external services