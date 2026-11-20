"""
ManuMind AI — Root-Cause Verification Governance & Write-Boundary Tests
Phase 5 Step 2.2 Security Invariant and Lifecycle State Machine Verification Suite.

Validates:
1. Candidate Root Cause vs. Verification Decision separation.
2. RootCauseVerificationDecision corroboration rules (score >= 0.60, source diversity >= 2, non-empty evidence IDs).
3. Prohibition of worker agents acting as verification authority.
4. Cross-field state validation linking VERIFIED status to authoritative decisions and evidence provenance.
5. Human approval state machine lifecycle transitions (PENDING -> APPROVED/REJECTED/EXPIRED, terminal state immutability).
6. Prohibition of agent self-authorization.
7. Reducers (merge_verification_decisions, merge_human_approval) determinism, immutability, and conflict preservation.
8. Agent write-boundary enforcement via validate_agent_state_update.
"""

from datetime import datetime, timezone
import math
import pytest
from pydantic import ValidationError

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    ConfidenceStatus,
    EvidenceSourceType,
    ExecutionMode,
    ExecutionStage,
    HumanApprovalStatus,
    VerificationAuthority,
    VerificationMethod,
    VerificationStatus,
    WorkflowStatus,
)
from backend.app.agents.reducers import (
    FORBIDDEN_WORKER_FIELDS,
    merge_human_approval,
    merge_verification_decisions,
    validate_agent_state_update,
)
from backend.app.agents.schemas import (
    CandidateRootCause,
    EvidenceItem,
    HumanApprovalDetails,
    RootCauseVerificationDecision,
)
from backend.app.agents.state import (
    ManuMindStateModel,
    create_initial_state,
    validate_state,
)


# =============================================================================
# Category 1: Candidate Root Cause & Verification Decision Governance
# =============================================================================

def test_candidate_root_cause_cannot_directly_self_assert_verified():
    """Security Invariant: CandidateRootCause cannot be instantiated with VERIFIED status."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="Security Invariant Violation"):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing spall",
            hypothesis="Outer race fatigue",
            confidence=0.92,
            verification_status=VerificationStatus.VERIFIED,
            supporting_evidence_ids=["EV-001", "EV-002"],
            identified_at=now,
        )


def test_candidate_root_cause_accepts_unverified_and_pending():
    """CandidateRootCause accepts unverified hypothesis lifecycle statuses."""
    now = datetime.now(timezone.utc)
    cand_unverified = CandidateRootCause(
        cause_id="RC-001",
        description="Bearing spall",
        hypothesis="Outer race fatigue",
        confidence=0.75,
        verification_status=VerificationStatus.UNVERIFIED,
        supporting_evidence_ids=["EV-001"],
        identified_at=now,
    )
    assert cand_unverified.verification_status == VerificationStatus.UNVERIFIED

    cand_pending = CandidateRootCause(
        cause_id="RC-002",
        description="Lubricant starvation",
        hypothesis="Oil film breakdown",
        confidence=0.81,
        verification_status=VerificationStatus.HYPOTHESIS_PENDING,
        supporting_evidence_ids=["EV-001", "EV-003"],
        identified_at=now,
    )
    assert cand_pending.verification_status == VerificationStatus.HYPOTHESIS_PENDING


def test_candidate_root_cause_rejects_nan_and_infinite_confidence():
    """Candidate confidence rejects NaN, infinity, and out-of-bound floats."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing spall",
            hypothesis="Hypothesis with NaN confidence",
            confidence=float("nan"),
            identified_at=now,
        )

    with pytest.raises(ValidationError):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing spall",
            hypothesis="Hypothesis with inf confidence",
            confidence=float("inf"),
            identified_at=now,
        )


def test_verification_decision_verified_requires_supporting_evidence():
    """RootCauseVerificationDecision VERIFIED requires non-empty verified_evidence_ids."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="without any verified supporting evidence IDs"):
        RootCauseVerificationDecision(
            decision_id="DEC-001",
            candidate_id="RC-001",
            verification_status=VerificationStatus.VERIFIED,
            verified_evidence_ids=[],  # Empty!
            corroboration_score=0.85,
            source_diversity_count=2,
            verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
            verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
            verification_rationale="Corroborated across telemetry and RAG manuals.",
            verified_at=now,
        )


def test_verification_decision_verified_requires_minimum_corroboration_score():
    """RootCauseVerificationDecision VERIFIED requires corroboration_score >= 0.60."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="minimum corroboration threshold"):
        RootCauseVerificationDecision(
            decision_id="DEC-001",
            candidate_id="RC-001",
            verification_status=VerificationStatus.VERIFIED,
            verified_evidence_ids=["EV-001", "EV-002"],
            corroboration_score=0.59,  # < 0.60!
            source_diversity_count=2,
            verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
            verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
            verification_rationale="Insufficient corroboration score.",
            verified_at=now,
        )


def test_verification_decision_verified_requires_source_diversity():
    """RootCauseVerificationDecision VERIFIED requires source_diversity_count >= 2."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="Source diversity count"):
        RootCauseVerificationDecision(
            decision_id="DEC-001",
            candidate_id="RC-001",
            verification_status=VerificationStatus.VERIFIED,
            verified_evidence_ids=["EV-001", "EV-002"],
            corroboration_score=0.85,
            source_diversity_count=1,  # < 2!
            verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
            verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
            verification_rationale="Single source type insufficient for multi-modal verification.",
            verified_at=now,
        )


def test_verification_decision_rejects_worker_agents_as_authority():
    """Worker agents (ANOMALY_DETECTION, ROOT_CAUSE_ANALYSIS) cannot render verification decisions."""
    now = datetime.now(timezone.utc)
    for worker in [AgentName.ANOMALY_DETECTION.value, AgentName.ROOT_CAUSE_ANALYSIS.value]:
        with pytest.raises(ValidationError, match="Security Invariant Violation"):
            RootCauseVerificationDecision(
                decision_id="DEC-001",
                candidate_id="RC-001",
                verification_status=VerificationStatus.VERIFIED,
                verified_evidence_ids=["EV-001", "EV-002"],
                corroboration_score=0.85,
                source_diversity_count=2,
                verified_by=worker,  # Illegal worker agent authority!
                verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
                verification_rationale="Worker agent self-assertion.",
                verified_at=now,
            )


def test_verification_decision_refuted_and_insufficient_data():
    """Non-VERIFIED decisions (REFUTED, INSUFFICIENT_DATA) do not require high corroboration score."""
    now = datetime.now(timezone.utc)
    refuted = RootCauseVerificationDecision(
        decision_id="DEC-002",
        candidate_id="RC-002",
        verification_status=VerificationStatus.REFUTED,
        verified_evidence_ids=[],
        corroboration_score=0.15,
        source_diversity_count=1,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_2_SENSOR_RAG_CORROBORATION,
        verification_rationale="Contradicted by historical maintenance logs showing recent shaft replacement.",
        verified_at=now,
    )
    assert refuted.verification_status == VerificationStatus.REFUTED

    insufficient = RootCauseVerificationDecision(
        decision_id="DEC-003",
        candidate_id="RC-003",
        verification_status=VerificationStatus.INSUFFICIENT_DATA,
        verified_evidence_ids=[],
        corroboration_score=0.45,
        source_diversity_count=1,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_3_HUMAN_EXPERT_ESCALATION,
        verification_rationale="Acoustic sensor data offline; cannot confirm or refute hypothesis.",
        verified_at=now,
    )
    assert insufficient.verification_status == VerificationStatus.INSUFFICIENT_DATA


def test_state_model_verified_status_requires_authoritative_decision():
    """StateModel enforces that root_cause_verification_status=VERIFIED requires a matching verified decision."""
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="Peak 12.4 mm/s vibration at 2X shaft rate",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    ev2 = EvidenceItem(
        evidence_id="EV-002",
        source_type=EvidenceSourceType.RAG_DOCUMENT,
        source_reference="bearing_failure_modes.pdf",
        description="Harmonic peak at 2X shaft rate indicates inner ring spalling",
        observed_at=now,
        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
    )
    cand = CandidateRootCause(
        cause_id="RC-001",
        description="Spindle bearing race failure",
        hypothesis="Severe spalling on bearing inner race",
        confidence=0.88,
        supporting_evidence_ids=["EV-001", "EV-002"],
        identified_at=now,
    )

    # Missing verification_decisions while root_cause_verification_status=VERIFIED
    with pytest.raises(ValidationError, match="without an authoritative RootCauseVerificationDecision"):
        ManuMindStateModel(
            workflow_id="WF-TEST-001",
            machine_id="M104",
            candidate_root_causes=[cand],
            evidence_collection=[ev1, ev2],
            root_cause_verification_status=VerificationStatus.VERIFIED,
            verification_decisions=[],  # Empty!
        )


def test_state_model_verified_decision_must_reference_existing_candidate():
    """StateModel rejects verified decision referencing non-existent candidate ID."""
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="Peak vibration",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    cand = CandidateRootCause(
        cause_id="RC-001",
        description="Spindle bearing race failure",
        hypothesis="Spalling",
        confidence=0.88,
        supporting_evidence_ids=["EV-001"],
        identified_at=now,
    )
    decision = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-NONEXISTENT",  # Candidate does not exist in state!
        verification_status=VerificationStatus.VERIFIED,
        verified_evidence_ids=["EV-001"],
        corroboration_score=0.88,
        source_diversity_count=2,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
        verification_rationale="Corroborated.",
        verified_at=now,
    )

    with pytest.raises(ValidationError, match="references candidate 'RC-NONEXISTENT' which does not exist"):
        ManuMindStateModel(
            workflow_id="WF-TEST-002",
            machine_id="M104",
            candidate_root_causes=[cand],
            evidence_collection=[ev1],
            root_cause_verification_status=VerificationStatus.VERIFIED,
            verification_decisions=[decision],
        )


def test_state_model_verified_decision_must_reference_existing_evidence():
    """StateModel rejects verified decision referencing evidence ID not present in state."""
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="Peak vibration",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    cand = CandidateRootCause(
        cause_id="RC-001",
        description="Spindle bearing race failure",
        hypothesis="Spalling",
        confidence=0.88,
        supporting_evidence_ids=["EV-001"],
        identified_at=now,
    )
    decision = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-001",
        verification_status=VerificationStatus.VERIFIED,
        verified_evidence_ids=["EV-001", "EV-GHOST-999"],  # EV-GHOST-999 not in state!
        corroboration_score=0.88,
        source_diversity_count=2,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
        verification_rationale="Corroborated.",
        verified_at=now,
    )

    with pytest.raises(ValidationError, match="references evidence ID 'EV-GHOST-999' which is not present"):
        ManuMindStateModel(
            workflow_id="WF-TEST-003",
            machine_id="M104",
            candidate_root_causes=[cand],
            evidence_collection=[ev1],
            root_cause_verification_status=VerificationStatus.VERIFIED,
            verification_decisions=[decision],
        )


def test_state_model_fully_corroborated_verification_succeeds():
    """Valid multi-source verified state model passes complete cross-validation."""
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="High vibration amplitude detected",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    ev2 = EvidenceItem(
        evidence_id="EV-002",
        source_type=EvidenceSourceType.RAG_DOCUMENT,
        source_reference="maintenance_manual.pdf",
        description="Spectrum matches bearing cage defect profile",
        observed_at=now,
        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
    )
    cand = CandidateRootCause(
        cause_id="RC-001",
        description="Spindle bearing failure",
        hypothesis="Bearing cage degradation",
        confidence=0.89,
        supporting_evidence_ids=["EV-001", "EV-002"],
        identified_at=now,
    )
    decision = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-001",
        verification_status=VerificationStatus.VERIFIED,
        verified_evidence_ids=["EV-001", "EV-002"],
        corroboration_score=0.91,
        source_diversity_count=2,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
        verification_rationale="Corroborated across telemetry spectrum and historical maintenance manual.",
        verified_at=now,
    )

    state = ManuMindStateModel(
        workflow_id="WF-TEST-004",
        machine_id="M104",
        candidate_root_causes=[cand],
        evidence_collection=[ev1, ev2],
        root_cause_verification_status=VerificationStatus.VERIFIED,
        verification_decisions=[decision],
    )
    assert state.root_cause_verification_status == VerificationStatus.VERIFIED
    assert len(state.verification_decisions) == 1
    assert state.verification_decisions[0].decision_id == "DEC-001"


# =============================================================================
# Category 2: Human Approval Lifecycle State Machine
# =============================================================================

def test_human_approval_lifecycle_valid_transitions():
    """Valid transitions from PENDING: APPROVED, REJECTED, EXPIRED."""
    now = datetime.now(timezone.utc)
    base = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.PENDING,
    )

    # Valid transitions from PENDING
    base.validate_transition_to(HumanApprovalStatus.APPROVED)
    base.validate_transition_to(HumanApprovalStatus.REJECTED)
    base.validate_transition_to(HumanApprovalStatus.EXPIRED)
    base.validate_transition_to(HumanApprovalStatus.PENDING)  # Idempotent


def test_human_approval_terminal_state_approved_immutable():
    """APPROVED is a terminal state and cannot transition to any other status."""
    now = datetime.now(timezone.utc)
    approved = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.APPROVED,
        approved_by="Lead Engineer S. Raman",
        approval_timestamp=now,
    )

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'APPROVED' to 'REJECTED'"):
        approved.validate_transition_to(HumanApprovalStatus.REJECTED)

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'APPROVED' to 'PENDING'"):
        approved.validate_transition_to(HumanApprovalStatus.PENDING)

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'APPROVED' to 'EXPIRED'"):
        approved.validate_transition_to(HumanApprovalStatus.EXPIRED)


def test_human_approval_terminal_state_rejected_immutable():
    """REJECTED is a terminal state; strictly rejects transition to APPROVED."""
    now = datetime.now(timezone.utc)
    rejected = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.REJECTED,
        approval_reason="Telemetry indicates false alarm due to workpiece vibration",
        approval_timestamp=now,
    )

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'REJECTED' to 'APPROVED'"):
        rejected.validate_transition_to(HumanApprovalStatus.APPROVED)

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'REJECTED' to 'PENDING'"):
        rejected.validate_transition_to(HumanApprovalStatus.PENDING)


def test_human_approval_terminal_state_expired_immutable():
    """EXPIRED is a terminal state; strictly rejects transition to APPROVED."""
    now = datetime.now(timezone.utc)
    expired = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.EXPIRED,
        approval_reason="Human operator review window timed out after 24 hours",
        approval_timestamp=now,
    )

    with pytest.raises(ValueError, match="Cannot transition from terminal state 'EXPIRED' to 'APPROVED'"):
        expired.validate_transition_to(HumanApprovalStatus.APPROVED)


def test_human_approval_not_required_cannot_transition():
    """NOT_REQUIRED state cannot transition to any other state."""
    not_req = HumanApprovalDetails(
        requires_human_approval=False,
        approval_status=HumanApprovalStatus.NOT_REQUIRED,
    )
    with pytest.raises(ValueError, match="Cannot transition from NOT_REQUIRED to 'APPROVED'"):
        not_req.validate_transition_to(HumanApprovalStatus.APPROVED)


def test_human_approval_approved_by_agent_strictly_rejected():
    """HumanApprovalDetails strictly forbids AI agent identities in approved_by."""
    now = datetime.now(timezone.utc)
    for agent in ["SUPERVISOR", "ANOMALY_DETECTION", "ROOT_CAUSE_ANALYSIS"]:
        with pytest.raises(ValidationError, match="Security Invariant 1 Violation"):
            HumanApprovalDetails(
                requires_human_approval=True,
                approval_status=HumanApprovalStatus.APPROVED,
                approved_by=agent,
                approval_timestamp=now,
            )


# =============================================================================
# Category 3: Reducers & Agent Write-Boundary Governance
# =============================================================================

def test_merge_verification_decisions_deduplication_and_immutability():
    """merge_verification_decisions deduplicates identical decisions and preserves inputs."""
    now = datetime.now(timezone.utc)
    dec1 = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-001",
        verification_status=VerificationStatus.VERIFIED,
        verified_evidence_ids=["EV-001", "EV-002"],
        corroboration_score=0.90,
        source_diversity_count=2,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
        verification_rationale="Consensus reached.",
        verified_at=now,
    )
    dec1_copy = dec1.model_copy()

    initial = [dec1]
    merged = merge_verification_decisions(initial, [dec1_copy])

    assert len(merged) == 1
    assert merged[0].decision_id == "DEC-001"
    # Immutability
    assert len(initial) == 1


def test_merge_verification_decisions_conflict_preservation():
    """merge_verification_decisions preserves differing decisions for same decision_id via disambiguation."""
    t1 = datetime(2026, 11, 18, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 18, 10, 5, 0, tzinfo=timezone.utc)
    dec1 = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-001",
        verification_status=VerificationStatus.INSUFFICIENT_DATA,
        verified_evidence_ids=[],
        corroboration_score=0.40,
        source_diversity_count=1,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_3_HUMAN_EXPERT_ESCALATION,
        verification_rationale="Initial assessment insufficient.",
        verified_at=t1,
    )
    dec1_alt = RootCauseVerificationDecision(
        decision_id="DEC-001",
        candidate_id="RC-001",
        verification_status=VerificationStatus.VERIFIED,
        verified_evidence_ids=["EV-001", "EV-002"],
        corroboration_score=0.92,
        source_diversity_count=2,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS,
        verification_rationale="Corroborated after secondary telemetry ingestion.",
        verified_at=t2,
    )

    merged = merge_verification_decisions([dec1], [dec1_alt])

    assert len(merged) == 2
    assert merged[0].decision_id == "DEC-001"
    assert merged[0].verification_status == VerificationStatus.INSUFFICIENT_DATA
    assert merged[1].decision_id == "DEC-001__alt_1"
    assert merged[1].verification_status == VerificationStatus.VERIFIED


def test_merge_human_approval_enforces_lifecycle():
    """merge_human_approval accepts valid transitions and rejects invalid terminal transitions."""
    now = datetime.now(timezone.utc)
    pending = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.PENDING,
    )
    approved = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.APPROVED,
        approved_by="Shift Manager R. Kumar",
        approval_timestamp=now,
    )
    rejected = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.REJECTED,
        approval_reason="False alarm",
        approval_timestamp=now,
    )

    # Valid transition: PENDING -> APPROVED
    res_approved = merge_human_approval(pending, approved)
    assert res_approved.approval_status == HumanApprovalStatus.APPROVED

    # Valid transition: PENDING -> REJECTED
    res_rejected = merge_human_approval(pending, rejected)
    assert res_rejected.approval_status == HumanApprovalStatus.REJECTED

    # Invalid transition: APPROVED -> REJECTED
    with pytest.raises(ValueError, match="Cannot transition from terminal state 'APPROVED' to 'REJECTED'"):
        merge_human_approval(res_approved, rejected)

    # Invalid transition: REJECTED -> APPROVED
    with pytest.raises(ValueError, match="Cannot transition from terminal state 'REJECTED' to 'APPROVED'"):
        merge_human_approval(res_rejected, approved)


def test_validate_agent_state_update_forbids_worker_agent_restricted_fields():
    """Worker agents cannot write to human_approval, verification_decisions, or workflow_status."""
    for worker in [AgentName.ANOMALY_DETECTION, AgentName.ROOT_CAUSE_ANALYSIS]:
        # Attempt to write human_approval
        with pytest.raises(PermissionError, match="Security Write-Boundary Violation"):
            validate_agent_state_update(
                worker,
                {"human_approval": {"approval_status": "APPROVED"}},
            )

        # Attempt to write verification_decisions
        with pytest.raises(PermissionError, match="Security Write-Boundary Violation"):
            validate_agent_state_update(
                worker,
                {"verification_decisions": []},
            )

        # Attempt to write workflow_status
        with pytest.raises(PermissionError, match="Security Write-Boundary Violation"):
            validate_agent_state_update(
                worker,
                {"workflow_status": "COMPLETED"},
            )


def test_validate_agent_state_update_permits_allowed_worker_and_supervisor_updates():
    """Worker agents can write permitted channels; Supervisor can write supervisor fields."""
    now = datetime.now(timezone.utc)
    # Permitted worker update: evidence and candidate causes
    cand = CandidateRootCause(
        cause_id="RC-001",
        description="Bearing spall",
        hypothesis="Outer race fatigue",
        confidence=0.78,
        identified_at=now,
    )
    worker_update = {
        "candidate_root_causes": [cand],
        "supporting_evidence": ["EV-001"],
    }
    validated_worker = validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, worker_update)
    assert validated_worker == worker_update

    # Permitted supervisor update
    supervisor_update = {
        "workflow_status": WorkflowStatus.RUNNING,
        "current_stage": ExecutionStage.ANOMALY_DETECTION,
    }
    validated_sup = validate_agent_state_update(AgentName.SUPERVISOR, supervisor_update)
    assert validated_sup == supervisor_update
