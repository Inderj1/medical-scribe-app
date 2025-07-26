# AWS Deployment Guide for Medical Scribe Application

## Overview

This guide provides instructions for deploying the Medical Scribe application on AWS using Terraform and Docker.

## Deployment Options

### Option 1: EC2 + RDS (Recommended)
- **Cost**: ~$65/month
- **Components**: 
  - EC2 t3.large instance (8GB RAM)
  - RDS PostgreSQL db.t3.micro
  - Elastic IP
  - VPC with public/private subnets

### Option 2: Single EC2 (Budget)
- **Cost**: ~$30/month
- **Components**: 
  - EC2 t3.medium instance (4GB RAM)
  - PostgreSQL on same instance
  - Docker Compose setup

### Option 3: ECS Fargate (Scalable)
- **Cost**: ~$40-80/month (usage-based)
- **Components**: 
  - Fargate containers
  - RDS PostgreSQL
  - Application Load Balancer

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Terraform installed (v1.0+)
4. SSH key pair for EC2 access
5. Domain name (optional, for SSL)

## Quick Start Deployment

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/medical-scribe-app.git
cd medical-scribe-app
```

### 2. Configure environment
```bash
cp .env.production.example .env
# Edit .env with your actual values
```

### 3. Run deployment script
```bash
cd deploy
./deploy-aws.sh
```

### 4. Manual deployment steps

#### a. Using Terraform (Infrastructure as Code)
```bash
cd deploy/terraform
terraform init
terraform plan
terraform apply
```

#### b. Manual EC2 Setup
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone repository
git clone https://github.com/yourusername/medical-scribe-app.git /opt/medical-scribe
cd /opt/medical-scribe

# Copy and configure environment
cp .env.production.example .env
nano .env  # Update with your values

# Build and run with Docker Compose
docker-compose up -d
```

## Post-Deployment Configuration

### 1. SSL Certificate (Required for Production)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 2. Configure DNS
Point your domain to the Elastic IP address in your DNS provider:
- Type: A Record
- Name: @ (or subdomain)
- Value: Your Elastic IP

### 3. Set up monitoring
```bash
# Install monitoring agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

### 4. Configure backups
The deployment automatically sets up daily database backups at 2 AM UTC.

## Security Considerations

1. **Update Security Groups**
   - Restrict SSH access to your IP only
   - Enable HTTPS (443) and disable HTTP (80) after SSL setup

2. **Secrets Management**
   - Use AWS Secrets Manager for API keys
   - Rotate database passwords regularly

3. **Enable AWS GuardDuty** for threat detection

4. **Set up WAF** for web application firewall

## Maintenance

### Update Application
```bash
ssh ubuntu@your-ec2-ip
cd /opt/medical-scribe
./deploy.sh
```

### View Logs
```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# Nginx logs
sudo tail -f /var/log/nginx/access.log
```

### Database Backup
```bash
# Manual backup
/opt/medical-scribe/backup.sh

# Restore backup
gunzip < /opt/backups/db_backup_20240115_120000.sql.gz | docker-compose exec -T postgres psql -U medscribe medical_scribe
```

## Scaling Options

### Vertical Scaling
- Upgrade EC2 instance type through AWS Console
- Increase RDS instance class

### Horizontal Scaling
- Use AWS Auto Scaling Groups
- Deploy with ECS for container orchestration
- Add Application Load Balancer

## Cost Optimization

1. **Use Reserved Instances** - Save up to 72%
2. **Enable Auto-stop** for development environments
3. **Use S3 for file storage** instead of EBS
4. **Monitor with AWS Cost Explorer**

## Troubleshooting

### Application not accessible
```bash
# Check Docker containers
docker-compose ps

# Check Nginx
sudo systemctl status nginx

# Check firewall
sudo ufw status
```

### Database connection issues
```bash
# Test database connection
docker-compose exec app python -c "from app.db.session import engine; engine.connect()"

# Check RDS security group
aws ec2 describe-security-groups --group-ids sg-xxxxxx
```

### High CPU/Memory usage
```bash
# Check resource usage
htop

# Docker stats
docker stats

# Restart services
docker-compose restart
```

## Support

For issues or questions:
1. Check application logs
2. Review AWS CloudWatch metrics
3. Contact support at support@example.com