"""
Pydantic Schemas for Machine
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class MachineBase(BaseModel):
    id: str = Field(..., example="M104")
    name: str = Field(..., example="CNC Milling Center 04")
    type: str = Field(..., example="CNC Milling")
    criticality: int = Field(..., ge=1, le=5, example=5)
    production_impact: int = Field(..., ge=1, le=5, example=5)


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    criticality: Optional[int] = Field(None, ge=1, le=5)
    production_impact: Optional[int] = Field(None, ge=1, le=5)


class MachineResponse(MachineBase):
    model_config = ConfigDict(from_attributes=True)
