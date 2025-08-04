# Terraform S3 Backend Configuration
# Copy this file to backend.hcl and update with your S3 details
# Then run: terraform init -backend-config=backend.hcl

bucket                      = "klyne-terraform"
region                      = "us-east-1"
endpoint                    = "https://c26be9b36a513ce4fc9074e8071346dd.r2.cloudflarestorage.com"
skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
force_path_style           = true