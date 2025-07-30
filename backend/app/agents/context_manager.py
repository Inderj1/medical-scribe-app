"""Handoff Context Manager for Agent Communication"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class HandoffContext:
    """Manages context for agent handoffs"""
    
    def __init__(self):
        # Global context storage for agent handoffs
        self._contexts: Dict[str, Dict[str, Any]] = {}
        
    def create_session(self, session_id: str, initial_context: Dict[str, Any]) -> None:
        """Create a new session with initial context"""
        self._contexts[session_id] = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            **initial_context
        }
        logger.info(f"Created session {session_id} with context: {list(initial_context.keys())}")
    
    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get context for a session"""
        return self._contexts.get(session_id)
    
    def update_context(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update context for a session"""
        if session_id in self._contexts:
            self._contexts[session_id].update(updates)
            self._contexts[session_id]["updated_at"] = datetime.utcnow().isoformat()
            logger.info(f"Updated session {session_id} with: {list(updates.keys())}")
        else:
            logger.warning(f"Session {session_id} not found for update")
    
    def add_to_context(self, session_id: str, key: str, value: Any) -> None:
        """Add a specific key-value to context"""
        if session_id in self._contexts:
            self._contexts[session_id][key] = value
            self._contexts[session_id]["updated_at"] = datetime.utcnow().isoformat()
            logger.info(f"Added {key} to session {session_id}")
        else:
            logger.warning(f"Session {session_id} not found")
    
    def get_from_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a specific value from context"""
        if session_id in self._contexts:
            return self._contexts[session_id].get(key, default)
        return default
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session's context"""
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info(f"Cleared session {session_id}")
    
    def list_sessions(self) -> list[str]:
        """List all active sessions"""
        return list(self._contexts.keys())


# Global handoff context instance
handoff_context = HandoffContext()