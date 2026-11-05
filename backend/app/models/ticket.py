"""
Ticket Model
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(50), primary_key=True, index=True)  # e.g., 'TCK-2026-001'
    alert_id = Column(String(50), ForeignKey("alerts.id"), nullable=False, unique=True, index=True)
    recommendation = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False)  # Retrieved passages, source citations, confidence metrics
    confidence = Column(Float, nullable=False, default=0.85)  # 0.0 to 1.0
    approval_status = Column(String(50), nullable=False, default="APPROVED")  # 'PENDING', 'APPROVED', 'REJECTED'
    approved_by = Column(String(100), nullable=False)  # Engineer ID/name who authorised the ticket
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    alert = relationship("Alert", back_populates="ticket")

    def __repr__(self) -> str:
        return f"<Ticket(id='{self.id}', alert_id='{self.alert_id}', approved_by='{self.approved_by}')>"
