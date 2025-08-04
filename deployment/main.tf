terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.47"
    }
  }
  required_version = ">= 1.0"
  
  # Using local backend for simplicity
  # For production, consider using remote backend (S3, Terraform Cloud, etc.)
}

# Note: S3 backend variables are configured via environment variables or backend config
# No need to declare them as Terraform variables since they're used only for backend

variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for server access"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "resend_api_key" {
  description = "Resend API key for email services"
  type        = string
  sensitive   = true
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH Key
resource "hcloud_ssh_key" "klyne_key" {
  name       = "klyne-deployment-key"
  public_key = var.ssh_public_key
}

# Network configuration removed - using only public IP

# Firewall
resource "hcloud_firewall" "klyne_firewall" {
  name = "klyne-firewall"

  rule {
    direction = "in"
    port      = "22"
    protocol  = "tcp"
    source_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "in"
    port      = "80"
    protocol  = "tcp"
    source_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "in"
    port      = "443"
    protocol  = "tcp"
    source_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "out"
    protocol  = "icmp"
    destination_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "out"
    port      = "1-65535"
    protocol  = "tcp"
    destination_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "out"
    port      = "1-65535"
    protocol  = "udp"
    destination_ips = ["0.0.0.0/0"]
  }
}

# Load balancer removed for cost optimization - using single server setup

# Single server for cost-optimized deployment
resource "hcloud_server" "klyne_server" {
  name        = "klyne-app"
  image       = "ubuntu-22.04"
  server_type = "cpx21"  # 3 vCPU, 4 GB RAM, 80 GB SSD
  location    = "nbg1"
  ssh_keys    = [hcloud_ssh_key.klyne_key.id]

  firewall_ids = [hcloud_firewall.klyne_firewall.id]
  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }

  user_data = templatefile("${path.module}/cloud-init.yml", {
    ssh_public_key = var.ssh_public_key
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Volume for PostgreSQL data removed - using local disk storage instead

# Outputs
output "server_ipv4" {
  description = "IPv4 address of the server"
  value       = hcloud_server.klyne_server.ipv4_address
}

output "server_ips" {
  description = "List of server IPs (for compatibility with deploy script)"
  value       = [hcloud_server.klyne_server.ipv4_address]
}

output "load_balancer_ipv4" {
  description = "Load balancer IP (same as server IP in single-server setup)"
  value       = hcloud_server.klyne_server.ipv4_address
}

output "server_name" {
  description = "Name of the server"
  value       = hcloud_server.klyne_server.name
}