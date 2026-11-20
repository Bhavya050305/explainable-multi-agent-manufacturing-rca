"""
ManuMind AI — Ticket Proposal and Consumed Token Models
Phase 4 Step 6: Secure Maintenance Ticket Creation Architecture

Department of AI & Data Science — RMK Engineering College
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class TicketProposal(Base):
    """
    Represents a staged maintenance ticket proposal awaiting authenticated human approval.

    Lifecycle:
    1. Agent generates proposal via propose_maintenance_ticket (status: PENDING_APPROVAL).
    2. Canonical payload hash is computed and stored. No active Ticket is created.
    3. Human engineer reviews the exact proposal via external approval interface.
    4. Upon authenticated approval, a signed HMAC token bound to proposal_id and payload_hash is issued.
    5. Agent or pipeline presents token via create_maintenance_ticket.
    6. Upon cryptographic and database verification, Ticket is created and proposal transitions to CONSUMED.
    """
    __tablename__ = "ticket_proposals"

    id = Column(String(50), primary_key=True, index=True)  # e.g., 'PROP-2026-0001'
    machine_id = Column(String(50), ForeignKey("machines.id"), nullable=False, index=True)
    alert_id = Column(String(50), ForeignKey("alerts.id"), nullable=True, index=True)
    recommendation = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False)  # Structured evidence payload
    confidence = Column(Float, nullable=False, default=0.85)  # 0.0 to 1.0
    payload_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of canonical payload
    status = Column(String(50), nullable=False, default="PENDING_APPROVAL", index=True)  # PENDING_APPROVAL, CONSUMED, REJECTED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)  # Proposal validity expiry
    approved_by = Column(String(100), nullable=True)  # Authenticated human approver identifier
    approved_at = Column(DateTime, nullable=True)  # Human approval timestamp
    token_id = Column(String(100), nullable=True, unique=True, index=True)  # Consumed token jti
    ticket_id = Column(String(50), ForeignKey("tickets.id"), nullable=True, unique=True, index=True)  # Resulting ticket

    machine = relationship("Machine")
    alert = relationship("Alert")
    ticket = relationship("Ticket")

    def __repr__(self) -> str:
        return f"<TicketProposal(id='{self.id}', machine_id='{self.machine_id}', status='{self.status}')>"


class ConsumedToken(Base):
    """
    Persistent audit and replay prevention log for consumed authorization tokens.

    Guarantees:
    - Primary key constraint on `jti` strictly prevents replay attacks at the database layer.
    - Token consumption is atomically recorded alongside ticket creation in the same transaction.
    """
    __tablename__ = "consumed_tokens"

    jti = Column(String(100), primary_key=True, index=True)  # Unique JWT ID (UUIDv4)
    proposal_id = Column(String(50), ForeignKey("ticket_proposals.id"), nullable=False, index=True)
    approver_id = Column(String(100), nullable=False)  # Authenticated engineer identifier
    consumed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    token_exp = Column(DateTime, nullable=False)  # Token expiration timestamp

    def __repr__(self) -> str:
        return f"<ConsumedToken(jti='{self.jti}', proposal_id='{self.proposal_id}', approver_id='{self.approver_id}')>"
