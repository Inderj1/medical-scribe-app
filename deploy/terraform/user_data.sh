#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    htop \
    ufw

# Enable Docker
systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw --force enable

# Create application directory
mkdir -p /opt/medical-scribe
cd /opt/medical-scribe

# Create environment file
cat > .env << EOL
# Database Configuration
DATABASE_HOST=${db_host}
DATABASE_PORT=5432
DATABASE_NAME=${db_name}
DATABASE_USER=${db_user}
DATABASE_PASSWORD=${db_password}
DATABASE_URL=postgresql://${db_user}:${db_password}@${db_host}:5432/${db_name}

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Application Configuration
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production

# Add your actual keys here
CLERK_SECRET_KEY=your_clerk_secret_key
OPENAI_API_KEY=your_openai_api_key

# EHR Integration
OPENEHR_API_URL=http://98.86.40.56

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
EOL

# Set permissions
chown -R ubuntu:ubuntu /opt/medical-scribe
chmod 600 /opt/medical-scribe/.env

# Create systemd service
cat > /etc/systemd/system/medical-scribe.service << EOL
[Unit]
Description=Medical Scribe Application
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/medical-scribe
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Configure Nginx
cat > /etc/nginx/sites-available/medical-scribe << 'EOL'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /ws {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOL

# Enable Nginx site
ln -sf /etc/nginx/sites-available/medical-scribe /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t
systemctl restart nginx

# Create deployment script
cat > /opt/medical-scribe/deploy.sh << 'EOL'
#!/bin/bash
cd /opt/medical-scribe
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
EOL

chmod +x /opt/medical-scribe/deploy.sh

# Create backup script
cat > /opt/medical-scribe/backup.sh << 'EOL'
#!/bin/bash
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker-compose exec -T postgres pg_dump -U ${db_user} ${db_name} | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete
EOL

chmod +x /opt/medical-scribe/backup.sh

# Set up cron for daily backups
echo "0 2 * * * /opt/medical-scribe/backup.sh" | crontab -u ubuntu -

echo "Setup complete! Please:"
echo "1. Clone your repository to /opt/medical-scribe"
echo "2. Update the .env file with your actual API keys"
echo "3. Run: cd /opt/medical-scribe && docker-compose up -d"
echo "4. Set up SSL with: sudo certbot --nginx -d yourdomain.com"