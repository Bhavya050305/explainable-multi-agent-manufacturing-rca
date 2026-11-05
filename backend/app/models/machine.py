"""
Machine Model
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(String(50), primary_key=True, index=True)  # e.g., 'M101'
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., 'CNC Milling', 'Hydraulic Press'
    criticality = Column(Integer, nullable=False, default=3)  # 1 to 5 scale
    production_impact = Column(Integer, nullable=False, default=3)  # 1 to 5 scale

    # Relationships
    sensor_readings = relationship("SensorReading", back_populates="machine", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceHistory", back_populates="machine", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="machine", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Machine(id='{self.id}', name='{self.name}', type='{self.type}')>"
