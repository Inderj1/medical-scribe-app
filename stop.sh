#!/bin/bash

# Medical Scribe Application - Stop Script
# This script stops all running services

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
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Kill process on port
kill_port() {
    local port=$1
    local service=$2
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        print_status "Stopping $service on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 1
        print_success "$service stopped"
    else
        print_status "$service not running on port $port"
    fi
}

# Stop all services
stop_all() {
    echo -e "${BLUE}Stopping Medical Scribe Application...${NC}"
    echo ""
    
    # Kill processes using PID files if they exist
    if [ -f .backend.pid ]; then
        pid=$(cat .backend.pid)
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping backend (PID: $pid)"
            kill $pid 2>/dev/null || true
            print_success "Backend stopped"
        fi
        rm .backend.pid
    fi
    
    if [ -f .frontend.pid ]; then
        pid=$(cat .frontend.pid)
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping frontend (PID: $pid)"
            kill $pid 2>/dev/null || true
            print_success "Frontend stopped"
        fi
        rm .frontend.pid
    fi
    
    # Kill processes on ports as backup
    kill_port $BACKEND_PORT "Backend API"
    kill_port $FRONTEND_PORT "Frontend"
    
    # Stop Docker containers if running
    if command -v docker >/dev/null 2>&1; then
        if docker-compose ps -q 2>/dev/null | grep -q .; then
            print_status "Stopping Docker containers..."
            docker-compose down
            print_success "Docker containers stopped"
        fi
    fi
    
    # Optionally stop local services (commented out by default)
    # Uncomment if you want to stop system-wide PostgreSQL and Redis
    
    # if [[ "$OSTYPE" == "darwin"* ]]; then
    #     print_status "Stopping local services (macOS)..."
    #     brew services stop postgresql 2>/dev/null || true
    #     brew services stop redis 2>/dev/null || true
    # else
    #     print_status "Stopping local services (Linux)..."
    #     sudo systemctl stop postgresql 2>/dev/null || true
    #     sudo systemctl stop redis 2>/dev/null || true
    # fi
    
    echo ""
    print_success "All services stopped"
}

# Main execution
stop_all