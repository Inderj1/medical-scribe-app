import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.config import settings
from app.db.session import get_db, get_redis
from app.core.auth import get_current_user_ws
from app.core.clerk_auth import get_clerk_user_ws

# Import enhanced services
from app.services.enhanced_transcription_service import (
    EnhancedWhisperClient, TranscriptionJob, TranscriptionResult
)
from app.services.enhanced_clinical_nlp import EnhancedAnthropicClient, ClinicalAnalysis
from app.services.transcription_queue import TranscriptionQueue
from app.services.client_manager import ClientManager
from app.services.audio_processor import AudioProcessor
from app.services.openehr_service import get_openehr_service

# Import new agent services
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.ehr_prefill_service import EHRPrefillService

logger = logging.getLogger(__name__)

router = APIRouter()


class MedicalScribeServer:
    def __init__(self):
        self.whisper_client = EnhancedWhisperClient()
        self.anthropic_client = EnhancedAnthropicClient()
        self.client_manager = ClientManager()
        self.transcription_queue = TranscriptionQueue(get_redis())
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.is_running = True
        
        # Initialize new agent services
        self.agent_orchestrator = AgentOrchestrator()
        self.ehr_prefill_service = EHRPrefillService()
        
        # Performance metrics
        self.metrics = {
            "total_transcriptions": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "average_processing_time": 0.0,
            "active_connections": 0,
            "start_time": time.time()
        }
        
        # Clinical notes storage per encounter
        self.encounter_notes: Dict[str, Dict] = {}
        self.clinical_analyses: Dict[str, list] = {}  # Store analyses per encounter
        
        # Start background tasks
        asyncio.create_task(self._process_transcription_queue())
        asyncio.create_task(self._send_periodic_metrics())
    
    async def handle_connection(self, websocket: WebSocket, user_id: str, metadata: Dict = None):
        """Handle new WebSocket client connection"""
        await self.client_manager.connect(websocket, user_id, metadata)
        self.metrics["active_connections"] += 1
        
        # Initialize audio processor for this connection
        audio_processor = AudioProcessor(get_redis())
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                await self.handle_client_message(user_id, data, audio_processor)
                
        except WebSocketDisconnect:
            logger.info(f"Client {user_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {user_id}: {str(e)}")
        finally:
            self.client_manager.disconnect(websocket, user_id)
            self.metrics["active_connections"] -= 1
            
            # Cleanup any active sessions
            encounter_id = self.client_manager.get_encounter(user_id)
            if encounter_id:
                session_id = f"{user_id}_{encounter_id}"
                await audio_processor.cleanup_session(session_id)
    
    async def handle_client_message(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle incoming message from client"""
        message_type = message.get("type")
        
        handlers = {
            "encounter:start": self._handle_encounter_start,
            "encounter:end": self._handle_encounter_end,
            "audio:stream": self._handle_audio_stream,
            "transcription": self._handle_transcription_request,
            "notes:update": self._handle_notes_update,
            "settings:update": self._handle_settings_update,
            "vitals:update": self._handle_vitals_update,
            "get:status": self._handle_get_status,
            "ping": self._handle_ping,
            # New handlers for agent-based system
            "clinical_notes:start": self._handle_clinical_notes_start,
            "format:update": self._handle_format_update,
            "section:focus": self._handle_section_focus
        }
        
        handler = handlers.get(message_type)
        if handler:
            await handler(user_id, message, audio_processor)
        else:
            logger.warning(f"Unknown message type from client {user_id}: {message_type}")
    
    async def _handle_encounter_start(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle encounter start"""
        encounter_id = message.get("encounter_id")
        patient_id = message.get("patient_id")
        encounter_type = message.get("encounter_type", "general")
        note_format = message.get("note_format", "long")
        
        # Set up client state
        self.client_manager.set_encounter(user_id, encounter_id)
        self.client_manager.set_note_format(user_id, note_format)
        
        # Initialize encounter storage
        self.encounter_notes[encounter_id] = {}
        self.clinical_analyses[encounter_id] = []
        
        # Clear previous context for new encounter
        self.client_manager.clear_context(user_id)
        
        await self.client_manager.send_to_client(user_id, {
            "type": "encounter:started",
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "encounter_type": encounter_type,
            "note_format": note_format,
            "status": "recording",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_encounter_end(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle encounter end"""
        encounter_id = self.client_manager.get_encounter(user_id)
        if not encounter_id:
            return
        
        # Process any remaining audio
        session_id = f"{user_id}_{encounter_id}"
        remaining_audio = await audio_processor.get_audio_buffer(session_id)
        
        if remaining_audio:
            job = TranscriptionJob(
                id=str(uuid.uuid4()),
                audio_data=remaining_audio,
                timestamp=datetime.utcnow().isoformat(),
                client_id=user_id
            )
            self.transcription_queue.add_job(job, priority=0)  # High priority
        
        # Generate final clinical summary
        if encounter_id in self.clinical_analyses:
            analyses = self.clinical_analyses[encounter_id]
            note_format = self.client_manager.get_note_format(user_id)
            
            summary = await self.anthropic_client.generate_clinical_summary(
                analyses, note_format
            )
            
            await self.client_manager.send_to_client(user_id, {
                "type": "clinical:summary",
                "encounter_id": encounter_id,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Send to OpenEHR if configured
        if settings.OPENEHR_API_URL and encounter_id in self.encounter_notes:
            try:
                openehr_service = await get_openehr_service()
                patient_id = message.get("patient_id", "unknown")
                
                result = await openehr_service.create_composition(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    clinical_notes=self.encounter_notes[encounter_id],
                    vitals=message.get("vitals")
                )
                
                if "error" not in result:
                    logger.info(f"Successfully sent final composition to OpenEHR for encounter {encounter_id}")
                else:
                    logger.error(f"Failed to send final composition to OpenEHR: {result['error']}")
            except Exception as e:
                logger.error(f"Error sending final composition to OpenEHR: {str(e)}")
        
        # Clean up
        await audio_processor.cleanup_session(session_id)
        self.client_manager.set_encounter(user_id, None)
        
        # End encounter in orchestrator
        encounter_summary = self.agent_orchestrator.end_encounter(encounter_id)
        
        # Clean up encounter data
        if encounter_id in self.encounter_notes:
            del self.encounter_notes[encounter_id]
        if encounter_id in self.clinical_analyses:
            del self.clinical_analyses[encounter_id]
        
        await self.client_manager.send_to_client(user_id, {
            "type": "encounter:ended",
            "encounter_id": encounter_id,
            "summary": encounter_summary,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_audio_stream(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle audio streaming with enhanced processing"""
        audio_chunk = message.get("audio_chunk")  # Base64 encoded
        encounter_id = self.client_manager.get_encounter(user_id)
        
        if not encounter_id:
            await self.client_manager.send_to_client(user_id, {
                "type": "error",
                "message": "No active encounter",
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Process audio chunk
        session_id = f"{user_id}_{encounter_id}"
        await audio_processor.add_chunk(session_id, audio_chunk)
        
        # Check if we should transcribe
        should_transcribe = await audio_processor.should_transcribe(session_id)
        
        if should_transcribe:
            audio_data = await audio_processor.get_audio_buffer(session_id)
            
            # Create transcription job
            job = TranscriptionJob(
                id=str(uuid.uuid4()),
                audio_data=audio_data,
                timestamp=datetime.utcnow().isoformat(),
                client_id=user_id
            )
            
            # Add to queue
            self.transcription_queue.add_job(job)
            self.client_manager.add_transcription_job(user_id, job.id)
            
            # Send acknowledgment
            await self.client_manager.send_to_client(user_id, {
                "type": "transcription:queued",
                "job_id": job.id,
                "queue_status": self.transcription_queue.get_queue_status(),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Clear processed audio buffer
            await audio_processor.clear_buffer(session_id)
    
    async def _handle_transcription_request(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle direct transcription request"""
        audio_data = message.get("audio")  # Base64 encoded
        
        if not audio_data:
            return
        
        # Decode and create job
        import base64
        try:
            audio_bytes = base64.b64decode(audio_data)
            
            job = TranscriptionJob(
                id=message.get("id", str(uuid.uuid4())),
                audio_data=audio_bytes,
                timestamp=message.get("timestamp", datetime.utcnow().isoformat()),
                client_id=user_id
            )
            
            # Add to queue with priority
            priority = message.get("priority", 1)
            self.transcription_queue.add_job(job, priority)
            self.client_manager.add_transcription_job(user_id, job.id)
            
            # Send acknowledgment
            await self.client_manager.send_to_client(user_id, {
                "type": "transcription:queued",
                "job_id": job.id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling transcription request: {str(e)}")
            await self.client_manager.send_to_client(user_id, {
                "type": "transcription:error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_notes_update(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle notes update from frontend"""
        encounter_id = self.client_manager.get_encounter(user_id)
        section = message.get("section")
        content = message.get("content")
        
        if encounter_id and section:
            # Store notes
            if encounter_id not in self.encounter_notes:
                self.encounter_notes[encounter_id] = {}
            
            if section not in self.encounter_notes[encounter_id]:
                self.encounter_notes[encounter_id][section] = {"text": "", "entities": []}
            
            # Update content
            if isinstance(content, dict):
                if content.get("action") == "append":
                    self.encounter_notes[encounter_id][section]["text"] += "\n" + content.get("text", "")
                else:
                    self.encounter_notes[encounter_id][section]["text"] = content.get("text", "")
            
            # Broadcast update
            await self.client_manager.broadcast_to_encounter({
                "type": "notes:update",
                "section": section,
                "content": self.encounter_notes[encounter_id][section],
                "timestamp": datetime.utcnow().isoformat()
            }, encounter_id)
    
    async def _handle_settings_update(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle settings update"""
        if "noteFormat" in message:
            self.client_manager.set_note_format(user_id, message["noteFormat"])
        
        await self.client_manager.send_to_client(user_id, {
            "type": "settings:updated",
            "settings": {
                "noteFormat": self.client_manager.get_note_format(user_id)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_vitals_update(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle vitals update"""
        encounter_id = self.client_manager.get_encounter(user_id)
        vitals_data = message.get("vitals")
        
        if encounter_id:
            await self.client_manager.broadcast_to_encounter({
                "type": "vitals:update",
                "vitals": vitals_data,
                "timestamp": datetime.utcnow().isoformat()
            }, encounter_id)
    
    async def _handle_get_status(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle status request"""
        client_info = self.client_manager.get_client_info(user_id)
        queue_status = self.transcription_queue.get_queue_status()
        
        await self.client_manager.send_to_client(user_id, {
            "type": "status:response",
            "client_info": client_info,
            "queue_status": queue_status,
            "server_metrics": self.get_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_ping(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle ping/pong"""
        await self.client_manager.send_to_client(user_id, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_clinical_notes_start(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Initialize clinical notes with EHR data"""
        patient_id = message.get("patient_id")
        encounter_type = message.get("encounter_type", "routine_visit")
        
        if not patient_id:
            await self.client_manager.send_to_client(user_id, {
                "type": "error",
                "message": "Patient ID required to start clinical notes"
            })
            return
        
        try:
            logger.info(f"Starting clinical notes for patient {patient_id}")
            
            # Get database session properly for async context
            from app.db.session import SessionLocal
            db = SessionLocal()
            
            try:
                # Initialize encounter in orchestrator
                encounter_id = str(uuid.uuid4())
                logger.info(f"Generated encounter ID: {encounter_id}")
                
                await self.agent_orchestrator.initialize_encounter(encounter_id, patient_id)
                logger.info(f"Initialized encounter in agent orchestrator")
                
                # Fetch EHR data
                logger.info(f"Fetching EHR data for patient {patient_id}")
                prefill_data = await self.ehr_prefill_service.fetch_patient_data_for_notes(patient_id, db)
                logger.info(f"EHR data fetch completed for patient {patient_id}")
            finally:
                db.close()
            
            # Store encounter ID for this user
            self.client_manager.add_encounter(user_id, encounter_id, patient_id)
            
            # Send prefilled data to UI
            await self.client_manager.send_to_client(user_id, {
                "type": "clinical_notes:prefill",
                "encounter_id": encounter_id,
                "patient_id": patient_id,
                "data": prefill_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Started clinical notes for patient {patient_id}, encounter {encounter_id}")
            
        except Exception as e:
            logger.error(f"Error starting clinical notes: {str(e)}")
            await self.client_manager.send_to_client(user_id, {
                "type": "error",
                "message": f"Failed to start clinical notes: {str(e)}"
            })
    
    async def _handle_format_update(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle format preference update"""
        format_preference = message.get("format", "long")
        encounter_id = self.client_manager.get_encounter(user_id)
        
        if encounter_id:
            self.agent_orchestrator.update_format_preference(encounter_id, format_preference)
            
            # Store in client context
            context = self.client_manager.get_client_context(user_id)
            context["note_format"] = format_preference
            
            await self.client_manager.send_to_client(user_id, {
                "type": "format:updated",
                "format": format_preference,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_section_focus(self, user_id: str, message: Dict, audio_processor: AudioProcessor):
        """Handle when user focuses on a specific section"""
        section = message.get("section")
        encounter_id = self.client_manager.get_encounter(user_id)
        
        if encounter_id and section:
            # Could be used to prioritize routing or provide context
            context = self.client_manager.get_client_context(user_id)
            context["focused_section"] = section
            
            await self.client_manager.send_to_client(user_id, {
                "type": "section:focus_acknowledged",
                "section": section,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _process_transcription_queue(self):
        """Background task to process transcription jobs"""
        while self.is_running:
            try:
                job = self.transcription_queue.get_job()
                if job:
                    # Process job asynchronously
                    asyncio.create_task(self._process_transcription_job(job))
                else:
                    await asyncio.sleep(0.1)  # Short sleep if no jobs
            except Exception as e:
                logger.error(f"Error in transcription queue processing: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_transcription_job(self, job: TranscriptionJob):
        """Process individual transcription job"""
        self.transcription_queue.mark_processing(job)
        self.metrics["total_transcriptions"] += 1
        
        try:
            # Get user context
            context = self.client_manager.get_client_context(job.client_id)
            encounter_id = self.client_manager.get_encounter(job.client_id)
            encounter_type = "general"  # Could be stored in client metadata
            
            # Transcribe audio
            start_time = time.time()
            transcription_result = await self.whisper_client.transcribe_with_context(
                job.audio_data, job.id, context, encounter_type
            )
            
            # Update metrics
            processing_time = time.time() - start_time
            self._update_average_processing_time(processing_time)
            
            # Add to context
            self.client_manager.add_to_context(job.client_id, transcription_result.text)
            
            # Send transcription result
            await self.client_manager.send_to_client(job.client_id, {
                "type": "transcription:result",
                "job_id": transcription_result.id,
                "text": transcription_result.text,
                "confidence": transcription_result.confidence,
                "segments": transcription_result.segments,
                "processing_time": transcription_result.processing_time,
                "timestamp": transcription_result.timestamp
            })
            
            # Process with agent orchestrator if encounter exists
            if encounter_id:
                note_format = self.client_manager.get_note_format(job.client_id)
                
                # Process through agent orchestrator
                orchestration_result = await self.agent_orchestrator.process_transcription(
                    transcription_result,
                    encounter_id,
                    note_format
                )
                
                # Send speaker identification
                await self.client_manager.send_to_client(job.client_id, {
                    "type": "speaker:identified",
                    "speaker": orchestration_result.speaker_info.speaker,
                    "confidence": orchestration_result.speaker_info.confidence,
                    "timestamp": orchestration_result.timestamp
                })
                
                # Send section updates
                for section_update in orchestration_result.section_updates:
                    await self.client_manager.send_to_client(job.client_id, {
                        "type": "section:update",
                        "section": section_update.section,
                        "content": section_update.formatted_content.get(
                            note_format, 
                            section_update.content
                        ),
                        "entities": section_update.entities,
                        "confidence": section_update.confidence,
                        "requires_resummary": orchestration_result.requires_resummary,
                        "timestamp": section_update.timestamp
                    })
                
                # Store analysis for legacy compatibility
                if encounter_id in self.clinical_analyses:
                    # Create a legacy clinical analysis from orchestration result
                    legacy_analysis = ClinicalAnalysis(
                        transcription_id=job.id,
                        entities=orchestration_result.section_updates[0].entities if orchestration_result.section_updates else {},
                        suggested_section={"primary_section": orchestration_result.routing_decision.primary_section},
                        confidence=orchestration_result.routing_decision.confidence,
                        contextual_info={},
                        timestamp=orchestration_result.timestamp
                    )
                    self.clinical_analyses[encounter_id].append(legacy_analysis)
            else:
                # Fallback to old clinical analysis if no encounter
                note_format = self.client_manager.get_note_format(job.client_id)
                clinical_analysis = await self.anthropic_client.analyze_clinical_text(
                    transcription_result, context, note_format
                )
                
                # Send clinical analysis
                await self.client_manager.send_to_client(job.client_id, {
                    "type": "clinical:analysis",
                    "job_id": clinical_analysis.transcription_id,
                    "entities": clinical_analysis.entities,
                    "suggested_section": clinical_analysis.suggested_section,
                    "confidence": clinical_analysis.confidence,
                    "contextual_info": clinical_analysis.contextual_info,
                    "timestamp": clinical_analysis.timestamp
                })
            
            # Update notes if auto-add is enabled
            if encounter_id and clinical_analysis.suggested_section["confidence"] > 0.8:
                section = clinical_analysis.suggested_section["primary_section"]
                if encounter_id not in self.encounter_notes:
                    self.encounter_notes[encounter_id] = {}
                if section not in self.encounter_notes[encounter_id]:
                    self.encounter_notes[encounter_id][section] = {"text": "", "entities": []}
                
                # Auto-add high confidence content
                self.encounter_notes[encounter_id][section]["text"] += "\n" + transcription_result.text
                self.encounter_notes[encounter_id][section]["entities"].extend(
                    clinical_analysis.entities.get("symptoms", []) +
                    clinical_analysis.entities.get("medications", []) +
                    clinical_analysis.entities.get("procedures", [])
                )
                
                # Broadcast auto-update
                await self.client_manager.broadcast_to_encounter({
                    "type": "notes:auto_update",
                    "section": section,
                    "content": self.encounter_notes[encounter_id][section],
                    "source": "ai_suggestion",
                    "confidence": clinical_analysis.confidence,
                    "timestamp": datetime.utcnow().isoformat()
                }, encounter_id)
            
            self.transcription_queue.mark_completed(job.id)
            self.metrics["successful_transcriptions"] += 1
            logger.info(f"Successfully processed transcription job {job.id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process transcription job {job.id}: {error_msg}")
            
            # Send error to client
            await self.client_manager.send_to_client(job.client_id, {
                "type": "transcription:error",
                "job_id": job.id,
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.transcription_queue.mark_failed(job, error_msg)
            self.metrics["failed_transcriptions"] += 1
    
    def _update_average_processing_time(self, processing_time: float):
        """Update average processing time metric"""
        current_avg = self.metrics["average_processing_time"]
        total_successful = self.metrics["successful_transcriptions"]
        
        if total_successful == 1:
            self.metrics["average_processing_time"] = processing_time
        else:
            # Calculate running average
            self.metrics["average_processing_time"] = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
    
    async def _send_periodic_metrics(self):
        """Send periodic metrics to all clients"""
        while self.is_running:
            await asyncio.sleep(30)  # Every 30 seconds
            
            metrics = self.get_metrics()
            await self.client_manager.broadcast_to_all({
                "type": "metrics:update",
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def get_metrics(self) -> Dict:
        """Get server performance metrics"""
        return {
            **self.metrics,
            "queue_status": self.transcription_queue.get_queue_status(),
            "client_stats": self.client_manager.get_stats(),
            "uptime": time.time() - self.metrics["start_time"]
        }
    
    def stop_server(self):
        """Stop the server"""
        self.is_running = False
        self.executor.shutdown(wait=True)
        self.transcription_queue.cleanup()
        logger.info("Medical Scribe Server stopped")


# Global server instance
server = MedicalScribeServer()


@router.websocket("/enhanced-audio-stream")
async def enhanced_websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db=Depends(get_db)
):
    """Enhanced WebSocket endpoint with agentic AI capabilities"""
    
    # Try Clerk auth first
    user = await get_clerk_user_ws(token)
    
    if not user:
        # Fall back to regular auth
        user = await get_current_user_ws(token, db)
    
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # Extract user info
    user_id = str(user.get('id', user.id if hasattr(user, 'id') else 'unknown'))
    metadata = {
        "email": user.get('email', getattr(user, 'email', None)),
        "name": user.get('name', getattr(user, 'name', None))
    }
    
    # Handle connection
    await server.handle_connection(websocket, user_id, metadata)