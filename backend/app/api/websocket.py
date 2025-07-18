from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Set
import json
import asyncio
import logging
from datetime import datetime
import uuid

from app.core.config import settings
from app.services.audio_processor import AudioProcessor
from app.services.transcription_service import TranscriptionService
from app.services.clinical_nlp import ClinicalNLPService
from app.db.session import get_db, get_redis
from app.core.auth import get_current_user_ws

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_encounters: Dict[str, str] = {}  # user_id -> encounter_id
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket")
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")
        
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    
    async def broadcast_to_encounter(self, message: dict, encounter_id: str):
        # Find all users connected to this encounter
        for user_id, enc_id in self.user_encounters.items():
            if enc_id == encounter_id:
                await self.send_personal_message(message, user_id)


manager = ConnectionManager()


@router.websocket("/audio-stream")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db=Depends(get_db),
    redis=Depends(get_redis)
):
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
        
    user_id = str(user.id)
    await manager.connect(websocket, user_id)
    
    # Initialize services
    audio_processor = AudioProcessor(redis)
    transcription_service = TranscriptionService()
    nlp_service = ClinicalNLPService()
    
    # Send initial connection status
    await websocket.send_json({
        "type": "connection:status",
        "status": "connected",
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "encounter:start":
                # Start new encounter
                encounter_id = data.get("encounter_id")
                patient_id = data.get("patient_id")
                
                manager.user_encounters[user_id] = encounter_id
                
                await websocket.send_json({
                    "type": "encounter:started",
                    "encounter_id": encounter_id,
                    "status": "recording"
                })
                
            elif message_type == "audio:stream":
                # Handle audio streaming
                audio_chunk = data.get("audio_chunk")  # Base64 encoded audio
                encounter_id = manager.user_encounters.get(user_id)
                
                if not encounter_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active encounter"
                    })
                    continue
                
                # Process audio chunk
                session_id = f"{user_id}_{encounter_id}"
                await audio_processor.add_chunk(session_id, audio_chunk)
                
                # Check if we have enough audio to transcribe
                if await audio_processor.should_transcribe(session_id):
                    audio_data = await audio_processor.get_audio_buffer(session_id)
                    
                    # Transcribe audio
                    transcription = await transcription_service.transcribe(audio_data)
                    
                    # Send partial transcription
                    await manager.broadcast_to_encounter({
                        "type": "transcription:partial",
                        "text": transcription.text,
                        "confidence": transcription.confidence,
                        "timestamp": datetime.utcnow().isoformat()
                    }, encounter_id)
                    
                    # Process with NLP
                    clinical_data = await nlp_service.extract_clinical_entities(transcription.text)
                    
                    # Send structured clinical data
                    await manager.broadcast_to_encounter({
                        "type": "notes:update",
                        "section": clinical_data.section,
                        "content": clinical_data.content,
                        "entities": clinical_data.entities
                    }, encounter_id)
                    
                    # Clear processed audio buffer
                    await audio_processor.clear_buffer(session_id)
                    
            elif message_type == "encounter:end":
                # End encounter
                encounter_id = manager.user_encounters.get(user_id)
                if encounter_id:
                    # Process any remaining audio
                    session_id = f"{user_id}_{encounter_id}"
                    remaining_audio = await audio_processor.get_audio_buffer(session_id)
                    
                    if remaining_audio:
                        transcription = await transcription_service.transcribe(remaining_audio)
                        
                        await manager.broadcast_to_encounter({
                            "type": "transcription:final",
                            "text": transcription.text,
                            "timestamp": datetime.utcnow().isoformat()
                        }, encounter_id)
                    
                    # Clean up
                    await audio_processor.cleanup_session(session_id)
                    del manager.user_encounters[user_id]
                    
                    await websocket.send_json({
                        "type": "encounter:ended",
                        "encounter_id": encounter_id
                    })
                    
            elif message_type == "vitals:update":
                # Update vitals
                encounter_id = manager.user_encounters.get(user_id)
                vitals_data = data.get("vitals")
                
                if encounter_id:
                    await manager.broadcast_to_encounter({
                        "type": "vitals:update",
                        "vitals": vitals_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }, encounter_id)
                    
            elif message_type == "ping":
                # Heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        # Clean up any active sessions
        if user_id in manager.user_encounters:
            session_id = f"{user_id}_{manager.user_encounters[user_id]}"
            await audio_processor.cleanup_session(session_id)
            del manager.user_encounters[user_id]
            
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
        await websocket.close(code=4000, reason="Internal error")