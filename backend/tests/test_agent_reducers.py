"""
Unit tests for ManuMind AI LangGraph reducers.
Verifies determinism, deduplication, conflict preservation, chronological ordering,
immutability, and safe handling of empty/None updates.
"""

from datetime import datetime, timezone
import pytest

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    ConfidenceStatus,
    EvidenceSourceType,
    VerificationStatus,
)
from backend.app.agents.reducers import (
    merge_agent_executions,
    merge_candidate_root_causes,
    merge_errors,
    merge_evidence,
    merge_rag_citations,
    merge_unique_strings,
    overwrite_supervisor_field,
    sanitize_error_message,
)
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    CandidateRootCause,
    EvidenceItem,
)


def test_merge_unique_strings_immutability_and_deduplication():
    initial = ["sensor_1", "sensor_2"]
    update = ["sensor_2", "sensor_3"]

    merged = merge_unique_strings(initial, update)

    assert merged == ["sensor_1", "sensor_2", "sensor_3"]
    # Verify input immutability
    assert initial == ["sensor_1", "sensor_2"]
    assert update == ["sensor_2", "sensor_3"]


def test_merge_unique_strings_handles_none_and_empty():
    assert merge_unique_strings(None, None) == []
    assert merge_unique_strings(["a"], None) == ["a"]
    assert merge_unique_strings(None, ["b"]) == ["b"]
    assert merge_unique_strings(["a"], "b") == ["a", "b"]


def test_merge_rag_citations_preserves_order_and_deduplicates():
    initial = ["[CIT-1]", "[CIT-2]"]
    update = ["[CIT-2]", "[CIT-3]"]

    merged = merge_rag_citations(initial, update)
    assert merged == ["[CIT-1]", "[CIT-2]", "[CIT-3]"]
    assert initial == ["[CIT-1]", "[CIT-2]"]


def test_sanitize_error_message_masks_credentials():
    url_with_pass = "postgresql://postgres:mysecretpass123@aws-0.pooler.supabase.com:5432/postgres"
    sanitized = sanitize_error_message(url_with_pass)
    assert "mysecretpass123" not in sanitized
    assert ":********@" in sanitized

    bearer_str = "Error in tool call: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
    sanitized_bearer = sanitize_error_message(bearer_str)
    assert "eyJhbGci" not in sanitized_bearer
    assert "********" in sanitized_bearer


def test_merge_errors_sanitizes_and_appends():
    initial = ["Init error"]
    update = ["Connection failed to postgresql://user:pass123@host:5432/db"]

    merged = merge_errors(initial, update)
    assert len(merged) == 2
    assert "pass123" not in merged[1]
    assert ":********@" in merged[1]
    # Verify immutability
    assert initial == ["Init error"]


def test_overwrite_supervisor_field():
    assert overwrite_supervisor_field("STAGE_1", "STAGE_2") == "STAGE_2"
    assert overwrite_supervisor_field("STAGE_1", None) == "STAGE_1"
    assert overwrite_supervisor_field(None, "STAGE_1") == "STAGE_1"


def test_merge_evidence_concatenation_and_immutability():
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
        source_type=EvidenceSourceType.SHAP_ANALYSIS,
        source_reference="model_shap_vibration",
        description="Vibration contributed 0.62 to anomaly score",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )

    initial = [ev1]
    update = [ev2]

    merged = merge_evidence(initial, update)
    assert len(merged) == 2
    assert merged[0].evidence_id == "EV-001"
    assert merged[1].evidence_id == "EV-002"

    # Input immutability
    assert len(initial) == 1
    assert len(update) == 1


def test_merge_evidence_deduplication_of_identical_evidence():
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="High vibration amplitude detected",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    # Identical copy
    ev1_copy = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="High vibration amplitude detected",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )

    initial = [ev1]
    merged = merge_evidence(initial, [ev1_copy])
    assert len(merged) == 1
    assert merged[0].evidence_id == "EV-001"


def test_merge_evidence_conflict_preservation():
    now = datetime.now(timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="temp_channel",
        description="Normal temperature within envelope",
        observed_at=now,
        source_agent=AgentName.ANOMALY_DETECTION,
    )
    # Conflicting evidence with same ID but differing description and source agent
    ev1_conflict = EvidenceItem(
        evidence_id="EV-001",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="temp_channel",
        description="Conflicting sensor re-read indicates elevated temperature",
        observed_at=now,
        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
    )

    initial = [ev1]
    merged = merge_evidence(initial, [ev1_conflict])

    # Conflicting evidence must NOT be silently dropped or overwritten!
    assert len(merged) == 2
    assert merged[0].evidence_id == "EV-001"
    assert merged[0].description == "Normal temperature within envelope"
    assert merged[1].evidence_id == "EV-001__conflict_1"
    assert merged[1].source_agent == AgentName.ROOT_CAUSE_ANALYSIS


def test_merge_candidate_root_causes_preserves_competing_hypotheses():
    now = datetime.now(timezone.utc)
    c1 = CandidateRootCause(
        cause_id="RC-001",
        description="Inner bearing race spalling",
        hypothesis="Fatigue failure on inner bearing race",
        confidence=0.75,
        confidence_category=ConfidenceStatus.MODERATE,
        supporting_evidence_ids=["EV-001"],
        identified_at=now,
    )
    # Competing candidate with same ID but different hypothesis
    c1_alt = CandidateRootCause(
        cause_id="RC-001",
        description="Lubrication starvation caused overheating",
        hypothesis="Degraded oil viscosity led to metal-on-metal contact",
        confidence=0.65,
        confidence_category=ConfidenceStatus.MODERATE,
        supporting_evidence_ids=["EV-002"],
        identified_at=now,
    )

    initial = [c1]
    merged = merge_candidate_root_causes(initial, [c1_alt])

    assert len(merged) == 2
    assert merged[0].cause_id == "RC-001"
    assert merged[0].description == "Inner bearing race spalling"
    assert merged[1].cause_id == "RC-001__alt_1"
    assert merged[1].description == "Lubrication starvation caused overheating"


def test_merge_agent_executions_chronological_ordering_and_in_place_lifecycle_updates():
    t1 = datetime(2026, 11, 18, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 18, 10, 5, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 11, 18, 10, 10, 0, tzinfo=timezone.utc)

    # Initial running execution
    rec1 = AgentExecutionRecord(
        record_id="EXEC-001",
        agent_name=AgentName.SUPERVISOR,
        execution_status=AgentExecutionStatus.RUNNING,
        started_at=t1,
    )

    # Completed update for rec1
    rec1_updated = AgentExecutionRecord(
        record_id="EXEC-001",
        agent_name=AgentName.SUPERVISOR,
        execution_status=AgentExecutionStatus.COMPLETED,
        started_at=t1,
        completed_at=t2,
        execution_duration=300.0,
    )

    # Second execution starting later
    rec2 = AgentExecutionRecord(
        record_id="EXEC-002",
        agent_name=AgentName.ANOMALY_DETECTION,
        execution_status=AgentExecutionStatus.RUNNING,
        started_at=t3,
    )

    # Test update existing
    initial = [rec1]
    updated_state = merge_agent_executions(initial, [rec1_updated])
    assert len(updated_state) == 1
    assert updated_state[0].execution_status == AgentExecutionStatus.COMPLETED
    assert updated_state[0].execution_duration == 300.0

    # Test append next
    further_state = merge_agent_executions(updated_state, [rec2])
    assert len(further_state) == 2
    assert further_state[0].record_id == "EXEC-001"
    assert further_state[1].record_id == "EXEC-002"

    # Test chronological sorting if update arrives out of order
    rec_early = AgentExecutionRecord(
        record_id="EXEC-000",
        agent_name=AgentName.SUPERVISOR,
        execution_status=AgentExecutionStatus.COMPLETED,
        started_at=datetime(2026, 11, 18, 9, 50, 0, tzinfo=timezone.utc),
    )
    ordered = merge_agent_executions(further_state, [rec_early])
    assert len(ordered) == 3
    assert ordered[0].record_id == "EXEC-000"
    assert ordered[1].record_id == "EXEC-001"
    assert ordered[2].record_id == "EXEC-002"
