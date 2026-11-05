"""
Pydantic Schemas for Sensor Readings
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class SensorReadingBase(BaseModel):
    machine_id: str
    timestamp: datetime
    vibration: float = Field(..., description="Vibration velocity RMS in mm/s")
    temperature: float = Field(..., description="Temperature in °C")
    pressure: float = Field(..., description="Pressure in bar")
    current: float = Field(..., description="Current in Amperes")
    rpm: float = Field(..., description="Speed in RPM")


class SensorReadingCreate(SensorReadingBase):
    pass


class SensorReadingResponse(SensorReadingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SensorWindowResponse(BaseModel):
    machine_id: str
    count: int
    readings: List[SensorReadingResponse]
