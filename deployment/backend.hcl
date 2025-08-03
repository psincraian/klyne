# Terraform S3 Backend Configuration
# Copy this file to backend.hcl and update with your S3 details
# Then run: terraform init -backend-config=backend.hcl

bucket                      = "your-terraform-state-bucket"
region                      = "us-east-1"
endpoint                    = "https://your-s3-endpoint.com"
access_key                  = "your-s3-access-key"
secret_key                  = "your-s3-secret-key"
skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
force_path_style           = true