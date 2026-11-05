"""
Pydantic Schemas for Maintenance History
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class MaintenanceHistoryBase(BaseModel):
    machine_id: str
    date: datetime
    issue: str
    action: str
    outcome: str


class MaintenanceHistoryCreate(MaintenanceHistoryBase):
    pass


class MaintenanceHistoryResponse(MaintenanceHistoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
