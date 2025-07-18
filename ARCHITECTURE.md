# Medical Scribe Real-Time Application Architecture

## Overview
A real-time medical documentation system that receives audio from mobile devices, transcribes it using AI, and displays structured clinical notes in a web interface.

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Material-UI** for component library
- **Socket.io-client** for WebSocket connections
- **Redux Toolkit** for state management
- **React Query** for data fetching
- **Chart.js** for vitals visualization

### Backend
- **FastAPI** (Python 3.11+) for REST API and WebSocket
- **SQLAlchemy** ORM with Alembic migrations
- **Pydantic** for data validation
- **Celery** for background tasks
- **Redis** for caching and session management

### Databases
- **PostgreSQL** - Primary database for:
  - Patient records
  - Encounter data
  - Transcriptions
  - Clinical notes
- **Redis** - For:
  - Session management
  - Real-time data caching
  - WebSocket connection tracking
  - Audio buffer management

### AI/ML Services
- **OpenAI Whisper API** - Audio transcription
- **Claude API** or **GPT-4** - Clinical entity extraction and note structuring
- **spaCy** with medical models - NLP processing

### Infrastructure
- **Docker** & **Docker Compose** for containerization
- **Nginx** for reverse proxy
- **MinIO** for audio file storage

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Mobile App    │     │   Web Client    │     │  Admin Portal   │
│   (React Native)│     │     (React)     │     │     (React)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         │ Audio Stream          │ WebSocket               │ HTTPS
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway (Nginx)                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  WebSocket  │  │   REST API   │  │  Background Tasks  │    │
│  │   Handler   │  │   Endpoints  │  │     (Celery)       │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐
│  Audio Service  │  │   Database   │  │   AI Services      │
│  - Whisper API  │  │  PostgreSQL  │  │  - Claude/GPT-4    │
│  - Processing   │  │    Redis     │  │  - spaCy Medical   │
└─────────────────┘  └──────────────┘  └────────────────────┘
```

## Data Flow

1. **Audio Capture**: Mobile app captures audio via microphone
2. **Streaming**: Audio chunks sent via WebSocket to backend
3. **Transcription**: Audio processed by Whisper API in real-time
4. **NLP Processing**: Transcribed text analyzed for medical entities
5. **Structuring**: AI structures text into clinical sections
6. **Broadcasting**: Updates sent to web client via WebSocket
7. **Display**: React components update in real-time

## Database Schema

### PostgreSQL Tables

```sql
-- Patients
CREATE TABLE patients (
    id UUID PRIMARY KEY,
    mrn VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Encounters
CREATE TABLE encounters (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    encounter_date TIMESTAMP DEFAULT NOW(),
    chief_complaint TEXT,
    status VARCHAR(50) DEFAULT 'active',
    provider_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transcriptions
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES encounters(id),
    audio_url TEXT,
    raw_text TEXT,
    processed_text JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Clinical Notes
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES encounters(id),
    section_type VARCHAR(50), -- 'history', 'examination', 'assessment', 'plan'
    content JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vitals
CREATE TABLE vitals (
    id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES encounters(id),
    measurement_time TIMESTAMP DEFAULT NOW(),
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    heart_rate INTEGER,
    respiratory_rate INTEGER,
    temperature DECIMAL(4,1),
    oxygen_saturation INTEGER,
    pain_level INTEGER
);
```

### Redis Structure

```
# WebSocket connections
ws:connections:{user_id} -> {connection_id, timestamp}

# Active encounters
encounter:active:{encounter_id} -> {patient_data, start_time}

# Audio buffers
audio:buffer:{session_id} -> [audio_chunks]

# Transcription cache
transcription:cache:{encounter_id} -> {recent_transcriptions}
```

## API Endpoints

### REST API

```
POST   /api/auth/login              # Authenticate user
POST   /api/auth/logout             # Logout user
GET    /api/patients               # List patients
GET    /api/patients/{id}          # Get patient details
POST   /api/encounters             # Create new encounter
GET    /api/encounters/{id}        # Get encounter details
PUT    /api/encounters/{id}        # Update encounter
POST   /api/encounters/{id}/vitals # Add vitals
GET    /api/encounters/{id}/notes  # Get clinical notes
PUT    /api/encounters/{id}/notes  # Update notes
POST   /api/encounters/{id}/sign   # Sign and close encounter
```

### WebSocket Events

```
Client → Server:
- audio:stream        # Stream audio chunks
- encounter:start     # Start new encounter
- encounter:end       # End current encounter
- vitals:update       # Update vital signs

Server → Client:
- transcription:partial   # Partial transcription update
- transcription:final     # Final transcription
- notes:update           # Clinical notes update
- vitals:update          # Vitals update
- connection:status      # Connection status
```

## Security Considerations

1. **Authentication**: JWT tokens with refresh mechanism
2. **HTTPS/WSS**: All connections encrypted
3. **HIPAA Compliance**: 
   - Data encryption at rest and in transit
   - Audit logging for all access
   - Role-based access control (RBAC)
4. **Input Validation**: Strict validation on all inputs
5. **Rate Limiting**: Prevent abuse of API endpoints

## Performance Optimization

1. **Audio Buffering**: Buffer audio chunks before processing
2. **Batch Processing**: Process multiple transcriptions together
3. **Caching**: Redis caching for frequent queries
4. **Connection Pooling**: Database connection pooling
5. **CDN**: Static assets served via CDN
6. **Horizontal Scaling**: Support for multiple backend instances

## Deployment Strategy

1. **Development**: Docker Compose for local development
2. **Staging**: Kubernetes cluster with auto-scaling
3. **Production**: 
   - Blue-green deployment
   - Health checks and monitoring
   - Automated backups
   - Disaster recovery plan