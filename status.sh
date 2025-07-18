#!/bin/bash

# Medical Scribe Application - Status Check Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379

# Print colored output
print_running() {
    echo -e "  ${GREEN}●${NC} $1"
}

print_stopped() {
    echo -e "  ${RED}●${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}●${NC} $1"
}

# Check if port is in use
check_port() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Check if service is healthy
check_health() {
    curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1
}

# Main status check
echo -e "${BLUE}Medical Scribe Application Status${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Backend API
if check_port $BACKEND_PORT; then
    if check_health; then
        print_running "Backend API (port $BACKEND_PORT) - Healthy"
    else
        print_warning "Backend API (port $BACKEND_PORT) - Running but not healthy"
    fi
else
    print_stopped "Backend API (port $BACKEND_PORT) - Not running"
fi

# Frontend
if check_port $FRONTEND_PORT; then
    print_running "Frontend (port $FRONTEND_PORT) - Running"
else
    print_stopped "Frontend (port $FRONTEND_PORT) - Not running"
fi

# PostgreSQL
if check_port $POSTGRES_PORT; then
    print_running "PostgreSQL (port $POSTGRES_PORT) - Running"
else
    print_stopped "PostgreSQL (port $POSTGRES_PORT) - Not running"
fi

# Redis
if check_port $REDIS_PORT; then
    print_running "Redis (port $REDIS_PORT) - Running"
else
    print_stopped "Redis (port $REDIS_PORT) - Not running"
fi

# Docker status
echo ""
if command -v docker >/dev/null 2>&1; then
    containers=$(docker-compose ps -q 2>/dev/null | wc -l | tr -d ' ')
    if [ "$containers" -gt 0 ]; then
        echo -e "${BLUE}Docker Containers:${NC}"
        docker-compose ps 2>/dev/null
    fi
fi

# URLs
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  Backend API:  http://localhost:$BACKEND_PORT"
echo -e "  API Docs:     http://localhost:$BACKEND_PORT/docs"
echo -e "  Frontend:     http://localhost:$FRONTEND_PORT"
echo -e "  Health Check: http://localhost:$BACKEND_PORT/health"

# Check for common issues
echo ""
echo -e "${BLUE}Configuration:${NC}"

if [ -f "backend/.env" ]; then
    if grep -q "your-secret-key-here\|your-openai-api-key" "backend/.env"; then
        print_warning "backend/.env needs API keys configuration"
    else
        print_running "backend/.env configured"
    fi
else
    print_stopped "backend/.env missing"
fi

if [ -f "frontend/.env" ]; then
    print_running "frontend/.env exists"
else
    print_stopped "frontend/.env missing"
fi

# Python virtual environment
if [ -d "backend/venv" ]; then
    print_running "Python virtual environment exists"
else
    print_stopped "Python virtual environment missing"
fi

# Node modules
if [ -d "frontend/node_modules" ]; then
    print_running "Node modules installed"
else
    print_stopped "Node modules missing"
fi

echo ""