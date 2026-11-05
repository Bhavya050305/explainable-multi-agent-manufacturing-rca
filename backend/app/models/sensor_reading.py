"""
SensorReading Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 5 Key Industrial Telemetry Channels
    vibration = Column(Float, nullable=False)     # mm/s (Velocity RMS)
    temperature = Column(Float, nullable=False)   # °C (Bearing/Motor Housing)
    pressure = Column(Float, nullable=False)      # bar (Hydraulic/Pneumatic line)
    current = Column(Float, nullable=False)       # A (Motor Load current)
    rpm = Column(Float, nullable=False)           # RPM (Spindle/Motor speed)

    machine = relationship("Machine", back_populates="sensor_readings")

    __table_args__ = (
        Index("idx_sensor_machine_time", "machine_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<SensorReading(machine_id='{self.machine_id}', timestamp='{self.timestamp}', vib={self.vibration})>"
