"""
Pydantic Schemas for Alerts
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional


class AlertBase(BaseModel):
    id: str
    machine_id: str
    risk: float = Field(..., ge=0.0, le=1.0)
    criticality: int = Field(..., ge=1, le=5)
    impact: int = Field(..., ge=1, le=5)
    priority_score: float
    shap_json: Optional[Dict[str, float]] = None
    sensor_contrib_json: Optional[Dict[str, float]] = None
    status: str = "PENDING_APPROVAL"


class AlertCreate(AlertBase):
    pass


class AlertUpdateStatus(BaseModel):
    status: str = Field(..., example="APPROVED")
    comment: Optional[str] = None
    approved_by: Optional[str] = None


class AlertResponse(AlertBase):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PriorityAlertItem(AlertResponse):
    machine_name: str
    machine_type: str
    top_driver: str
