"""
Pydantic Schemas for Tickets
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional


class TicketBase(BaseModel):
    id: str
    alert_id: str
    recommendation: str
    evidence: Dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)
    approval_status: str = "APPROVED"
    approved_by: str


class TicketCreate(BaseModel):
    alert_id: str
    recommendation: str
    evidence: Dict[str, Any]
    confidence: float
    approved_by: str  # Mandatory for gate check!


class TicketResponse(TicketBase):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
