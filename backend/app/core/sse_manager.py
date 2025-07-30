import asyncio
import json
from typing import Dict, Set, AsyncGenerator, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SSEManager:
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(self, channel: str) -> AsyncGenerator[Dict, None]:
        """Subscribe to a channel for SSE events"""
        queue: asyncio.Queue = asyncio.Queue()
        
        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers[channel].discard(queue)
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
    
    async def publish(self, channel: str, event: Dict):
        """Publish an event to all subscribers of a channel"""
        # Support both old (event_type, data) and new (event dict) interfaces
        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")
            
        # Ensure event has required fields
        if "type" not in event or "data" not in event:
            raise ValueError("Event must have 'type' and 'data' fields")
            
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()
        
        subscribers = []
        async with self._lock:
            if channel in self._subscribers:
                # Create list to avoid modification during iteration
                subscribers = list(self._subscribers[channel])
                
        # Send to all subscribers
        for queue in subscribers:
            try:
                await queue.put(event)
            except:
                # Queue might be full or closed
                pass
                
        logger.info(f"Published {event['type']} to {channel} ({len(subscribers)} subscribers)")
    
    async def close_channel(self, channel: str):
        """Close a channel and notify all subscribers"""
        await self.publish(channel, {
            "type": "channel_closed",
            "data": {"reason": "completed"}
        })
        
        async with self._lock:
            if channel in self._subscribers:
                del self._subscribers[channel]


# Global instance
sse_manager = SSEManager()