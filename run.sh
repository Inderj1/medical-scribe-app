#!/bin/bash

# Medical Scribe Application - Complete Setup and Run Script
# This script handles all setup and startup tasks

set -e  # Exit on error

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

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ASCII Art Banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                  Medical Scribe Application                  ║"
    echo "║                    AI-Powered EHR System                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        print_warning "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    local missing_deps=()
    
    # Check Python
    if ! command_exists python3; then
        missing_deps+=("python3")
    else
        python_version=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python $python_version found"
    fi
    
    # Check Node.js
    if ! command_exists node; then
        missing_deps+=("nodejs")
    else
        node_version=$(node --version)
        print_success "Node.js $node_version found"
    fi
    
    # Check npm
    if ! command_exists npm; then
        missing_deps+=("npm")
    else
        npm_version=$(npm --version)
        print_success "npm $npm_version found"
    fi
    
    # Check PostgreSQL
    if ! command_exists psql; then
        print_warning "PostgreSQL not found - will use Docker"
    else
        print_success "PostgreSQL found"
    fi
    
    # Check Redis
    if ! command_exists redis-cli; then
        print_warning "Redis not found - will use Docker"
    else
        print_success "Redis found"
    fi
    
    # Check Docker (optional but recommended)
    if command_exists docker; then
        print_success "Docker found (optional)"
    fi
    
    # Report missing dependencies
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo "Please install them first:"
        echo "  macOS: brew install ${missing_deps[*]}"
        echo "  Ubuntu: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

# Stop all services on required ports
stop_existing_services() {
    print_status "Stopping existing services..."
    
    # Kill processes on specific ports
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    kill_port $POSTGRES_PORT
    kill_port $REDIS_PORT
    
    # Stop any running Docker containers from this project
    if command_exists docker; then
        docker-compose down 2>/dev/null || true
    fi
    
    print_success "All ports cleared"
}

# Setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Verify virtual environment is active
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment activated: $(which python)"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    # Install requirements
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Install agent dependencies
    print_status "Installing OpenAI Agents SDK..."
    pip install openai-agents >/dev/null 2>&1 || print_warning "OpenAI Agents SDK already installed"
    
    print_success "Python environment ready"
    cd ..
}

# Setup Node.js environment
setup_node_env() {
    print_status "Setting up Node.js environment..."
    
    cd frontend
    
    # Install dependencies if node_modules doesn't exist or package.json is newer
    if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
        print_status "Installing Node.js dependencies..."
        npm install
        print_success "Node.js dependencies installed"
    else
        print_success "Node.js dependencies up to date"
    fi
    
    cd ..
}

# Setup databases
setup_databases() {
    print_status "Setting up databases..."
    
    # Check if we should use Docker for databases
    use_docker=false
    if ! command_exists psql || ! command_exists redis-cli; then
        if command_exists docker; then
            use_docker=true
            print_status "Using Docker for databases..."
            
            # Start only database services with docker-compose
            docker-compose up -d postgres redis
            
            # Wait for services to be ready
            print_status "Waiting for databases to start..."
            sleep 5
            
            # Create database if it doesn't exist
            docker-compose exec -T postgres psql -U medscribe -d medical_scribe_db -c "SELECT 1" >/dev/null 2>&1 || \
            docker-compose exec -T postgres createdb -U medscribe medical_scribe_db 2>/dev/null || true
            
            print_success "Docker databases started"
        else
            print_error "PostgreSQL or Redis not found and Docker is not available"
            print_error "Please install PostgreSQL and Redis or Docker"
            exit 1
        fi
    else
        # Use local PostgreSQL and Redis
        print_status "Using local PostgreSQL and Redis..."
        
        # Start PostgreSQL if not running
        if ! pg_isready -q; then
            print_status "Starting PostgreSQL..."
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew services start postgresql 2>/dev/null || true
            else
                sudo systemctl start postgresql 2>/dev/null || true
            fi
        fi
        
        # Start Redis if not running
        if ! redis-cli ping >/dev/null 2>&1; then
            print_status "Starting Redis..."
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew services start redis 2>/dev/null || true
            else
                sudo systemctl start redis 2>/dev/null || true
            fi
        fi
        
        # Create database if it doesn't exist
        createdb medical_scribe_db 2>/dev/null || true
        
        print_success "Local databases ready"
    fi
}

# Create .env files if they don't exist
setup_env_files() {
    print_status "Setting up environment files..."
    
    # Backend .env
    if [ ! -f "backend/.env" ]; then
        print_status "Creating backend .env file..."
        cp backend/.env.example backend/.env
        print_warning "Please edit backend/.env and add your API keys"
    fi
    
    # Frontend .env
    if [ ! -f "frontend/.env" ]; then
        print_status "Creating frontend .env file..."
        cat > frontend/.env << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
REACT_APP_EPIC_REDIRECT_URI=https://localhost:3000/callback
EOF
        print_success "Frontend .env created"
    fi
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    cd backend
    source venv/bin/activate
    
    # Initialize alembic if needed
    if [ ! -d "alembic/versions" ]; then
        alembic init alembic 2>/dev/null || true
    fi
    
    # Run migrations - use Docker database if available
    if docker-compose ps postgres | grep -q "Up"; then
        DATABASE_URL="postgresql://medscribe:medscribe_password@localhost:5432/medical_scribe_db" \
        python -c "from app.db.session import engine; from app.db.base_class import Base; Base.metadata.create_all(bind=engine)" || {
            print_warning "Migration failed - database might not be ready yet"
        }
    else
        python -c "from app.db.session import engine; from app.db.base_class import Base; Base.metadata.create_all(bind=engine)" || {
            print_warning "Migration failed - database might not be ready yet"
        }
    fi
    
    cd ..
    print_success "Database migrations complete"
}

# Start backend server
start_backend() {
    print_status "Starting backend server..."
    
    cd backend
    
    # Ensure virtual environment is activated
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found. Run setup first."
        exit 1
    fi
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_error "Virtual environment not activated"
        exit 1
    fi
    
    # Export environment for agent system
    export PYTHONPATH="$PWD:$PYTHONPATH"
    
    # Start uvicorn in background
    uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    
    cd ..
    print_success "Backend started with venv (PID: $BACKEND_PID)"
    echo $BACKEND_PID > .backend.pid
}

# Start frontend server
start_frontend() {
    print_status "Starting frontend server..."
    
    cd frontend
    
    # Clear build cache if exists
    if [ -d "build" ]; then
        print_status "Clearing build cache..."
        rm -rf build
    fi
    
    # Clear node modules cache
    if [ -d "node_modules/.cache" ]; then
        print_status "Clearing node modules cache..."
        rm -rf node_modules/.cache
    fi
    
    # Check if HTTPS certificates exist
    if [ -f "certificates/localhost.crt" ] && [ -f "certificates/localhost.key" ]; then
        print_status "Starting frontend with HTTPS..."
        HTTPS=true SSL_CRT_FILE=certificates/localhost.crt SSL_KEY_FILE=certificates/localhost.key npm start > ../logs/frontend.log 2>&1 &
    else
        print_warning "HTTPS certificates not found, starting with HTTP..."
        print_warning "For Epic integration, run: cd frontend && mkdir certificates && openssl req -x509 -newkey rsa:4096 -keyout certificates/localhost.key -out certificates/localhost.crt -days 365 -nodes -subj '/CN=localhost'"
        npm start > ../logs/frontend.log 2>&1 &
    fi
    
    FRONTEND_PID=$!
    
    cd ..
    print_success "Frontend started (PID: $FRONTEND_PID)"
    echo $FRONTEND_PID > .frontend.pid
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for backend
    local retries=30
    while [ $retries -gt 0 ]; do
        if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
            print_success "Backend is ready"
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done
    
    if [ $retries -eq 0 ]; then
        print_error "Backend failed to start"
        cleanup
        exit 1
    fi
    
    # Test agent system
    if curl -s http://localhost:$BACKEND_PORT/api/v2/agent/status >/dev/null 2>&1; then
        print_success "Agent system is ready"
    else
        print_warning "Agent system endpoint not responding"
    fi
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    
    # Kill backend
    if [ -f .backend.pid ]; then
        kill $(cat .backend.pid) 2>/dev/null || true
        rm .backend.pid
    fi
    
    # Kill frontend
    if [ -f .frontend.pid ]; then
        kill $(cat .frontend.pid) 2>/dev/null || true
        rm .frontend.pid
    fi
    
    # Stop Docker containers if used
    if command_exists docker; then
        docker-compose down 2>/dev/null || true
    fi
}

# Trap cleanup on exit
trap cleanup EXIT INT TERM

# Show status
show_status() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Medical Scribe Application is running!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BLUE}Backend API:${NC}     http://localhost:$BACKEND_PORT"
    echo -e "  ${BLUE}Frontend:${NC}        http://localhost:$FRONTEND_PORT"
    echo -e "  ${BLUE}API Docs:${NC}        http://localhost:$BACKEND_PORT/docs"
    echo -e "  ${BLUE}Health Check:${NC}    http://localhost:$BACKEND_PORT/health"
    echo -e "  ${BLUE}Agent Status:${NC}    http://localhost:$BACKEND_PORT/api/v2/agent/status"
    echo ""
    echo -e "  ${YELLOW}Logs:${NC}"
    echo -e "    Backend:  tail -f logs/backend.log"
    echo -e "    Frontend: tail -f logs/frontend.log"
    echo ""
    echo -e "  ${YELLOW}Stop:${NC} Press Ctrl+C to stop all services"
    echo ""
    
    if [ ! -f "backend/.env" ] || grep -q "your-secret-key-here\|your-openai-api-key" "backend/.env"; then
        echo -e "  ${RED}⚠️  WARNING:${NC} Please update backend/.env with your API keys"
        echo ""
    fi
}

# Test agent system
test_agents() {
    print_status "Testing agent system..."
    
    cd backend
    
    # Ensure virtual environment is activated
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found"
        return 1
    fi
    
    # Run agent tests
    if [ -f "app/agents/simple_transcription_agent.py" ]; then
        print_status "Running simple agent test..."
        python app/agents/simple_transcription_agent.py
    else
        print_warning "Agent test file not found"
    fi
    
    cd ..
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --quick, -q       Quick start (skip dependency updates)"
    echo "  --test-agents     Test the agent system"
    echo "  --backend-only    Start only the backend server"
    echo "  --frontend-only   Start only the frontend server"
    echo ""
    echo "Examples:"
    echo "  $0                Full setup and start"
    echo "  $0 --quick        Quick start without updates"
    echo "  $0 --test-agents  Test agent functionality"
}

# Main execution
main() {
    # Parse command line arguments
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --test-agents)
            print_banner
            test_agents
            exit 0
            ;;
        --backend-only)
            print_banner
            mkdir -p logs
            stop_existing_services
            setup_python_env
            start_backend
            wait_for_services
            show_status
            ;;
        --frontend-only)
            print_banner
            mkdir -p logs
            kill_port $FRONTEND_PORT
            setup_node_env
            start_frontend
            show_status
            ;;
        --quick|-q)
            print_banner
            mkdir -p logs
            print_status "Quick start mode - skipping dependency updates"
            stop_existing_services
            start_backend
            start_frontend
            wait_for_services
            show_status
            ;;
        *)
            print_banner
            # Create logs directory
            mkdir -p logs
            
            # Run all setup steps
            check_requirements
            stop_existing_services
            setup_env_files
            setup_databases
            setup_python_env
            setup_node_env
            run_migrations
            start_backend
            start_frontend
            wait_for_services
            show_status
            ;;
    esac
    
    # Keep script running (except for test-agents)
    if [[ "$1" != "--test-agents" ]]; then
        print_status "Press Ctrl+C to stop all services..."
        
        # Wait indefinitely
        while true; do
            sleep 1
        done
    fi
}

# Run main function with all arguments
main "$@"