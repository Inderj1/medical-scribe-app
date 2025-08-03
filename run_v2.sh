#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Medical Scribe Application v2 (OpenAI Agents SDK)${NC}"
echo "=================================================="

# Parse command line arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false
SKIP_DOCKER=false

for arg in "$@"
do
    case $arg in
        --backend-only)
        BACKEND_ONLY=true
        shift
        ;;
        --frontend-only)
        FRONTEND_ONLY=true
        shift
        ;;
        --skip-docker)
        SKIP_DOCKER=true
        shift
        ;;
        *)
        # unknown option
        ;;
    esac
done

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill backend if it's running
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Kill frontend if it's running
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # Stop Docker services if we started them
    if [ "$SKIP_DOCKER" = false ] && [ "$FRONTEND_ONLY" = false ]; then
        echo "Stopping Docker services..."
        docker-compose stop postgres redis
    fi
    
    exit 0
}

# Set up trap to cleanup on Ctrl+C
trap cleanup INT

# Start Docker services (PostgreSQL and Redis) if not skipped
if [ "$SKIP_DOCKER" = false ] && [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${BLUE}Starting Docker services (PostgreSQL and Redis)...${NC}"
    docker-compose up -d postgres redis
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U medscribe >/dev/null 2>&1; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
fi

# Start Backend
if [ "$FRONTEND_ONLY" = false ]; then
    # Check if backend is already running
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}Backend is already running on port 8000${NC}"
        echo "Stopping existing backend..."
        kill $(lsof -Pi :8000 -sTCP:LISTEN -t)
        sleep 2
    fi

    echo -e "${GREEN}Starting backend v2...${NC}"
    cd backend

    # Export environment variables
    export PYTHONPATH=/Users/jay/Cloudmantra_code/medical-scribe-app/backend:$PYTHONPATH

    # Activate virtual environment and start with the v2 main file
    source venv/bin/activate
    python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!

    echo -e "${GREEN}Backend v2 started with PID: $BACKEND_PID${NC}"
    echo "Waiting for backend to be ready..."
    
    # Wait for backend to be ready
    for i in {1..30}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}Backend is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    
    # Test the API
    echo -e "${GREEN}Testing API endpoints...${NC}"
    curl -s http://localhost:8000/health | jq .
    
    cd ..
fi

# Start Frontend
if [ "$BACKEND_ONLY" = false ]; then
    # Check if frontend is already running
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}Frontend is already running on port 3000${NC}"
        echo "Stopping existing frontend..."
        kill $(lsof -Pi :3000 -sTCP:LISTEN -t)
        sleep 2
    fi

    echo -e "${GREEN}Starting frontend...${NC}"
    cd frontend
    
    # Check if .env file exists, if not create it
    if [ ! -f .env ]; then
        echo "REACT_APP_API_URL=http://localhost:8000" > .env
        echo "Created frontend .env file"
    fi
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    
    # Start frontend
    npm start &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"
    cd ..
fi

# Summary
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Medical Scribe v2 is running!${NC}"
echo -e "${GREEN}======================================${NC}"

if [ "$SKIP_DOCKER" = false ] && [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${BLUE}Docker Services:${NC}"
    echo "  PostgreSQL: localhost:5432"
    echo "  Redis: localhost:6379"
fi

if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${BLUE}Backend:${NC}"
    echo "  API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
fi

if [ "$BACKEND_ONLY" = false ]; then
    echo -e "${BLUE}Frontend:${NC}"
    echo "  Web App: http://localhost:3000"
fi

echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for services
if [ "$FRONTEND_ONLY" = false ] && [ "$BACKEND_ONLY" = false ]; then
    # Wait for both
    wait $BACKEND_PID $FRONTEND_PID
elif [ "$FRONTEND_ONLY" = false ]; then
    # Wait for backend only
    wait $BACKEND_PID
elif [ "$BACKEND_ONLY" = false ]; then
    # Wait for frontend only
    wait $FRONTEND_PID
fi