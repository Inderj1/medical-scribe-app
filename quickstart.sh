#!/bin/bash

# Medical Scribe App Quick Start Script

echo "🏥 Medical Scribe App - Quick Start"
echo "=================================="

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install $1 first."
        exit 1
    fi
    echo "✅ $1 is installed"
}

echo "Checking prerequisites..."
check_command python3
check_command node
check_command npm
check_command docker
check_command docker-compose

# Create .env files if they don't exist
if [ ! -f backend/.env ]; then
    echo "Creating backend .env file..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please edit backend/.env and add your API keys"
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend .env file..."
    cat > frontend/.env << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
EOF
fi

# Ask user for setup method
echo ""
echo "How would you like to run the application?"
echo "1) Docker (recommended)"
echo "2) Local development"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "Starting with Docker..."
        docker-compose up -d
        echo ""
        echo "✅ Application is starting..."
        echo "   Backend: http://localhost:8000"
        echo "   Frontend: http://localhost:3000"
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop: docker-compose down"
        ;;
    2)
        echo "Starting local development setup..."
        
        # Backend setup
        echo "Setting up backend..."
        cd backend
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        
        # Start backend in background
        echo "Starting backend server..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        
        # Frontend setup
        echo "Setting up frontend..."
        cd ../frontend
        npm install
        
        # Start frontend
        echo "Starting frontend server..."
        npm start &
        FRONTEND_PID=$!
        
        echo ""
        echo "✅ Application is running!"
        echo "   Backend: http://localhost:8000 (PID: $BACKEND_PID)"
        echo "   Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
        echo ""
        echo "To stop: kill $BACKEND_PID $FRONTEND_PID"
        
        # Wait for user input
        read -p "Press Enter to stop servers..."
        kill $BACKEND_PID $FRONTEND_PID
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac