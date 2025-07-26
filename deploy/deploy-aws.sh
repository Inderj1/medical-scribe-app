#!/bin/bash

# AWS Deployment Script for Medical Scribe Application

set -e

echo "🚀 Medical Scribe AWS Deployment Script"
echo "======================================="

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed. Aborting." >&2; exit 1; }

# Get deployment parameters
read -p "Enter AWS Region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

read -p "Enter environment name (default: production): " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-production}

read -p "Enter your domain name (e.g., medical-scribe.example.com): " DOMAIN_NAME

# Export variables
export TF_VAR_aws_region=$AWS_REGION
export TF_VAR_environment=$ENVIRONMENT

# Initialize Terraform
echo "📦 Initializing Terraform..."
cd deploy/terraform
terraform init

# Plan deployment
echo "📋 Planning infrastructure..."
terraform plan -out=tfplan

# Confirm deployment
read -p "Do you want to proceed with deployment? (yes/no): " CONFIRM
if [[ $CONFIRM != "yes" ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Apply Terraform
echo "🏗️ Creating infrastructure..."
terraform apply tfplan

# Get outputs
APP_IP=$(terraform output -raw app_public_ip)
DB_ENDPOINT=$(terraform output -raw db_endpoint)
DB_PASSWORD=$(terraform output -raw db_password)

echo "✅ Infrastructure created successfully!"
echo "======================================="
echo "Application IP: $APP_IP"
echo "Database Endpoint: $DB_ENDPOINT"
echo ""
echo "Next steps:"
echo "1. SSH into the server: ssh ubuntu@$APP_IP"
echo "2. Clone your repository:"
echo "   git clone https://github.com/yourusername/medical-scribe-app.git /opt/medical-scribe"
echo "3. Update /opt/medical-scribe/.env with your API keys"
echo "4. Start the application:"
echo "   cd /opt/medical-scribe && docker-compose up -d"
echo "5. Set up SSL certificate:"
echo "   sudo certbot --nginx -d $DOMAIN_NAME"
echo ""
echo "📝 Save these credentials securely:"
echo "Database Password: $DB_PASSWORD"