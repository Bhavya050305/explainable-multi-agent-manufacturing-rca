"""
Unit tests for ManuMind AI typed shared state architecture.
Covers validation rules, security invariants, self-authorization rejection,
confidence bounds, serialization, and LangGraph StateGraph execution.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import pytest
from pydantic import ValidationError

from langgraph.graph import StateGraph, START, END

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    AnomalySeverity,
    AnomalyType,
    ConfidenceStatus,
    EvidenceSourceType,
    ExecutionMode,
    ExecutionStage,
    HumanApprovalStatus,
    VerificationStatus,
    WorkflowStatus,
)
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    AnomalyDetectionResult,
    CandidateRootCause,
    ConfidenceGovernance,
    EvidenceItem,
    HumanApprovalDetails,
    SensorMeasurementsSummary,
    TelemetryWindow,
)
from backend.app.agents.state import (
    ManuMindState,
    ManuMindStateModel,
    create_initial_state,
    validate_state,
)


def test_valid_initial_state_construction():
    now = datetime.now(timezone.utc)
    window = TelemetryWindow(
        start_time=datetime(2026, 11, 18, 8, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 18, 9, 0, 0, tzinfo=timezone.utc),
        sample_count=3600,
    )
    summary = SensorMeasurementsSummary(
        readings={"vibration": 2.45, "temperature": 52.1},
        units={"vibration": "mm/s", "temperature": "degC"},
    )

    state = create_initial_state(
        workflow_id="WF-2026-TEST-001",
        machine_id="M104",
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        telemetry_window=window,
        sensor_measurements=summary,
    )

    assert state["workflow_id"] == "WF-2026-TEST-001"
    assert state["machine_id"] == "M104"
    assert state["workflow_status"] == WorkflowStatus.INITIALIZED
    assert state["current_stage"] == ExecutionStage.INITIAL_TRIAGE
    assert state["human_approval"]["requires_human_approval"] is True
    assert state["human_approval"]["approval_status"] == HumanApprovalStatus.PENDING

    # Validate against Pydantic schema
    validated = validate_state(state)
    assert validated.workflow_id == "WF-2026-TEST-001"


def test_missing_required_identifiers_raises_validation_error():
    with pytest.raises(ValidationError):
        ManuMindStateModel(
            workflow_id="",  # Empty string rejected
            machine_id="M104",
        )

    with pytest.raises(ValidationError):
        ManuMindStateModel(
            workflow_id="WF-001",
            machine_id="",  # Empty machine_id rejected
        )


def test_invalid_confidence_values_rejected():
    now = datetime.now(timezone.utc)

    # Negative confidence
    with pytest.raises(ValidationError):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing failure",
            hypothesis="Bearing outer race defect",
            confidence=-0.1,  # Must be >= 0.0
            identified_at=now,
        )

    # Confidence exceeding 1.0
    with pytest.raises(ValidationError):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing failure",
            hypothesis="Bearing outer race defect",
            confidence=1.1,  # Must be <= 1.0
            identified_at=now,
        )

    # Confidence governance bounds
    with pytest.raises(ValidationError):
        ConfidenceGovernance(anomaly_confidence=1.5)

    with pytest.raises(ValidationError):
        ConfidenceGovernance(root_cause_confidence=-0.05)


def test_invalid_workflow_status_raises_validation_error():
    with pytest.raises(ValidationError):
        ManuMindStateModel(
            workflow_id="WF-001",
            machine_id="M104",
            workflow_status="NON_EXISTENT_STATUS",  # Not a valid WorkflowStatus enum
        )


def test_candidate_root_cause_cannot_self_assert_verified_status():
    now = datetime.now(timezone.utc)

    # Security Invariant: CandidateRootCause cannot directly self-assert VERIFIED status
    with pytest.raises(ValidationError, match="Security Invariant Violation"):
        CandidateRootCause(
            cause_id="RC-001",
            description="Bearing fatigue",
            hypothesis="Unverified hypothesis marked as verified",
            confidence=0.85,
            verification_status=VerificationStatus.VERIFIED,
            supporting_evidence_ids=["EV-001", "EV-002"],
            identified_at=now,
        )

    # Valid candidate as hypothesis (UNVERIFIED or HYPOTHESIS_PENDING)
    valid_candidate = CandidateRootCause(
        cause_id="RC-001",
        description="Bearing fatigue",
        hypothesis="Candidate hypothesis pending multi-modal corroboration",
        confidence=0.85,
        verification_status=VerificationStatus.HYPOTHESIS_PENDING,
        supporting_evidence_ids=["EV-001", "EV-002"],
        identified_at=now,
    )
    assert valid_candidate.verification_status == VerificationStatus.HYPOTHESIS_PENDING


def test_agent_self_authorization_strictly_rejected():
    # Security Invariant 1: An AI agent CANNOT self-authorize ticket creation
    now = datetime.now(timezone.utc)

    for agent_role in ["SUPERVISOR", "ANOMALY_DETECTION", "ROOT_CAUSE_ANALYSIS"]:
        with pytest.raises(ValidationError, match="Security Invariant 1 Violation"):
            HumanApprovalDetails(
                requires_human_approval=True,
                approval_status=HumanApprovalStatus.APPROVED,
                approval_reference="PROP-001",
                approved_by=agent_role,  # Agent role rejected!
                approval_timestamp=now,
            )

    # APPROVED without approved_by also rejected
    with pytest.raises(ValidationError, match="Security Invariant 1 Violation"):
        HumanApprovalDetails(
            requires_human_approval=True,
            approval_status=HumanApprovalStatus.APPROVED,
            approved_by=None,
        )

    # External human approval succeeds
    valid_approval = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.APPROVED,
        approval_reference="PROP-2026-001",
        approved_by="Lead Engineer S. Raman",
        approval_timestamp=now,
        approval_reason="Verified vibration spectrum matches maintenance manual guidelines",
    )
    assert valid_approval.approval_status == HumanApprovalStatus.APPROVED
    assert valid_approval.approved_by == "Lead Engineer S. Raman"


def test_synthetic_evidence_indicator_and_rag_citations_preserved():
    now = datetime.now(timezone.utc)
    ev = EvidenceItem(
        evidence_id="EV-SYN-001",
        source_type=EvidenceSourceType.RAG_DOCUMENT,
        source_reference="CNC_Milling_Troubleshooting.pdf",
        description="Spindle bearing replacement protocol",
        observed_at=now,
        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
        synthetic_data_indicator=True,
        citation_ids=["[CIT-1]", "[CIT-2]"],
        relevance_score=0.88,
    )

    assert ev.synthetic_data_indicator is True
    assert ev.citation_ids == ["[CIT-1]", "[CIT-2]"]
    assert ev.relevance_score == 0.88


def test_pydantic_serialization_and_deserialization_round_trip():
    now = datetime.now(timezone.utc)
    ev = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration",
        description="Amplitude spike",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    rec = AgentExecutionRecord(
        record_id="REC-001",
        agent_name=AgentName.ANOMALY_DETECTION,
        execution_status=AgentExecutionStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        execution_duration=1.25,
    )

    model = ManuMindStateModel(
        workflow_id="WF-ROUNDTRIP-001",
        machine_id="M104",
        workflow_status=WorkflowStatus.RUNNING,
        evidence_collection=[ev],
        agent_executions=[rec],
    )

    # JSON dump and load
    json_str = model.model_dump_json()
    assert "WF-ROUNDTRIP-001" in json_str

    deserialized = ManuMindStateModel.model_validate_json(json_str)
    assert deserialized.workflow_id == model.workflow_id
    assert len(deserialized.evidence_collection) == 1
    assert deserialized.evidence_collection[0].evidence_id == "EV-001"
    assert len(deserialized.agent_executions) == 1


def test_langgraph_stategraph_integration():
    """
    Demonstrates LangGraph StateGraph compatibility with ManuMindState channels and reducers.
    Simulates:
    1. Supervisor initializing the workflow
    2. Anomaly Detection Agent appending evidence and updating telemetry
    3. Root Cause Analysis Agent proposing a candidate cause
    """
    now = datetime.now(timezone.utc)

    # Node 1: Supervisor Node
    def supervisor_node(state: ManuMindState) -> Dict[str, Any]:
        rec = AgentExecutionRecord(
            record_id="EXEC-SUP-01",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=0.5,
        )
        return {
            "current_stage": ExecutionStage.ANOMALY_DETECTION,
            "agent_executions": [rec],
        }

    # Node 2: Anomaly Detection Node
    def anomaly_detection_node(state: ManuMindState) -> Dict[str, Any]:
        ev = EvidenceItem(
            evidence_id="EV-ANOM-01",
            source_type=EvidenceSourceType.TELEMETRY,
            source_reference="vibration_channel",
            description="Peak vibration measured at 10.98 mm/s exceeding 4.5 threshold",
            observed_at=now,
            source_agent=AgentName.ANOMALY_DETECTION,
        )
        anomaly_res = AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_type=AnomalyType.VIBRATION_SPIKE,
            severity=AnomalySeverity.HIGH,
            affected_sensors=["vibration"],
            detection_timestamp=now,
            supporting_evidence_references=["EV-ANOM-01"],
        )
        rec = AgentExecutionRecord(
            record_id="EXEC-ANOM-01",
            agent_name=AgentName.ANOMALY_DETECTION,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=1.2,
        )
        return {
            "current_stage": ExecutionStage.ROOT_CAUSE_ANALYSIS,
            "anomaly_detection_result": anomaly_res,
            "anomaly_type": AnomalyType.VIBRATION_SPIKE,
            "anomaly_severity": AnomalySeverity.HIGH,
            "affected_sensors": ["vibration"],
            "evidence_collection": [ev],
            "agent_executions": [rec],
        }

    # Node 3: Root Cause Analysis Node
    def rca_node(state: ManuMindState) -> Dict[str, Any]:
        ev_rag = EvidenceItem(
            evidence_id="EV-RAG-01",
            source_type=EvidenceSourceType.RAG_DOCUMENT,
            source_reference="CNC_Milling_Troubleshooting.pdf",
            description="Vibration at 10+ mm/s indicates imminent bearing failure",
            observed_at=now,
            source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
            citation_ids=["[CIT-1]"],
        )
        candidate = CandidateRootCause(
            cause_id="RC-BEARING-01",
            description="Main spindle bearing inner race fatigue failure",
            hypothesis="Spindle bearing race failure due to lubrication degradation",
            confidence=0.88,
            confidence_category=ConfidenceStatus.HIGH,
            supporting_evidence_ids=["EV-ANOM-01", "EV-RAG-01"],
            citation_ids=["[CIT-1]"],
            verification_status=VerificationStatus.HYPOTHESIS_PENDING,
            identified_at=now,
        )
        rec = AgentExecutionRecord(
            record_id="EXEC-RCA-01",
            agent_name=AgentName.ROOT_CAUSE_ANALYSIS,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=2.1,
        )
        return {
            "current_stage": ExecutionStage.HUMAN_APPROVAL_GATE,
            "candidate_root_causes": [candidate],
            "relevant_rag_citation_ids": ["[CIT-1]"],
            "evidence_collection": [ev_rag],
            "agent_executions": [rec],
        }

    # Build LangGraph StateGraph using ManuMindState
    builder = StateGraph(ManuMindState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("anomaly_detection", anomaly_detection_node)
    builder.add_node("root_cause_analysis", rca_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("supervisor", "anomaly_detection")
    builder.add_edge("anomaly_detection", "root_cause_analysis")
    builder.add_edge("root_cause_analysis", END)

    graph = builder.compile()

    # Initial state
    initial = create_initial_state(
        workflow_id="WF-GRAPH-TEST-001",
        machine_id="M104",
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
    )

    # Execute workflow graph
    final_output = graph.invoke(initial)

    # Assert graph execution outcomes
    assert final_output["workflow_id"] == "WF-GRAPH-TEST-001"
    assert final_output["current_stage"] == ExecutionStage.HUMAN_APPROVAL_GATE
    assert final_output["anomaly_type"] == AnomalyType.VIBRATION_SPIKE
    assert final_output["anomaly_severity"] == AnomalySeverity.HIGH
    assert final_output["affected_sensors"] == ["vibration"]

    # Reducer verifications:
    # 1. Evidence items merged deterministically
    assert len(final_output["evidence_collection"]) == 2
    assert final_output["evidence_collection"][0].evidence_id == "EV-ANOM-01"
    assert final_output["evidence_collection"][1].evidence_id == "EV-RAG-01"

    # 2. Candidate root causes merged
    assert len(final_output["candidate_root_causes"]) == 1
    assert final_output["candidate_root_causes"][0].cause_id == "RC-BEARING-01"

    # 3. RAG citations merged
    assert final_output["relevant_rag_citation_ids"] == ["[CIT-1]"]

    # 4. Agent executions merged chronologically
    assert len(final_output["agent_executions"]) == 3
    assert final_output["agent_executions"][0].record_id == "EXEC-SUP-01"
    assert final_output["agent_executions"][1].record_id == "EXEC-ANOM-01"
    assert final_output["agent_executions"][2].record_id == "EXEC-RCA-01"

    # 5. Full state passes Pydantic model validation
    validated_final = validate_state(final_output)
    assert validated_final.workflow_id == "WF-GRAPH-TEST-001"


def test_handling_of_failed_agent_execution():
    now = datetime.now(timezone.utc)
    rec_failed = AgentExecutionRecord(
        record_id="EXEC-FAIL-01",
        agent_name=AgentName.ANOMALY_DETECTION,
        execution_status=AgentExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
        execution_duration=0.1,
        error_summary="Failed to connect to postgresql://postgres:secret123@pooler.supabase.com:5432/db",
    )

    state_model = ManuMindStateModel(
        workflow_id="WF-FAIL-001",
        machine_id="M104",
        workflow_status=WorkflowStatus.FAILED,
        error_details=rec_failed.error_summary,
        agent_executions=[rec_failed],
    )

    # Verify secret is sanitized in state
    assert "secret123" not in state_model.error_details
    assert ":********@" in state_model.error_details
    assert state_model.agent_executions[0].execution_status == AgentExecutionStatus.FAILED
