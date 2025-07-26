"""Base agent classes for medical scribe system"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Message passed between agents"""
    agent_id: str
    message_type: str
    payload: Any
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.is_running = False
        self._handlers: Dict[str, Callable] = {}
        self._task: Optional[asyncio.Task] = None
        
    @abstractmethod
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming message and return response"""
        pass
    
    async def start(self):
        """Start the agent"""
        self.is_running = True
        logger.info(f"Agent {self.name} started")
        
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info(f"Agent {self.name} stopped")
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        self._handlers[message_type] = handler
        
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Route message to appropriate handler"""
        handler = self._handlers.get(message.message_type)
        if handler:
            return await handler(message)
        return await self.process(message)


class StreamingAgent(BaseAgent):
    """Base class for agents that handle streaming data"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self._stream_handlers: Dict[str, Callable] = {}
        
    async def handle_stream(self, stream_type: str, data: bytes):
        """Handle streaming data"""
        handler = self._stream_handlers.get(stream_type)
        if handler:
            await handler(data)
            
    def register_stream_handler(self, stream_type: str, handler: Callable):
        """Register a handler for streaming data"""
        self._stream_handlers[stream_type] = handler


class AgentOrchestrator:
    """Orchestrates communication between agents"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._message_queue = asyncio.Queue()
        self._running = False
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
        
    async def send_message(self, to_agent: str, message: AgentMessage):
        """Send a message to a specific agent"""
        if to_agent in self.agents:
            await self._message_queue.put((to_agent, message))
        else:
            logger.error(f"Agent {to_agent} not found")
            
    async def broadcast_message(self, message: AgentMessage, exclude: Optional[str] = None):
        """Broadcast a message to all agents except the excluded one"""
        for agent_name in self.agents:
            if agent_name != exclude:
                await self._message_queue.put((agent_name, message))
                
    async def start(self):
        """Start the orchestrator and all agents"""
        self._running = True
        
        # Start all agents
        for agent in self.agents.values():
            await agent.start()
            
        # Start message processing
        asyncio.create_task(self._process_messages())
        logger.info("Agent orchestrator started")
        
    async def stop(self):
        """Stop the orchestrator and all agents"""
        self._running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
            
        logger.info("Agent orchestrator stopped")
        
    async def _process_messages(self):
        """Process messages in the queue"""
        while self._running:
            try:
                agent_name, message = await asyncio.wait_for(
                    self._message_queue.get(), 
                    timeout=0.1
                )
                
                agent = self.agents.get(agent_name)
                if agent:
                    # Process message and check for response
                    response = await agent.handle_message(message)
                    
                    # If there's a response, route it
                    if response and hasattr(response, 'target_agent'):
                        await self.send_message(response.target_agent, response)
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")


# Agent handoff utilities
class AgentHandoff:
    """Utilities for agent handoff patterns"""
    
    @staticmethod
    def create_handoff_message(
        from_agent: str,
        to_agent: str,
        data: Any,
        handoff_type: str = "process"
    ) -> AgentMessage:
        """Create a handoff message between agents"""
        return AgentMessage(
            agent_id=from_agent,
            message_type=f"handoff:{handoff_type}",
            payload=data,
            metadata={
                "target_agent": to_agent,
                "handoff_type": handoff_type
            }
        )
    
    @staticmethod
    def create_response_message(
        from_agent: str,
        to_agent: str,
        data: Any,
        original_message: AgentMessage
    ) -> AgentMessage:
        """Create a response message to another agent"""
        return AgentMessage(
            agent_id=from_agent,
            message_type="response",
            payload=data,
            metadata={
                "target_agent": to_agent,
                "original_message_id": id(original_message),
                "original_type": original_message.message_type
            }
        )