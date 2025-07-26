import json
import logging
from typing import Dict, Set, List, Optional
from datetime import datetime
import asyncio
from fastapi import WebSocket
import websockets

logger = logging.getLogger(__name__)


class ClientManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.client_contexts: Dict[str, List[str]] = {}  # Store context per client
        self.client_metadata: Dict[str, Dict] = {}  # Store client metadata
        self.user_encounters: Dict[str, str] = {}  # user_id -> encounter_id
        self.user_note_formats: Dict[str, str] = {}  # user_id -> note_format
        self.user_transcription_jobs: Dict[str, List[str]] = {}  # user_id -> job_ids
        
    async def connect(self, websocket: WebSocket, user_id: str, metadata: Dict = None):
        """Add new client connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Initialize client data
        if user_id not in self.client_contexts:
            self.client_contexts[user_id] = []
        
        # Store metadata
        if metadata:
            self.client_metadata[user_id] = {
                **metadata,
                "connected_at": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Client {user_id} connected via WebSocket")
        
        # Send connection confirmation
        await self.send_to_client(user_id, {
            "type": "connection_established",
            "client_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": self.client_metadata.get(user_id, {})
        })
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove client connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Don't clear context immediately - keep for reconnection
        
        logger.info(f"Client {user_id} disconnected from WebSocket")
    
    def get_client_context(self, user_id: str, limit: int = 10) -> List[str]:
        """Get conversation context for client"""
        context = self.client_contexts.get(user_id, [])
        return context[-limit:] if limit else context
    
    def add_to_context(self, user_id: str, text: str, max_context: int = 20):
        """Add transcription to client context"""
        if user_id not in self.client_contexts:
            self.client_contexts[user_id] = []
        
        self.client_contexts[user_id].append(text)
        
        # Keep only last N transcriptions for context
        if len(self.client_contexts[user_id]) > max_context:
            self.client_contexts[user_id] = self.client_contexts[user_id][-max_context:]
    
    def clear_context(self, user_id: str):
        """Clear context for a client"""
        if user_id in self.client_contexts:
            self.client_contexts[user_id] = []
    
    def set_encounter(self, user_id: str, encounter_id: str):
        """Set active encounter for user"""
        self.user_encounters[user_id] = encounter_id
    
    def get_encounter(self, user_id: str) -> Optional[str]:
        """Get active encounter for user"""
        return self.user_encounters.get(user_id)
    
    def set_note_format(self, user_id: str, note_format: str):
        """Set note format preference for user"""
        self.user_note_formats[user_id] = note_format
    
    def get_note_format(self, user_id: str) -> str:
        """Get note format preference for user"""
        return self.user_note_formats.get(user_id, "long")
    
    def add_transcription_job(self, user_id: str, job_id: str):
        """Track transcription job for user"""
        if user_id not in self.user_transcription_jobs:
            self.user_transcription_jobs[user_id] = []
        self.user_transcription_jobs[user_id].append(job_id)
        
        # Keep only last 100 job IDs
        if len(self.user_transcription_jobs[user_id]) > 100:
            self.user_transcription_jobs[user_id] = self.user_transcription_jobs[user_id][-100:]
    
    def get_user_jobs(self, user_id: str) -> List[str]:
        """Get transcription job IDs for user"""
        return self.user_transcription_jobs.get(user_id, [])
    
    async def send_to_client(self, user_id: str, message: Dict):
        """Send message to specific client"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"Client {user_id} connection closed")
                    disconnected.add(connection)
                except Exception as e:
                    logger.error(f"Error sending message to client {user_id}: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_encounter(self, message: Dict, encounter_id: str):
        """Broadcast message to all users in an encounter"""
        # Find all users connected to this encounter
        for user_id, enc_id in self.user_encounters.items():
            if enc_id == encounter_id:
                await self.send_to_client(user_id, message)
    
    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all connected clients"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_client(user_id, message)
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())
    
    def get_client_info(self, user_id: str) -> Dict:
        """Get comprehensive client information"""
        return {
            "user_id": user_id,
            "connected": user_id in self.active_connections,
            "connection_count": len(self.active_connections.get(user_id, set())),
            "encounter_id": self.user_encounters.get(user_id),
            "note_format": self.user_note_formats.get(user_id, "long"),
            "context_size": len(self.client_contexts.get(user_id, [])),
            "job_count": len(self.user_transcription_jobs.get(user_id, [])),
            "metadata": self.client_metadata.get(user_id, {})
        }
    
    def get_stats(self) -> Dict:
        """Get manager statistics"""
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "active_encounters": len(set(self.user_encounters.values())),
            "total_context_items": sum(len(ctx) for ctx in self.client_contexts.values()),
            "total_jobs_tracked": sum(len(jobs) for jobs in self.user_transcription_jobs.values())
        }
    
    def cleanup_user(self, user_id: str):
        """Clean up all data for a user"""
        # Remove from all tracking dictionaries
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.client_contexts:
            del self.client_contexts[user_id]
        if user_id in self.client_metadata:
            del self.client_metadata[user_id]
        if user_id in self.user_encounters:
            del self.user_encounters[user_id]
        if user_id in self.user_note_formats:
            del self.user_note_formats[user_id]
        if user_id in self.user_transcription_jobs:
            del self.user_transcription_jobs[user_id]
        
        logger.info(f"Cleaned up all data for user {user_id}")