# Tool processing event (for emitting tool logs or intermediate steps)
from typing import Literal
from typing import Literal, Union, Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# Base class for all events
class BaseAgentEvent(BaseModel):
    type: str
    timestamp: datetime = datetime.utcnow()


#########################
# Specific event types
#########################
# Websocket connection event
class WebsocketConnectionEvent(BaseAgentEvent):
    type: Literal["websocket_connection"] = "websocket_connection"
    content: Optional[str] = None

# Iteration start event
class IterationStartEvent(BaseAgentEvent):
    type: Literal["iteration_start"] = "iteration_start"
    iteration: int

# System prompt event
class SystemPromptEvent(BaseAgentEvent):
    type: Literal["system_prompt"] = "system_prompt"
    iteration: int
    content: str

# LLM request event
class LLMRequestEvent(BaseAgentEvent):
    type: Literal["llm_request"] = "llm_request"
    iteration: int
    messages: List[Dict[str, Any]]

# LLM thinking event
class LLMThinkingEvent(BaseAgentEvent):
    type: Literal["llm_thinking"] = "llm_thinking"
    iteration: int
    content: str

# Tool call event
class ToolCallEvent(BaseAgentEvent):
    type: Literal["tool_call"] = "tool_call"
    iteration: int
    tool: str
    args: Dict[str, Any]

# Tool processing event (for emitting tool logs or intermediate steps)
class ToolProcessingEvent(BaseAgentEvent):
    type: Literal["tool_processing"] = "tool_processing"
    log: str

# Tool result event
class ToolResultEvent(BaseAgentEvent):
    type: Literal["tool_result"] = "tool_result"
    iteration: int
    tool: str
    result: Any

# Final answer event
class FinalAnswerEvent(BaseAgentEvent):
    type: Literal["final_answer"] = "final_answer"
    content: str

# Error event
class ErrorEvent(BaseAgentEvent):
    type: Literal["error"] = "error"
    message: str



# Union of all agent events for type hinting
AgentEvent = Union[
    WebsocketConnectionEvent,
    IterationStartEvent,
    SystemPromptEvent,
    LLMRequestEvent,
    LLMThinkingEvent,
    ToolCallEvent,
    ToolProcessingEvent,
    ToolResultEvent,
    FinalAnswerEvent,
    ErrorEvent
]
