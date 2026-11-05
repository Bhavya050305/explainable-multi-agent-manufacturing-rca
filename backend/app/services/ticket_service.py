"""
ManuMind AI - Ticket Approval Service
Enforces Human-in-the-Loop approval gate for ticket creation.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.models.ticket import Ticket
from backend.app.models.alert import Alert


class TicketApprovalError(Exception):
    """Raised when an unapproved ticket creation attempt is blocked."""
    pass


def create_ticket_with_approval_gate(
    db: Session,
    alert_id: str,
    recommendation: str,
    evidence: Dict[str, Any],
    confidence: float,
    approved_by: Optional[str],
    ticket_id: Optional[str] = None
) -> Ticket:
    """
    Enforces Human-in-the-Loop approval:
    Ticket creation is STRICTLY REFUSED unless a valid approved_by engineer identifier is supplied.
    """
    if not approved_by or not str(approved_by).strip():
        raise TicketApprovalError(
            f"Ticket creation refused for Alert '{alert_id}': Human engineer approval is required before a maintenance work order can be created."
        )

    # Verify Alert exists
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alert with id '{alert_id}' not found.")

    # Check if a ticket already exists for this alert
    existing_ticket = db.query(Ticket).filter(Ticket.alert_id == alert_id).first()
    if existing_ticket:
        return existing_ticket

    # Generate ticket ID if not provided
    if not ticket_id:
        count = db.query(Ticket).count() + 1
        ticket_id = f"TCK-2026-{count:03d}"

    ticket = Ticket(
        id=ticket_id,
        alert_id=alert_id,
        recommendation=recommendation,
        evidence=evidence,
        confidence=confidence,
        approval_status="APPROVED",
        approved_by=str(approved_by).strip(),
        created_at=datetime.utcnow()
    )

    # Update alert status
    alert.status = "APPROVED"

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
