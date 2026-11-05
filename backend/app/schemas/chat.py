"""
Pydantic Schemas for Multi-Agent Chat and Defect Inspection
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(..., example="Why is machine M104 at risk?")
    session_id: Optional[str] = "default"


class ToolCallTrace(BaseModel):
    agent: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Citation(BaseModel):
    source_id: str
    title: str
    passage: str
    score: float


class ChatMessageResponse(BaseModel):
    response: str
    confidence: float
    citations: List[Citation] = []
    tool_traces: List[ToolCallTrace] = []
    escalated_to_human: bool = False
    suggested_action: Optional[str] = None


class DefectInspectionResponse(BaseModel):
    image_name: str
    defect_type: str  # e.g., 'Surface Crack', 'Spalling', 'Dent', 'Normal'
    confidence: float
    affected_machine_id: Optional[str] = None
    batch_number: Optional[str] = None
    recommendation: str
