# Klyne Manual Deployment Setup Guide

This guide provides step-by-step instructions for manually deploying Klyne for the first time, assuming you have a Hetzner Cloud API key and S3 bucket ready.

## Prerequisites

Before starting, ensure you have:

✅ **Hetzner Cloud API Token** - Get from [Hetzner Console](https://console.hetzner.cloud/)  
✅ **S3 Compatible Storage** - AWS S3, DigitalOcean Spaces, Minio, etc.  
✅ **Resend Account** - Get API key from [Resend](https://resend.com/api-keys)  
✅ **Domain Name** (optional) - For SSL certificates  

## Required Tools Installation

Install these tools on your local machine:

```bash
# Install Terraform
# macOS
brew install terraform

# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Install GitHub CLI (for repository secrets)
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh
```

## Step 1: Generate SSH Key Pair

Generate an SSH key for server access:

```bash
# Generate SSH key (replace with your email)
ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -f ~/.ssh/klyne_deployment

# Display public key (you'll need this for Terraform)
cat ~/.ssh/klyne_deployment.pub
```

## Step 2: Configure S3 Backend

Navigate to the deployment directory and configure the S3 backend:

```bash
cd deployment

# Copy the backend configuration file
cp backend.hcl backend-config.hcl

# Edit with your S3 details
nano backend-config.hcl
```

Update `backend-config.hcl` with your S3 information:

```hcl
bucket                      = "your-terraform-state-bucket"
region                      = "us-east-1"
endpoint                    = "https://nyc3.digitaloceanspaces.com"  # Example for DigitalOcean
access_key                  = "your-s3-access-key"
secret_key                  = "your-s3-secret-key"
skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
force_path_style           = true
```

## Step 3: Configure Terraform Variables

Configure your infrastructure variables:

```bash
# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your actual values
nano terraform.tfvars
```

Update `terraform.tfvars` with your information:

```hcl
# Hetzner Cloud Configuration
hcloud_token = "your-hetzner-cloud-api-token"

# SSH Configuration
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAA... your-email@example.com"

# Optional: Domain for SSL
domain_name = "your-domain.com"

# Email Service
resend_api_key = "your-resend-api-key"
```

## Step 4: Configure Application Secrets

Set up the application environment variables:

```bash
# Copy the secrets template
cp secrets.example.env secrets.env

# Edit with your values
nano secrets.env
```

Update `secrets.env`:

```env
# PostgreSQL Configuration
POSTGRES_PASSWORD=your-very-secure-postgres-password-here
POSTGRES_USER=postgres
POSTGRES_DB=klyne

# Application Security (generate a strong 32+ character key)
SECRET_KEY=your-very-secure-secret-key-minimum-32-characters-long

# Environment
ENVIRONMENT=production

# Resend API Key (same as in terraform.tfvars)
RESEND_API_KEY=your-resend-api-key

# Optional: Domain Configuration
DOMAIN_NAME=your-domain.com
```

### Generate Secure Keys

Generate secure passwords and keys:

```bash
# Generate a secure postgres password
openssl rand -base64 32

# Generate a secure secret key
openssl rand -base64 64
```

## Step 5: Initialize and Deploy Infrastructure

Initialize Terraform and deploy your infrastructure:

```bash
# Initialize Terraform with S3 backend configuration
terraform init -backend-config=backend-config.hcl

# Review the deployment plan
terraform plan

# Deploy infrastructure (this will take 5-10 minutes)
terraform apply
```

**Expected Output:**
```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:

server_ipv4 = "xxx.xxx.xxx.xxx"
server_name = "klyne-app"
```

## Step 6: Configure DNS (If Using Custom Domain)

If you specified a domain name, configure your DNS:

```bash
# Point your domain to the server IP
# A record: your-domain.com -> [server_ipv4 from terraform output]
```

## Step 7: Wait for Server Initialization

The servers need time to initialize (install Docker, configure security, etc.):

```bash
# Check if server is ready (this may take 5-10 minutes)
# Replace xxx.xxx.xxx.xxx with your server IP from terraform output
ssh -i ~/.ssh/klyne_deployment deploy@xxx.xxx.xxx.xxx "docker --version"
```

## Step 8: Deploy Application

Once servers are ready, deploy the application:

```bash
# Set environment variables for deployment
export SERVER="xxx.xxx.xxx.xxx"  # Your server IP
export IMAGE_TAG="latest"

# Source your secrets
source secrets.env

# Run the deployment script
./deploy.sh
```

## Step 9: Verify Deployment

Check that everything is working:

```bash
# Check application health
curl http://[server_ip]/health

# If you configured a domain
curl http://your-domain.com/health

# Use the health check script
./health-check.sh -s "[server_ip]" --check
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database": "connected"
}
```

## Step 10: Test the Application

Visit your application:

```bash
# Direct IP access
open http://[server_ip]

# Domain access (if configured)
open https://your-domain.com
```

You should see the Klyne landing page with email signup functionality.

## Step 11: Monitor and Maintain

Set up basic monitoring:

```bash
# Start continuous health monitoring
./health-check.sh -s "[server_ip]" --monitor

# Check logs on server
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "cd /opt/klyne && docker compose -f docker-compose.prod.yml logs -f"
```

## Common S3 Provider Examples

### AWS S3
```hcl
bucket                      = "your-terraform-state-bucket"
region                      = "us-east-1"
# endpoint = ""  # Leave out for AWS S3
access_key                  = "AKIA..."
secret_key                  = "your-secret-key"
skip_credentials_validation = false
skip_metadata_api_check     = false
skip_region_validation      = false
force_path_style           = false
```

### DigitalOcean Spaces
```hcl
bucket                      = "your-spaces-bucket"
region                      = "nyc3"
endpoint                    = "https://nyc3.digitaloceanspaces.com"
access_key                  = "your-spaces-key"
secret_key                  = "your-spaces-secret"
skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
force_path_style           = true
```

### Minio
```hcl
bucket                      = "terraform-state"
region                      = "us-east-1"
endpoint                    = "https://minio.your-domain.com"
access_key                  = "minio-access-key"
secret_key                  = "minio-secret-key"
skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
force_path_style           = true
```

## Troubleshooting

### Terraform Issues

```bash
# If S3 backend fails to initialize
terraform init -reconfigure

# If deployment fails, check plan
terraform plan -detailed-exitcode

# Clean up on failure
terraform destroy
```

### Server Connection Issues

```bash
# Check if server is accessible
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "echo 'Connected successfully'"

# Check cloud-init status
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "sudo cloud-init status"
```

### Application Issues

```bash
# Check container status
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "cd /opt/klyne && docker compose ps"

# View application logs
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "cd /opt/klyne && docker compose logs app"

# Check PostgreSQL data storage (local disk)
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "sudo df -h && docker volume ls"

# Restart application
ssh -i ~/.ssh/klyne_deployment deploy@[server_ip] "cd /opt/klyne && docker compose restart app"
```

## Architecture Overview

**Cost-Optimized Single Server Setup:**
- Single Hetzner Cloud server (cpx21: 3 vCPU, 4GB RAM, 80GB SSD)
- PostgreSQL data stored on local SSD (no external volumes)
- Single public IPv4 address (no IPv6 or private networking)
- Simplified networking for reduced complexity and costs

## Security Considerations

1. **Secure your secrets.env file** - Never commit this to version control
2. **Restrict SSH access** - The server is configured to only allow key-based SSH
3. **Firewall rules** - Only ports 22, 80, and 443 are open
4. **SSL certificates** - Configure Let's Encrypt if using a domain
5. **Regular updates** - The server is configured for automatic security updates
6. **Local disk storage** - PostgreSQL data stored on server's SSD (ensure regular backups)

## Next Steps

After successful deployment:

1. **Set up CI/CD** - Configure GitHub Actions for automated deployments
2. **Monitor performance** - Set up external monitoring (UptimeRobot, etc.)
3. **Configure backups** - Set up automated database backups (critical with local storage)
4. **Scale resources** - Monitor disk usage (80GB SSD) and server performance
5. **Backup strategy** - Regular PostgreSQL dumps since data is stored locally

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review deployment logs in `/opt/klyne/logs/` on servers
3. Use the health check script for diagnostics
4. Check Terraform state with `terraform show`

---

**Estimated total deployment time:** 20-30 minutes (including server initialization)