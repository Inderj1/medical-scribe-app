# Medical Scribe Application - Complete Setup Guide

## Quick Start (Recommended)

The fastest way to get started:

```bash
# 1. Clone the repository
git clone <repository-url>
cd medical-scribe-app

# 2. Run the setup script
./run.sh
```

This will handle everything automatically. Skip to the [Configuration](#configuration) section to add your API keys.

## Manual Setup

If you prefer to set things up manually or want to understand each step:

### 1. System Requirements

Ensure you have these installed:

- **Python 3.11+**
  ```bash
  # macOS
  brew install python

  # Ubuntu/Debian
  sudo apt-get install python3 python3-pip python3-venv

  # Check version
  python3 --version
  ```

- **Node.js 18+**
  ```bash
  # macOS
  brew install node

  # Ubuntu/Debian
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs

  # Check version
  node --version
  npm --version
  ```

- **PostgreSQL 15+**
  ```bash
  # macOS
  brew install postgresql
  brew services start postgresql

  # Ubuntu/Debian
  sudo apt-get install postgresql postgresql-contrib
  sudo systemctl start postgresql
  ```

- **Redis 7+**
  ```bash
  # macOS
  brew install redis
  brew services start redis

  # Ubuntu/Debian
  sudo apt-get install redis-server
  sudo systemctl start redis
  ```

- **Docker (Optional but recommended)**
  ```bash
  # macOS
  brew install docker docker-compose

  # Ubuntu/Debian
  sudo apt-get install docker.io docker-compose
  ```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
cat > .env << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
REACT_APP_EPIC_REDIRECT_URI=https://localhost:3000/callback
EOF
```

### 4. Database Setup

#### Option A: Docker (Recommended)

```bash
# Start databases with Docker
docker-compose up -d postgres redis

# Verify they're running
docker-compose ps
```

#### Option B: Local Installation

```bash
# Create PostgreSQL database
createdb medical_scribe_db

# Verify Redis is running
redis-cli ping
```

### 5. Database Migrations

```bash
cd backend
source venv/bin/activate

# Create database tables
python -c "from app.db.session import engine, Base; Base.metadata.create_all(bind=engine)"
```

### 6. Start Services

#### Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm start
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Configuration

### Required API Keys

Edit `backend/.env` with your API keys:

```env
# Required for AI transcription
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional for clinical NLP
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Required for security
SECRET_KEY=your-secure-secret-key-here
```

### Epic EHR Configuration

If using Epic integration, add to `backend/.env`:

```env
# Epic Configuration
EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
EPIC_CLIENT_SECRET=your-epic-client-secret-here
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth
EPIC_USE_SANDBOX=true
```

### HTTPS Setup (Required for Epic)

Epic requires HTTPS even for localhost:

```bash
# Create certificates directory
cd frontend
mkdir certificates

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout certificates/localhost.key -out certificates/localhost.crt -days 365 -nodes -subj '/CN=localhost'

# Trust certificate (macOS)
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certificates/localhost.crt

# Update package.json start script
"start": "HTTPS=true SSL_CRT_FILE=certificates/localhost.crt SSL_KEY_FILE=certificates/localhost.key react-scripts start"
```

## Management Commands

### Utility Scripts

```bash
# Start everything
./run.sh

# Stop all services
./stop.sh

# Check service status
./status.sh
```

### Individual Service Management

```bash
# Stop specific ports
sudo lsof -ti:8000 | xargs kill -9  # Backend
sudo lsof -ti:3000 | xargs kill -9  # Frontend

# View logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Database management
docker-compose up -d postgres redis     # Start
docker-compose stop postgres redis      # Stop
docker-compose logs postgres redis      # View logs
```

## Testing

### Basic Health Check

```bash
# Test backend
curl http://localhost:8000/health

# Test Epic configuration (if configured)
curl http://localhost:8000/api/auth/epic/configuration
```

### Epic Integration Test

1. Navigate to https://localhost:3000/launch?iss=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4&launch=test
2. Should redirect to Epic authorization
3. After authorization, should redirect back with patient data

### Database Connection Test

```bash
# PostgreSQL
psql -h localhost -U medscribe -d medical_scribe_db -c "SELECT 1"

# Redis
redis-cli ping
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find and kill process
   sudo lsof -ti:8000 | xargs kill -9
   ```

2. **Python virtual environment issues**
   ```bash
   # Remove and recreate
   rm -rf backend/venv
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Node modules issues**
   ```bash
   # Clear and reinstall
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **Database connection errors**
   ```bash
   # Check if services are running
   brew services list | grep postgres
   brew services list | grep redis
   
   # Restart if needed
   brew services restart postgresql
   brew services restart redis
   ```

5. **Epic integration errors**
   - Ensure HTTPS is working
   - Check client ID and secret
   - Verify redirect URI matches Epic configuration

### Log Files

Check these log files for detailed error information:

- `logs/backend.log` - Backend API logs
- `logs/frontend.log` - Frontend build/runtime logs
- Console output from terminals running services

### Environment Verification

```bash
# Check all environment variables
cd backend && source venv/bin/activate
python -c "from app.core.config import settings; print(f'DB: {settings.DATABASE_URL}'); print(f'Redis: {settings.REDIS_URL}')"
```

## Development Workflow

### Making Changes

1. **Backend changes**: FastAPI auto-reloads on file changes
2. **Frontend changes**: React auto-reloads on file changes
3. **Database changes**: Update models and run migrations

### Adding New Features

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Develop and test**
   ```bash
   # Run tests
   cd backend && python -m pytest
   cd frontend && npm test
   ```

3. **Update documentation**
   - Update README.md
   - Add API documentation
   - Update configuration if needed

## Deployment

### Production Preparation

1. **Environment configuration**
   ```bash
   # Set production environment variables
   export EPIC_USE_SANDBOX=false
   export EPIC_CLIENT_ID=cb117f80-34b1-4bdf-a404-b69cf3d044de
   ```

2. **Build frontend**
   ```bash
   cd frontend
   npm run build
   ```

3. **Configure reverse proxy** (nginx example)
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       location /api/ {
           proxy_pass http://localhost:8000;
       }
       
       location / {
           proxy_pass http://localhost:3000;
       }
   }
   ```

### Docker Production

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose ps
```

## Support

### Getting Help

1. **Check logs** for specific error messages
2. **Review configuration** files
3. **Test individual components** (database, API, frontend)
4. **Check Epic developer documentation** for EHR integration issues

### Useful Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Epic FHIR Documentation](https://fhir.epic.com/Documentation)
- [SMART on FHIR](http://docs.smarthealthit.org/)

Remember to keep your API keys secure and never commit them to version control!