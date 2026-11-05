"""
Alert Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(50), primary_key=True, index=True)  # e.g., 'ALT-M104-001'
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False, index=True)
    risk = Column(Float, nullable=False)  # 0.0 to 1.0 (failure risk probability)
    criticality = Column(Integer, nullable=False)  # 1 to 5
    impact = Column(Integer, nullable=False)  # 1 to 5 (production impact)
    priority_score = Column(Float, nullable=False, index=True)  # risk * criticality * impact
    shap_json = Column(JSON, nullable=True)  # feature attribution dictionary
    sensor_contrib_json = Column(JSON, nullable=True)  # LSTM reconstruction error per sensor
    status = Column(String(50), default="PENDING_APPROVAL", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    machine = relationship("Machine", back_populates="alerts")
    ticket = relationship("Ticket", back_populates="alert", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Alert(id='{self.id}', machine_id='{self.machine_id}', priority_score={self.priority_score})>"
