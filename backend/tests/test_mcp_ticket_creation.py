"""
ManuMind AI — Secure Maintenance Ticket Creation MCP Tool Test Suite
Phase 4 Step 6: Secure Maintenance Ticket Creation Architecture

Department of AI & Data Science — RMK Engineering College

Covers:
1. Proposal validation, constraints, and immutability (Tests 1–9)
2. Cryptographic token verification, signature, replay, tampering, and secret management (Tests 10–23)
3. Transaction atomicity, concurrency, and database linkage (Tests 24–30)
4. MCP Server 9-tool discovery and real stdio lifecycle integration (Tests 31–32)
"""

import os
import sys
import json
import uuid
import base64
import hmac
import hashlib
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
import anyio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.app.database import Base
from backend.app.models.machine import Machine
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_proposal import TicketProposal, ConsumedToken
from backend.app.mcp_server.server import SERVER_NAME, SERVER_VERSION, create_mcp_server
from backend.app.mcp_server.schemas import (
    ProposeMaintenanceTicketResponse,
    CreateMaintenanceTicketResponse,
)
from backend.app.mcp_server.approval import (
    compute_canonical_payload_hash,
    HMACApprovalTokenManager,
    DevelopmentHumanApprovalAdapter,
    ApprovalSecurityError,
    ApprovalConfigurationError,
    InvalidTokenError,
    TokenExpiredError,
    TokenProposalMismatchError,
    TokenPayloadMismatchError,
    APPROVAL_SECRET_ENV_VAR,
)
from backend.app.mcp_server.tools import (
    handle_propose_maintenance_ticket,
    handle_create_maintenance_ticket,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_SECRET_KEY = "super-secret-hmac-key-for-unit-testing-32bytes!"


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def setup_approval_secret_env(monkeypatch):
    """Ensure a deterministic secret key is set for tests unless explicitly unset."""
    monkeypatch.setenv(APPROVAL_SECRET_ENV_VAR, TEST_SECRET_KEY)


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    """
    Creates an isolated in-memory SQLite database populated with test machines and alerts.
    Completely isolated from the authoritative production database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Seed baseline machines M101 to M110
    for i in range(101, 111):
        m = Machine(
            id=f"M{i}",
            name=f"Test Machine {i}",
            type="CNC Milling" if i % 2 == 1 else "Hydraulic Press",
            criticality=4,
            production_impact=4,
        )
        session.add(m)

    # Seed an alert for M104
    alt = Alert(
        id="ALT-M104-001",
        machine_id="M104",
        risk=0.88,
        criticality=5,
        impact=5,
        priority_score=22.0,
        shap_json={"vibration": 0.54, "temperature": 0.22},
        sensor_contrib_json={"vibration": 0.62},
        status="PENDING_APPROVAL",
        created_at=datetime.utcnow(),
    )
    session.add(alt)
    session.commit()

    try:
        yield session
    finally:
        session.close()


# ===========================================================================
# 1. Proposal Tests (Tests 1–9)
# ===========================================================================

def test_1_valid_proposal_creation(memory_db: Session):
    """Test 1: Valid proposal creation stages a proposal in PENDING_APPROVAL status."""
    res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace damaged front spindle bearing assembly and recalibrate vibration sensor.",
        evidence={"vibration": 0.85, "defect": "surface_crack", "confidence": 0.94},
        alert_id="ALT-M104-001",
        confidence=0.92,
        session_override=memory_db,
    )

    assert res["status"] == "PENDING_APPROVAL"
    assert res["proposal_id"].startswith("PROP-2026-")
    assert res["machine_id"] == "M104"
    assert res["alert_id"] == "ALT-M104-001"
    assert len(res["payload_hash"]) == 64
    assert res["requires_human_approval"] is True
    assert res["is_synthetic"] is True
    assert "pending human engineer authorization" in res["message"]


def test_2_invalid_machine_id_rejection(memory_db: Session):
    """Test 2: Reject invalid machine IDs not matching ^M1(0[1-9]|10)$."""
    for invalid_id in ["M999", "M100", "M111", "INVALID", "", "M104; DROP TABLE"]:
        with pytest.raises(ValueError, match="Invalid machine_id"):
            handle_propose_maintenance_ticket(
                machine_id=invalid_id,
                recommendation="Replace front bearing assembly.",
                evidence={"metric": 1.0},
                session_override=memory_db,
            )


def test_3_empty_recommendation_rejection(memory_db: Session):
    """Test 3: Reject empty or whitespace-only recommendations (< 5 characters)."""
    for bad_rec in ["", "   ", "fix", "ab"]:
        with pytest.raises(ValueError, match="recommendation must be a non-empty string"):
            handle_propose_maintenance_ticket(
                machine_id="M104",
                recommendation=bad_rec,
                evidence={"metric": 1.0},
                session_override=memory_db,
            )


def test_4_oversized_recommendation_rejection(memory_db: Session):
    """Test 4: Reject recommendations exceeding 1000 characters."""
    oversized = "A" * 1001
    with pytest.raises(ValueError, match="exceeds maximum allowed length of 1000 characters"):
        handle_propose_maintenance_ticket(
            machine_id="M104",
            recommendation=oversized,
            evidence={"metric": 1.0},
            session_override=memory_db,
        )


def test_5_malformed_evidence_rejection(memory_db: Session):
    """Test 5: Reject non-dict or empty evidence inputs."""
    for bad_ev in [None, {}, [], "evidence", 123]:
        with pytest.raises(ValueError, match="evidence must be a non-empty structured dictionary"):
            handle_propose_maintenance_ticket(
                machine_id="M104",
                recommendation="Replace front bearing assembly.",
                evidence=bad_ev,  # type: ignore
                session_override=memory_db,
            )


def test_6_unexpected_fields_rejected():
    """Test 6: Verify schema rejects unexpected fields via extra='forbid'."""
    from pydantic import ValidationError
    from backend.app.mcp_server.schemas import ProposeMaintenanceTicketResponse

    with pytest.raises(ValidationError):
        ProposeMaintenanceTicketResponse(
            status="PENDING_APPROVAL",
            proposal_id="PROP-2026-0001",
            machine_id="M104",
            recommendation="Test recommendation",
            confidence=0.85,
            payload_hash="a" * 64,
            created_at=datetime.utcnow().isoformat(),
            expires_at=datetime.utcnow().isoformat(),
            message="Test message",
            approved_by="Agent Self-Approval Attempt",  # FORBIDDEN FIELD
        )


def test_7_proposal_remains_pending(memory_db: Session):
    """Test 7: Verify stored proposal has status PENDING_APPROVAL and zero tickets linked."""
    res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing assembly immediately.",
        evidence={"vibration": 0.85},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    prop = memory_db.query(TicketProposal).filter_by(id=res["proposal_id"]).first()
    assert prop is not None
    assert prop.status == "PENDING_APPROVAL"
    assert prop.ticket_id is None
    assert prop.approved_by is None


def test_8_no_active_ticket_created_during_proposal(memory_db: Session):
    """Test 8: Assert ticket count does NOT increase when a proposal is submitted."""
    initial_ticket_count = memory_db.query(Ticket).count()

    handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing assembly.",
        evidence={"vibration": 0.85},
        session_override=memory_db,
    )

    final_ticket_count = memory_db.query(Ticket).count()
    assert final_ticket_count == initial_ticket_count


def test_9_synthetic_evidence_disclosure_preserved(memory_db: Session):
    """Test 9: Verify synthetic demonstration flags and disclaimers are preserved."""
    res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Inspect hydraulic seal.",
        evidence={"sensor": "pressure"},
        session_override=memory_db,
    )

    assert res["is_synthetic"] is True
    assert "Ticket proposals do NOT create active maintenance work orders" in res["disclaimer"]


# ===========================================================================
# 2. Approval Security Tests (Tests 10–23)
# ===========================================================================

def test_10_missing_token_rejected(memory_db: Session):
    """Test 10: Missing or whitespace-only token is rejected."""
    with pytest.raises(ValueError, match="approval_token must be a non-empty string"):
        handle_create_maintenance_ticket(
            proposal_id="PROP-2026-0001",
            approval_token="   ",
            session_override=memory_db,
        )


def test_11_malformed_token_rejected(memory_db: Session):
    """Test 11: Malformed token structure (not 3 dot-separated segments) is rejected."""
    # Create proposal first
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace damaged bearing.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    for malformed in ["not.a.valid.jwt.token", "only-one-part", "two.parts"]:
        with pytest.raises(InvalidTokenError):
            handle_create_maintenance_ticket(
                proposal_id=prop_res["proposal_id"],
                approval_token=malformed,
                session_override=memory_db,
            )


def test_12_invalid_signature_rejected(memory_db: Session):
    """Test 12: Token with tampered signature is rejected."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace damaged bearing.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    parts = token.split(".")
    tampered_sig = parts[2][:-4] + "XXXX"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(InvalidTokenError, match="Cryptographic signature verification failed"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=tampered_token,
            session_override=memory_db,
        )


def test_13_wrong_proposal_id_rejected(memory_db: Session):
    """Test 13: Token bound to PROP-0001 rejected when used for PROP-0002."""
    prop_res1 = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        session_override=memory_db,
    )
    prop_res2 = handle_propose_maintenance_ticket(
        machine_id="M102",
        recommendation="Calibrate pressure on M102.",
        evidence={"test": 2},
        session_override=memory_db,
    )

    # Issue token for proposal 1
    token1 = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res1["proposal_id"],
        payload_hash=prop_res1["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    # Attempt to use token 1 for proposal 2
    with pytest.raises(TokenProposalMismatchError, match="Token is bound to proposal"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res2["proposal_id"],
            approval_token=token1,
            session_override=memory_db,
        )


def test_14_wrong_payload_hash_rejected(memory_db: Session):
    """Test 14: Token with mismatched payload hash is rejected."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    fake_hash = "f" * 64
    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=fake_hash,
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    with pytest.raises(TokenPayloadMismatchError, match="Cryptographic binding failure"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_15_untrusted_issuer_rejected(memory_db: Session):
    """Test 15: Token with untrusted issuer is rejected."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    # Manually craft token with untrusted issuer
    header_b64 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    claims = {
        "jti": str(uuid.uuid4()),
        "proposal_id": prop_res["proposal_id"],
        "payload_hash": prop_res["payload_hash"],
        "approver_id": "Lead Engineer S. Raman",
        "approver_role": "Lead Reliability Engineer",
        "action": "APPROVE_MAINTENANCE_TICKET",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
        "v": 1,
        "iss": "untrusted-rogue-issuer",
    }
    claims_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signing_input = f"{header_b64}.{claims_b64}".encode()
    sig = hmac.new(TEST_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    token = f"{header_b64}.{claims_b64}.{sig_b64}"

    with pytest.raises(InvalidTokenError, match="Untrusted token issuer"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_16_expired_token_rejected(memory_db: Session):
    """Test 16: Expired token is rejected."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    # Issue token with negative validity (expired 10 seconds ago)
    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
        validity_seconds=-10,
    )

    with pytest.raises(TokenExpiredError, match="Authorization token expired"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_17_replayed_token_rejected(memory_db: Session):
    """Test 17: Token that has already been consumed cannot be re-used (replay prevention)."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    adapter = DevelopmentHumanApprovalAdapter()
    token = adapter.authenticate_and_approve(
        engineer_id="ENG-RAMAN-01",
        credential="RamanSecurePass2026!",
        proposal_id=prop_res["proposal_id"],
        proposal_data={
            "machine_id": "M104",
            "recommendation": "Replace bearing on M104.",
            "evidence": {"test": 1},
            "alert_id": "ALT-M104-001",
            "confidence": 0.85,
            "payload_hash": prop_res["payload_hash"],
        },
    )

    # 1. First execution succeeds
    res1 = handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )
    assert res1["status"] == "APPROVED"

    # 2. Second execution with same token is rejected
    with pytest.raises(ValueError, match="cannot be authorized: status is 'CONSUMED'"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_18_already_consumed_proposal_rejected(memory_db: Session):
    """Test 18: Proposal marked CONSUMED cannot produce another ticket."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace bearing on M104.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    # First consumption succeeds
    handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    # Create a fresh token for the same proposal
    token2 = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Chief Engineer K. Patel",
        approver_role="Chief Maintenance Engineer",
    )

    with pytest.raises(ValueError, match="status is 'CONSUMED'"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token2,
            session_override=memory_db,
        )


def test_19_altered_recommendation_rejected(memory_db: Session):
    """Test 19: Altering proposal recommendation after token issuance causes hash mismatch rejection."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Initial benign recommendation.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    # Tamper with recommendation in database directly
    prop = memory_db.query(TicketProposal).filter_by(id=prop_res["proposal_id"]).first()
    prop.recommendation = "Malicious altered recommendation!"
    memory_db.commit()

    with pytest.raises(ValueError, match="Proposal integrity violation: Stored payload hash does not match"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_20_altered_evidence_rejected(memory_db: Session):
    """Test 20: Altering proposal evidence after token issuance causes hash mismatch rejection."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing assembly.",
        evidence={"vibration": 0.5},
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    # Tamper with evidence in database
    prop = memory_db.query(TicketProposal).filter_by(id=prop_res["proposal_id"]).first()
    prop.evidence = {"vibration": 99.9, "tampered": True}
    memory_db.commit()

    with pytest.raises(ValueError, match="Proposal integrity violation"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_21_invalid_token_algorithm_rejected(memory_db: Session):
    """Test 21: Reject token specifying algorithm other than HS256 (e.g. 'none')."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    header = {"alg": "none", "typ": "JWT"}
    claims = {
        "jti": str(uuid.uuid4()),
        "proposal_id": prop_res["proposal_id"],
        "payload_hash": prop_res["payload_hash"],
        "approver_id": "Lead Engineer S. Raman",
        "approver_role": "Lead Reliability Engineer",
        "action": "APPROVE_MAINTENANCE_TICKET",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
        "v": 1,
        "iss": "manumind-human-approval-gate",
    }
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    c_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    none_token = f"{h_b64}.{c_b64}."

    with pytest.raises(InvalidTokenError, match="Unsupported or invalid algorithm 'none'"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=none_token,
            session_override=memory_db,
        )


def test_22_missing_signing_secret_fails_closed(monkeypatch, memory_db: Session):
    """Test 22: Unset environment signing secret causes service to fail closed."""
    monkeypatch.delenv(APPROVAL_SECRET_ENV_VAR, raising=False)

    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing.",
        evidence={"test": 1},
        session_override=memory_db,
    )

    with pytest.raises(ApprovalConfigurationError, match="fails closed"):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token="dummy.token.value",
            session_override=memory_db,
        )


def test_23_agent_supplied_approved_by_rejected():
    """Test 23: Agent cannot pass arbitrary approved_by string in tool invocation."""
    from pydantic import ValidationError
    from backend.app.mcp_server.schemas import CreateMaintenanceTicketResponse

    # Assert that tool handler signature does not even have approved_by parameter
    import inspect
    sig = inspect.signature(handle_create_maintenance_ticket)
    assert "approved_by" not in sig.parameters

    # Schema rejects extra fields
    with pytest.raises(ValidationError):
        CreateMaintenanceTicketResponse(
            status="APPROVED",
            ticket_id="TCK-2026-002",
            proposal_id="PROP-2026-0001",
            machine_id="M104",
            alert_id="ALT-M104-001",
            recommendation="Test",
            confidence=0.85,
            approved_by="Lead Engineer S. Raman",
            approved_at=datetime.utcnow().isoformat(),
            created_at=datetime.utcnow().isoformat(),
            message="Test",
            agent_self_authorization="Attempt to bypass approval gate",  # FORBIDDEN
        )


# ===========================================================================
# 3. Transaction & Concurrency Tests (Tests 24–30)
# ===========================================================================

def test_24_successful_authorized_ticket_creation(memory_db: Session):
    """Test 24: Successful authorized ticket creation creates active ticket in database."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Overhaul spindle assembly on machine M104.",
        evidence={"vibration": 0.88, "root_cause": "bearing spalling"},
        alert_id="ALT-M104-001",
        confidence=0.88,
        session_override=memory_db,
    )

    adapter = DevelopmentHumanApprovalAdapter()
    token = adapter.authenticate_and_approve(
        engineer_id="ENG-RAMAN-01",
        credential="RamanSecurePass2026!",
        proposal_id=prop_res["proposal_id"],
        proposal_data={
            "machine_id": "M104",
            "recommendation": "Overhaul spindle assembly on machine M104.",
            "evidence": {"vibration": 0.88, "root_cause": "bearing spalling"},
            "alert_id": "ALT-M104-001",
            "confidence": 0.88,
            "payload_hash": prop_res["payload_hash"],
        },
    )

    res = handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    assert res["status"] == "APPROVED"
    assert res["ticket_id"].startswith("TCK-2026-")
    assert res["approved_by"] == "Lead Engineer S. Raman"
    assert res["is_synthetic"] is True

    # Verify ticket in database
    ticket = memory_db.query(Ticket).filter_by(id=res["ticket_id"]).first()
    assert ticket is not None
    assert ticket.alert_id == "ALT-M104-001"
    assert ticket.approved_by == "Lead Engineer S. Raman"


def test_25_ticket_and_proposal_linkage_preserved(memory_db: Session):
    """Test 25: Bidirectional relationship between proposal and ticket is preserved."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Overhaul spindle assembly.",
        evidence={"vibration": 0.88},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Chief Engineer K. Patel",
        approver_role="Chief Maintenance Engineer",
    )

    res = handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    prop = memory_db.query(TicketProposal).filter_by(id=prop_res["proposal_id"]).first()
    assert prop.ticket_id == res["ticket_id"]
    assert prop.ticket is not None
    assert prop.ticket.id == res["ticket_id"]


def test_26_token_consumption_recorded(memory_db: Session):
    """Test 26: Token consumption is persistently recorded in consumed_tokens table."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    consumed = memory_db.query(ConsumedToken).filter_by(proposal_id=prop_res["proposal_id"]).first()
    assert consumed is not None
    assert consumed.approver_id == "Lead Engineer S. Raman"
    assert consumed.jti is not None


def test_27_proposal_marked_consumed(memory_db: Session):
    """Test 27: Staged proposal transitions from PENDING_APPROVAL to CONSUMED."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    prop = memory_db.query(TicketProposal).filter_by(id=prop_res["proposal_id"]).first()
    assert prop.status == "CONSUMED"
    assert prop.approved_at is not None


def test_28_duplicate_creation_rejected(memory_db: Session):
    """Test 28: Duplicate creation attempt fails."""
    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    handle_create_maintenance_ticket(
        proposal_id=prop_res["proposal_id"],
        approval_token=token,
        session_override=memory_db,
    )

    with pytest.raises(ValueError):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token=token,
            session_override=memory_db,
        )


def test_29_concurrent_creation_attempts(tmp_path):
    """Test 29: Concurrent creation requests produce at most one ticket."""
    test_db_path = tmp_path / "concurrent_ticket.db"
    engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False, "timeout": 30}, echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    init_session = SessionLocal()
    init_session.add(Machine(id="M104", name="CNC Machine 04", type="CNC Milling", criticality=5, production_impact=5))
    init_session.add(Alert(
        id="ALT-M104-001",
        machine_id="M104",
        risk=0.9,
        criticality=5,
        impact=5,
        priority_score=22.5,
        status="PENDING_APPROVAL",
        created_at=datetime.utcnow()
    ))
    init_session.commit()

    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing on M104.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=init_session,
    )
    init_session.close()

    token = HMACApprovalTokenManager.issue_token(
        proposal_id=prop_res["proposal_id"],
        payload_hash=prop_res["payload_hash"],
        approver_id="Lead Engineer S. Raman",
        approver_role="Lead Reliability Engineer",
    )

    successes = []
    failures = []

    def attempt_create():
        s = SessionLocal()
        try:
            res = handle_create_maintenance_ticket(
                proposal_id=prop_res["proposal_id"],
                approval_token=token,
                session_override=s,
            )
            successes.append(res)
        except Exception as exc:
            failures.append(exc)
        finally:
            s.close()

    t1 = threading.Thread(target=attempt_create)
    t2 = threading.Thread(target=attempt_create)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly 1 thread must succeed, and the other must fail with unique constraint or status error
    assert len(successes) == 1
    assert len(failures) == 1

    engine.dispose()


def test_30_failed_creation_leaves_no_partial_commits(memory_db: Session):
    """Test 30: Validation failure leaves no ticket or consumed token committed."""
    initial_ticket_count = memory_db.query(Ticket).count()
    initial_consumed_count = memory_db.query(ConsumedToken).count()

    prop_res = handle_propose_maintenance_ticket(
        machine_id="M104",
        recommendation="Replace front bearing on M104.",
        evidence={"test": 1},
        alert_id="ALT-M104-001",
        session_override=memory_db,
    )

    # Use a token with invalid signature
    with pytest.raises(InvalidTokenError):
        handle_create_maintenance_ticket(
            proposal_id=prop_res["proposal_id"],
            approval_token="invalid.signature.token",
            session_override=memory_db,
        )

    assert memory_db.query(Ticket).count() == initial_ticket_count
    assert memory_db.query(ConsumedToken).count() == initial_consumed_count


# ===========================================================================
# 4. MCP Integration Tests (Tests 31–32)
# ===========================================================================

def test_31_mcp_server_registers_all_nine_tools():
    """Test 31: MCP server instance registers exactly nine tools including proposal & creation."""
    server = create_mcp_server()
    assert hasattr(server, "_tool_manager")

    tool_names = list(server._tool_manager._tools.keys())
    assert len(tool_names) == 9
    assert set(tool_names) == {
        "ping",
        "get_machine_data",
        "detect_anomaly",
        "predict_failure_risk",
        "search_manuals",
        "get_maintenance_history",
        "check_defect_image",
        "propose_maintenance_ticket",
        "create_maintenance_ticket",
    }

    # Inspect tool schemas
    prop_tool = server._tool_manager.get_tool("propose_maintenance_ticket")
    assert prop_tool is not None
    assert "proposal" in prop_tool.description.lower()

    create_tool = server._tool_manager.get_tool("create_maintenance_ticket")
    assert create_tool is not None
    assert "cryptographic" in create_tool.description.lower()


@pytest.mark.asyncio
async def test_32_mcp_server_real_stdio_ticket_creation_lifecycle(tmp_path):
    """
    Test 32: Mandatory real stdio subprocess JSON-RPC 2.0 lifecycle verification:
    1. Spawns MCP server as independent subprocess on stdio transport.
    2. Initializes session via JSON-RPC handshake.
    3. Discovers all 9 tools via list_tools().
    4. Proposes maintenance ticket via JSON-RPC.
    5. Issues signed cryptographic approval token via development adapter.
    6. Authorizes and creates ticket via JSON-RPC.
    7. Asserts structured response schema and clean exit.
    """
    # Create isolated test database file for stdio subprocess
    test_db_path = tmp_path / "test_mcp_ticket.db"
    engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Seed M104 and alert
    session.add(Machine(id="M104", name="CNC Machine 04", type="CNC Milling", criticality=5, production_impact=5))
    session.add(Alert(
        id="ALT-M104-001",
        machine_id="M104",
        risk=0.9,
        criticality=5,
        impact=5,
        priority_score=22.5,
        status="PENDING_APPROVAL",
        created_at=datetime.utcnow()
    ))
    session.commit()
    session.close()

    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(REPO_ROOT)
    child_env["PYTHONUNBUFFERED"] = "1"
    child_env[APPROVAL_SECRET_ENV_VAR] = TEST_SECRET_KEY
    child_env["DATABASE_URL"] = f"sqlite:///{test_db_path}"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "backend.app.mcp_server"],
        cwd=str(REPO_ROOT),
        env=child_env,
    )

    with anyio.fail_after(120):
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_client:
                # 1. MCP Protocol Handshake
                init_result = await mcp_client.initialize()
                assert init_result is not None
                assert init_result.server_info.name == SERVER_NAME

                # 2. Tool Discovery: Exactly 9 tools
                tools_response = await mcp_client.list_tools()
                assert tools_response is not None
                tool_names = [t.name for t in tools_response.tools]
                assert len(tool_names) == 9
                assert "propose_maintenance_ticket" in tool_names
                assert "create_maintenance_ticket" in tool_names

                # 3. Propose ticket via stdio JSON-RPC
                prop_call = await mcp_client.call_tool(
                    "propose_maintenance_ticket",
                    arguments={
                        "machine_id": "M104",
                        "recommendation": "Replace front bearing and lubricate roller assembly.",
                        "evidence": {"vibration": 0.88, "defect": "surface_crack"},
                        "alert_id": "ALT-M104-001",
                        "confidence": 0.9,
                    },
                )
                assert prop_call is not None
                assert not getattr(prop_call, "isError", False)
                prop_data = prop_call.content[0].text if hasattr(prop_call.content[0], "text") else prop_call.content[0]
                if isinstance(prop_data, str):
                    prop_dict = json.loads(prop_data)
                else:
                    prop_dict = prop_data

                assert prop_dict["status"] == "PENDING_APPROVAL"
                proposal_id = prop_dict["proposal_id"]
                payload_hash = prop_dict["payload_hash"]

                # 4. Authenticate human engineer and issue signed token
                adapter = DevelopmentHumanApprovalAdapter()
                token = adapter.authenticate_and_approve(
                    engineer_id="ENG-RAMAN-01",
                    credential="RamanSecurePass2026!",
                    proposal_id=proposal_id,
                    proposal_data={
                        "machine_id": "M104",
                        "recommendation": "Replace front bearing and lubricate roller assembly.",
                        "evidence": {"vibration": 0.88, "defect": "surface_crack"},
                        "alert_id": "ALT-M104-001",
                        "confidence": 0.9,
                        "payload_hash": payload_hash,
                    },
                )

                # 5. Authorize and create ticket via stdio JSON-RPC
                create_call = await mcp_client.call_tool(
                    "create_maintenance_ticket",
                    arguments={
                        "proposal_id": proposal_id,
                        "approval_token": token,
                    },
                )
                assert create_call is not None
                assert not getattr(create_call, "isError", False)
                create_data = create_call.content[0].text if hasattr(create_call.content[0], "text") else create_call.content[0]
                if isinstance(create_data, str):
                    create_dict = json.loads(create_data)
                else:
                    create_dict = create_data

                assert create_dict["status"] == "APPROVED"
                assert create_dict["ticket_id"].startswith("TCK-2026-")
                assert create_dict["approved_by"] == "Lead Engineer S. Raman"
