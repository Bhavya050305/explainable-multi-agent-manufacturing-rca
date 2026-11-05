"""
MaintenanceHistory Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    issue = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    outcome = Column(String(50), nullable=False)  # 'Resolved', 'Monitoring', 'Temporary Fix'

    machine = relationship("Machine", back_populates="maintenance_records")

    def __repr__(self) -> str:
        return f"<MaintenanceHistory(machine_id='{self.machine_id}', date='{self.date}', outcome='{self.outcome}')>"
