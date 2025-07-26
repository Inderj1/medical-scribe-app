#!/bin/bash

# Terraform Deployment Script for Medical Scribe App
# Using t3.large EC2 instance

set -e

echo "🚀 Medical Scribe AWS Deployment with Terraform"
echo "=============================================="
echo "Instance Type: t3.large (2 vCPU, 8GB RAM)"
echo "Database: RDS PostgreSQL db.t3.micro"
echo "=============================================="

# Check prerequisites
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Installing..."
    # For macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew tap hashicorp/tap
        brew install hashicorp/tap/terraform
    else
        echo "Please install Terraform: https://www.terraform.io/downloads"
        exit 1
    fi
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
echo "📋 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run: aws configure"
    exit 1
fi

echo "✅ AWS Account: $(aws sts get-caller-identity --query Account --output text)"
echo ""

# Navigate to terraform directory
cd "$(dirname "$0")/terraform"

# Create tfvars if not exists
if [ ! -f terraform.tfvars ]; then
    echo "📝 Creating terraform.tfvars..."
    cp terraform.tfvars.example terraform.tfvars
    echo "⚠️  Please edit terraform.tfvars with your settings"
    echo "Press Enter to continue after editing..."
    read
fi

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init -upgrade

# Validate configuration
echo "✅ Validating Terraform configuration..."
terraform validate

# Create workspace if needed
WORKSPACE=${TF_WORKSPACE:-production}
if ! terraform workspace list | grep -q $WORKSPACE; then
    echo "📁 Creating workspace: $WORKSPACE"
    terraform workspace new $WORKSPACE
else
    terraform workspace select $WORKSPACE
fi

# Plan the deployment
echo "📋 Planning infrastructure..."
terraform plan -out=tfplan

# Show estimated costs
echo ""
echo "💰 Estimated Monthly Costs:"
echo "- EC2 t3.large: ~$60/month"
echo "- RDS db.t3.micro: ~$15/month"
echo "- EBS Storage (30GB): ~$3/month"
echo "- Elastic IP: Free (while attached)"
echo "- Total: ~$78/month"
echo ""

# Confirm deployment
read -p "🚀 Ready to deploy? (yes/no): " CONFIRM
if [[ $CONFIRM != "yes" ]]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

# Apply Terraform
echo "🏗️  Creating AWS infrastructure..."
terraform apply tfplan

# Get outputs
echo ""
echo "✅ Deployment Complete!"
echo "=============================================="

# Save outputs to file
terraform output -json > ../deployment-outputs.json

# Display connection info
APP_IP=$(terraform output -raw app_public_ip)
DB_ENDPOINT=$(terraform output -raw db_endpoint)

echo "🌐 Application IP: $APP_IP"
echo "🗄️  Database Endpoint: $DB_ENDPOINT"
echo ""
echo "📝 Next Steps:"
echo "1. SSH into the server:"
echo "   ssh -i ~/.ssh/id_rsa ubuntu@$APP_IP"
echo ""
echo "2. Clone and setup the application:"
echo "   git clone <your-repo-url> /opt/medical-scribe"
echo "   cd /opt/medical-scribe"
echo "   sudo docker-compose up -d"
echo ""
echo "3. Access the application:"
echo "   http://$APP_IP"
echo ""
echo "4. Set up domain and SSL:"
echo "   sudo certbot --nginx -d yourdomain.com"
echo ""
echo "⚠️  Important: Update security group SSH access to your IP only!"
echo "   aws ec2 modify-security-group-rules --group-id <sg-id> --security-group-rules <rules>"

# Create post-deployment script
cat > ../post-deployment.sh << EOF
#!/bin/bash
# Post-deployment setup script

SERVER_IP=$APP_IP
DB_ENDPOINT=$DB_ENDPOINT
DB_PASSWORD=$(terraform output -raw db_password)

echo "🔧 Post-Deployment Setup"
echo "======================="

# SSH command function
ssh_exec() {
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@\$SERVER_IP "\$@"
}

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready..."
sleep 30

# Clone repository
echo "📦 Cloning repository..."
ssh_exec "sudo git clone $REPO_URL /opt/medical-scribe || true"

# Update environment file
echo "🔐 Configuring environment..."
ssh_exec "sudo tee /opt/medical-scribe/.env > /dev/null << EOL
DATABASE_HOST=\$DB_ENDPOINT
DATABASE_PORT=5432
DATABASE_NAME=medical_scribe
DATABASE_USER=medscribe
DATABASE_PASSWORD=\$DB_PASSWORD
DATABASE_URL=postgresql://medscribe:\$DB_PASSWORD@\$DB_ENDPOINT:5432/medical_scribe
REDIS_URL=redis://localhost:6379
SECRET_KEY=\$(openssl rand -hex 32)
ENVIRONMENT=production
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
OPENAI_API_KEY=$OPENAI_API_KEY
OPENEHR_API_URL=http://98.86.40.56
CORS_ORIGINS=http://\$SERVER_IP,https://yourdomain.com
EOL"

# Start services
echo "🚀 Starting services..."
ssh_exec "cd /opt/medical-scribe && sudo docker-compose up -d"

echo "✅ Post-deployment complete!"
echo "Access your application at: http://\$SERVER_IP"
EOF

chmod +x ../post-deployment.sh

echo ""
echo "💡 Run ./post-deployment.sh to complete the setup"