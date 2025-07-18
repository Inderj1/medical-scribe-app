# Medical Scribe Real-Time Application

A real-time medical documentation system that receives audio from mobile devices, transcribes it using AI, and displays structured clinical notes in a web interface.

## Features

- **Real-time Audio Transcription**: Stream audio from mobile devices and get instant transcription using OpenAI Whisper
- **Clinical Entity Extraction**: Automatically extract medical entities (symptoms, diagnoses, medications) using AI
- **Live Updates**: WebSocket-based real-time updates for transcriptions, vitals, and clinical notes
- **Structured Documentation**: Organize transcriptions into clinical sections (History, Examination, Assessment, Plan)
- **Multi-user Support**: Handle multiple concurrent sessions with authentication
- **Export Capabilities**: Export encounters as PDF, HL7, or FHIR formats
- **EHR Integration**: Connect with Epic, Cerner, and other major EHR systems via FHIR APIs
- **Patient Data Sync**: Import patient demographics, medications, allergies, and conditions from EHR
- **Real-time Vitals**: Pull latest vital signs from connected EHR systems

## Architecture

```
Mobile App → WebSocket → Backend (FastAPI) → AI Services → Frontend (React)
                            ↓                      ↓
                      PostgreSQL + Redis     OpenAI Whisper + Claude
```

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **WebSocket** - Real-time bidirectional communication
- **PostgreSQL** - Primary database for patient and encounter data
- **Redis** - Session management and caching
- **SQLAlchemy** - ORM for database operations
- **OpenAI Whisper** - Audio transcription
- **Anthropic Claude** - Clinical entity extraction

### Frontend
- **React 18** with TypeScript
- **Material-UI** - Component library
- **Socket.io-client** - WebSocket client
- **Redux Toolkit** - State management
- **React Query** - Data fetching and caching

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- OpenAI API key
- Anthropic API key (optional)

## Quick Start

### One-Command Setup

The easiest way to get started is using the automated setup script:

```bash
# Clone and start everything
git clone <repository-url>
cd medical-scribe-app

# Run the complete setup (handles everything automatically)
./run.sh
```

This script will:
- Check system requirements
- Stop any conflicting services
- Set up Python virtual environment
- Install all dependencies
- Set up databases (PostgreSQL + Redis)
- Create environment files
- Run database migrations
- Start backend and frontend servers

### Manual Installation

If you prefer manual setup:

### Backend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd medical-scribe-app
```

2. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up the database:
```bash
# Create PostgreSQL database
createdb medical_scribe_db

# Run migrations
alembic upgrade head
```

6. Start the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd ../frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the development server:
```bash
npm start
```

The application will be available at http://localhost:3000

## Management Scripts

The project includes several convenience scripts:

### Main Scripts

```bash
# Start everything (complete setup and launch)
./run.sh

# Stop all services
./stop.sh

# Check status of all services
./status.sh
```

### Individual Services

```bash
# Backend only
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm start

# Databases with Docker
docker-compose up -d postgres redis
```

### Logs

```bash
# View real-time logs
tail -f logs/backend.log
tail -f logs/frontend.log

# All logs
tail -f logs/*.log
```

## Usage

### Starting a Session

1. **Login**: Access the web interface and login with your credentials
2. **Select Patient**: Choose or create a patient record
3. **Start Encounter**: Click "New Encounter" to begin a session
4. **Connect Mobile**: Use the mobile app to connect and start streaming audio
5. **Real-time Transcription**: Speak into the mobile device and watch live transcription
6. **Review & Edit**: Edit the structured notes as needed
7. **Sign & Close**: Sign the encounter to finalize documentation

### Mobile App Connection

The mobile app connects via WebSocket to stream audio:

```javascript
// Mobile app connection example
const socket = io('ws://your-server:8000/ws/audio-stream', {
  auth: { token: 'your-jwt-token' }
});

// Stream audio chunks
socket.emit('audio:stream', {
  audio_chunk: base64AudioData
});
```

## API Documentation

### REST Endpoints

- `POST /api/auth/login` - Authenticate user
- `POST /api/auth/register` - Register new user
- `GET /api/patients` - List patients
- `POST /api/encounters` - Create new encounter
- `GET /api/encounters/{id}` - Get encounter details
- `PUT /api/encounters/{id}/notes` - Update clinical notes

### EHR Integration Endpoints

- `POST /api/ehr/connections` - Create EHR connection
- `GET /api/ehr/connections` - List EHR connections
- `POST /api/ehr/connections/{id}/test` - Test EHR connection
- `POST /api/ehr/search/patients` - Search patients in EHR
- `POST /api/ehr/sync/patient` - Sync patient from EHR
- `GET /api/ehr/patient/{id}/refresh` - Refresh patient data
- `GET /api/ehr/patient/{id}/encounters` - Get patient encounters from EHR
- `GET /api/ehr/patient/{id}/vitals/latest` - Get latest vitals from EHR

### WebSocket Events

**Client → Server:**
- `audio:stream` - Stream audio chunks
- `encounter:start` - Start new encounter
- `encounter:end` - End current encounter
- `vitals:update` - Update vital signs

**Server → Client:**
- `transcription:partial` - Partial transcription update
- `transcription:final` - Final transcription
- `notes:update` - Clinical notes update
- `vitals:update` - Vitals update

## Project Structure

```
medical-scribe-app/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core functionality
│   │   ├── db/           # Database configuration
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── main.py       # Application entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── services/     # API services
│   │   ├── hooks/        # Custom hooks
│   │   ├── store/        # Redux store
│   │   └── App.tsx       # Main application
│   └── package.json
└── docs/
    ├── ARCHITECTURE.md
    └── IMPLEMENTATION_PLAN.md
```

## Development

### Running Tests

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm test
```

### Code Quality

Backend:
```bash
# Format code
black app/

# Lint
flake8 app/

# Type checking
mypy app/
```

Frontend:
```bash
# Lint
npm run lint

# Type checking
npm run type-check
```

## Deployment

### Docker Deployment

1. Build images:
```bash
docker-compose build
```

2. Run services:
```bash
docker-compose up -d
```

### Production Considerations

- Use HTTPS/WSS for all connections
- Enable CORS only for trusted domains
- Implement rate limiting
- Set up monitoring and logging
- Configure backup strategies
- Ensure HIPAA compliance

## Security

- JWT-based authentication
- Encrypted connections (TLS/SSL)
- Input validation and sanitization
- Role-based access control (RBAC)
- Audit logging for all actions
- Data encryption at rest

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Contact the development team at support@medicalscribe.com

## Acknowledgments

- OpenAI for Whisper API
- Anthropic for Claude API
- FastAPI team for the excellent framework
- React and Material-UI teams