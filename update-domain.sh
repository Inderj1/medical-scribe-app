#!/bin/bash

# Script to update Medical Scribe application for custom domain

if [ -z "$1" ]; then
    echo "Usage: ./update-domain.sh yourdomain.com"
    exit 1
fi

DOMAIN=$1
SERVER_IP="54.197.58.233"

echo "Updating Medical Scribe application for domain: $DOMAIN"

# SSH into server and update configurations
ssh -i ~/.ssh/medical-scribe-key ubuntu@$SERVER_IP << EOF

# Update backend environment
echo "Updating backend configuration..."
sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://$DOMAIN\",\"https://www.$DOMAIN\",\"http://$DOMAIN\",\"http://www.$DOMAIN\",\"http://localhost:3000\"]|" /opt/medical-scribe/backend/.env

# Update frontend environment
echo "Updating frontend configuration..."
cat > /opt/medical-scribe/frontend/.env << EOL
REACT_APP_API_URL=https://$DOMAIN/api
REACT_APP_WS_URL=wss://$DOMAIN/ws
REACT_APP_EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
REACT_APP_EPIC_REDIRECT_URI=https://$DOMAIN/callback
REACT_APP_CLERK_PUBLISHABLE_KEY=pk_test_ZXhjaXRpbmctc2FsbW9uLTY3LmNsZXJrLmFjY291bnRzLmRldiQ
EOL

# Update nginx configuration
echo "Updating nginx configuration..."
sudo bash -c "cat > /etc/nginx/sites-available/medical-scribe << 'EONGINX'
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 100M;

    # Frontend
    location / {
        proxy_pass http://localhost:3100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_cache_bypass \\\$http_upgrade;
    }

    # Backend API
    location /api {
        rewrite ^/api(.*)\\\$ \\\$1 break;
        proxy_pass http://localhost:8100;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    # Backend docs
    location /docs {
        proxy_pass http://localhost:8100/docs;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
    }

    # Backend health
    location /health {
        proxy_pass http://localhost:8100/health;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
    }
}
EONGINX"

# Test and reload nginx
sudo nginx -t && sudo systemctl reload nginx

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Restart services
echo "Restarting services..."
pkill -f uvicorn
pkill -f 'react-scripts'
cd /opt/medical-scribe
nohup ./start-backend.sh > backend.log 2>&1 &
nohup ./start-frontend.sh > frontend.log 2>&1 &

echo "Configuration updated! Services are restarting..."
echo ""
echo "Next steps:"
echo "1. Wait for DNS propagation (5-30 minutes)"
echo "2. Test HTTP access: http://$DOMAIN"
echo "3. Set up SSL certificate: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"

EOF

echo "Domain update script completed!"