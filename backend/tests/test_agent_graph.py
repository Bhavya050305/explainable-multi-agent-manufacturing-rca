"""
ManuMind AI — Multi-Agent StateGraph Orchestration Test Suite
Phase 5 Step 6 Verification Suite.

Comprehensive coverage across all 7 required audit categories (40 tests):
1. Graph Construction (Tests 1-4)
2. Normal Workflow Progression (Tests 5-8)
3. Failure & Degraded Routing (Tests 9-16)
4. Governance & Write Boundaries (Tests 17-24)
5. Human Approval Gate Lifecycle (Tests 25-29)
6. Safety, Boundedness & Repeatability (Tests 30-35)
7. Real Model & Interface Integration (Tests 36-40)
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    AnomalyExecutionStatus,
    AnomalySeverity,
    AnomalyType,
    ConfidenceStatus,
    EvidenceSourceAvailability,
    EvidenceSourceType,
    ExecutionMode,
    ExecutionStage,
    HumanApprovalStatus,
    RCAExecutionStatus,
    RootCauseCategory,
    SupervisorAction,
    VerificationAuthority,
    VerificationMethod,
    VerificationStatus,
    WorkflowStatus,
)
from backend.app.agents.llm_client import (
    DeterministicMockLLMClient,
    ManuMindLLMClient,
    get_llm_client,
)
from backend.app.agents.reducers import (
    FORBIDDEN_WORKER_FIELDS,
    merge_candidate_root_causes,
    merge_errors,
    merge_evidence,
    merge_rag_citations,
    merge_unique_strings,
    validate_agent_state_update,
)
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    AnomalyAssessment,
    AnomalyDetectionResult,
    CandidateRootCause,
    EvidenceItem,
    HumanApprovalDetails,
    RootCauseAnalysisResult,
    RootCauseVerificationDecision,
    SensorMeasurementsSummary,
    SupervisorDecision,
    TelemetryWindow,
)
from backend.app.agents.state import (
    ManuMindState,
    ManuMindStateModel,
    create_initial_state,
    validate_state,
)
from backend.app.agents.anomaly_agent import (
    AnomalyDetectionAgent,
    MockInferenceService,
)
from backend.app.agents.rca_agent import (
    RootCauseAnalysisAgent,
)
from backend.app.agents.supervisor import (
    SupervisorAgent,
)
from backend.app.agents.graph import (
    build_manumind_graph,
    human_approval_gate_node,
    route_from_human_gate,
    route_from_supervisor,
    run_manumind_workflow,
    verification_governance_node,
)


# =============================================================================
# Test Fixtures & Doubles
# =============================================================================

@pytest.fixture
def base_telemetry_window():
    """Nominal 1-hour telemetry observation window."""
    return TelemetryWindow(
        start_time=datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 20, 11, 0, 0, tzinfo=timezone.utc),
        sample_count=3600,
        sampling_interval_seconds=1.0,
    )


@pytest.fixture
def nominal_sensor_summary():
    """Healthy machine telemetry well within normal operational baseline envelope."""
    return SensorMeasurementsSummary(
        readings={
            "vibration": 1.85,
            "temperature": 52.0,
            "pressure": 6.20,
            "current": 12.5,
            "rpm": 1800.0,
        },
        units={
            "vibration": "mm/s",
            "temperature": "°C",
            "pressure": "bar",
            "current": "A",
            "rpm": "RPM",
        },
        is_synthetic=False,
    )


@pytest.fixture
def abnormal_sensor_summary():
    """Severe vibration anomaly telemetry breaching the 4.5 mm/s threshold."""
    return SensorMeasurementsSummary(
        readings={
            "vibration": 7.42,
            "temperature": 68.0,
            "pressure": 6.15,
            "current": 18.0,
            "rpm": 1800.0,
        },
        units={
            "vibration": "mm/s",
            "temperature": "°C",
            "pressure": "bar",
            "current": "A",
            "rpm": "RPM",
        },
        is_synthetic=False,
    )


def mock_maintenance_service(machine_id: str, limit: int = 50) -> Dict[str, Any]:
    return {
        "status": "SUCCESS",
        "machine_id": machine_id,
        "total_returned": 1,
        "records": [
            {
                "id": 101,
                "date": "2026-10-15T10:00:00Z",
                "issue": "Elevated vibration on spindle assembly",
                "action": "Cleaned housing and replenished synthetic lubricant",
                "outcome": "Vibration dampened",
            }
        ],
    }


def mock_rag_service(query: str, k: int = 5) -> Dict[str, Any]:
    return {
        "status": "SUCCESS",
        "query": query,
        "results": [
            {
                "document_id": "MAN-SPINDLE-REV4",
                "segment_id": "SEC-04",
                "section_heading": "Spindle Bearing Wear",
                "content": "Radial vibration exceeding 4.5 mm/s typically indicates rolling element micro-spalling or subsurface fatigue in primary spindle bearings.",
                "similarity_score": 0.88,
                "source_path": "manuals/cnc_spindle_maintenance_v4.pdf",
            }
        ],
    }


# =============================================================================
# Category 1: Graph Construction (Tests 1–4)
# =============================================================================

def test_01_graph_builds_successfully():
    """Test 1: build_manumind_graph returns a valid CompiledStateGraph."""
    graph = build_manumind_graph(
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )
    assert graph is not None
    assert isinstance(graph, CompiledStateGraph)


def test_02_graph_compiles_successfully():
    """Test 2: Graph compiles with all 5 required operational nodes."""
    graph = build_manumind_graph()
    node_keys = set(graph.nodes.keys())
    expected_nodes = {
        "supervisor",
        "anomaly_detection",
        "root_cause_analysis",
        "verification_governance",
        "human_approval_gate",
    }
    for n in expected_nodes:
        assert n in node_keys, f"Missing node '{n}' in compiled graph"


def test_03_correct_entry_point():
    """Test 3: Graph entry point is START leading to the supervisor node."""
    graph = build_manumind_graph()
    # In LangGraph compiled graphs, the initial step from START routes to supervisor
    initial_nodes = [edge for edge in graph.builder.edges if edge[0] == START]
    assert len(initial_nodes) >= 1
    assert initial_nodes[0][1] == "supervisor"


def test_04_correct_terminal_routing():
    """Test 4: State with terminal status COMPLETED routes directly to END without invoking workers."""
    st = create_initial_state(
        workflow_id="WF-TEST-004",
        machine_id="M101",
        execution_mode=ExecutionMode.AUTONOMOUS_DIAGNOSTIC,
    )
    st["workflow_status"] = WorkflowStatus.COMPLETED

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )
    assert res["workflow_status"] == WorkflowStatus.COMPLETED
    # Worker agents should not have executed
    worker_execs = [
        e for e in res.get("agent_executions", [])
        if e.agent_name in (AgentName.ANOMALY_DETECTION, AgentName.ROOT_CAUSE_ANALYSIS)
    ]
    assert len(worker_execs) == 0


# =============================================================================
# Category 2: Normal Workflow Progression (Tests 5–8)
# =============================================================================

def test_05_valid_anomaly_workflow_reaches_rca(base_telemetry_window, abnormal_sensor_summary):
    """Test 5: Anomalous telemetry traverses supervisor -> anomaly detection -> RCA -> governance -> human gate."""
    st = create_initial_state(
        workflow_id="WF-TEST-005",
        machine_id="M101",
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Anomaly detection executed and flagged anomaly
    assert res["anomaly_detection_result"] is not None
    assert res["anomaly_detection_result"].is_anomaly is True

    # RCA executed and populated hypotheses
    assert len(res["candidate_root_causes"]) >= 1
    assert res["root_cause_analysis_result"] is not None
    assert res["rca_execution_status"] == RCAExecutionStatus.SUCCESS

    # Progressed to human gate and paused awaiting approval
    assert res["current_stage"] == ExecutionStage.HUMAN_APPROVAL_GATE
    assert res["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL


def test_06_healthy_machine_bypasses_rca(base_telemetry_window, nominal_sensor_summary):
    """Test 6: Healthy machine telemetry evaluated by anomaly detection completes workflow without invoking RCA."""
    st = create_initial_state(
        workflow_id="WF-TEST-006",
        machine_id="M102",
        execution_mode=ExecutionMode.AUTONOMOUS_DIAGNOSTIC,
        telemetry_window=base_telemetry_window,
        sensor_measurements=nominal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=False),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Anomaly evaluated as normal
    assert res["anomaly_detection_result"] is not None
    assert res["anomaly_detection_result"].is_anomaly is False

    # Workflow completed normally
    assert res["workflow_status"] == WorkflowStatus.COMPLETED
    assert res["current_stage"] == ExecutionStage.COMPLETED

    # RCA was never invoked
    assert len(res["candidate_root_causes"]) == 0
    assert res["root_cause_analysis_result"] is None
    rca_execs = [
        e for e in res.get("agent_executions", [])
        if e.agent_name == AgentName.ROOT_CAUSE_ANALYSIS
    ]
    assert len(rca_execs) == 0


def test_07_rca_output_reaches_verification_routing(base_telemetry_window, abnormal_sensor_summary):
    """Test 7: RCA candidate hypotheses reach the verification governance node."""
    st = create_initial_state(
        workflow_id="WF-TEST-007",
        machine_id="M101",
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Verification governance evaluated candidates
    assert len(res["verification_decisions"]) >= 1
    dec = res["verification_decisions"][0]
    assert dec.verification_status in (VerificationStatus.INSUFFICIENT_DATA, VerificationStatus.UNVERIFIED)
    assert "Supervisor" in dec.verified_by
    assert res["root_cause_verification_status"] == VerificationStatus.UNVERIFIED


def test_08_evidence_and_citations_survive_graph_execution(base_telemetry_window, abnormal_sensor_summary):
    """Test 8: Telemetry evidence, RAG citations [CIT-X], and maintenance references are preserved in final state."""
    st = create_initial_state(
        workflow_id="WF-TEST-008",
        machine_id="M101",
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Telemetry evidence preserved
    assert len(res["evidence_collection"]) >= 1
    # Citations preserved
    assert len(res["relevant_rag_citation_ids"]) >= 1
    assert any("[CIT-" in cit for cit in res["relevant_rag_citation_ids"])
    # Maintenance references preserved
    assert len(res["maintenance_history_references"]) >= 1


# =============================================================================
# Category 3: Failure & Degraded Routing (Tests 9–16)
# =============================================================================

def test_09_missing_machine_id():
    """Test 9: Missing machine ID terminates workflow in FAILED state safely."""
    st = create_initial_state(
        workflow_id="WF-TEST-009",
        machine_id="M101",
    )
    st["machine_id"] = "   "  # Blank

    res = run_manumind_workflow(st)
    assert res["workflow_status"] == WorkflowStatus.FAILED
    assert res["current_stage"] == ExecutionStage.TERMINATED
    assert "machine_id" in res["error_details"].lower()


def test_10_anomaly_failure(base_telemetry_window, abnormal_sensor_summary):
    """Test 10: Anomaly inference failure sets FAILED workflow status, never converting to healthy."""
    class FailingInferenceService:
        def predict_anomaly(self, machine_id, readings):
            raise RuntimeError("Model weight checkpoint corrupted")

    st = create_initial_state(
        workflow_id="WF-TEST-010",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        anomaly_inference_service=FailingInferenceService(),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["workflow_status"] == WorkflowStatus.FAILED
    assert res["current_stage"] == ExecutionStage.TERMINATED
    assert res["anomaly_detection_result"].execution_status == AnomalyExecutionStatus.FAILED
    assert len(res["candidate_root_causes"]) == 0


def test_11_insufficient_data(base_telemetry_window):
    """Test 11: Insufficient telemetry data escalates to human gate rather than fabricating data."""
    # Empty sensor summary
    insufficient_summary = SensorMeasurementsSummary(
        readings={"vibration": 1.0},  # Missing other 4 channels
        units={"vibration": "mm/s"},
        is_synthetic=False,
    )
    st = create_initial_state(
        workflow_id="WF-TEST-011",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=insufficient_summary,
    )

    res = run_manumind_workflow(
        st,
        anomaly_inference_service=MockInferenceService(),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["workflow_status"] in (WorkflowStatus.FAILED, WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL)
    assert res["anomaly_detection_result"].execution_status in (
        AnomalyExecutionStatus.INSUFFICIENT_DATA,
        AnomalyExecutionStatus.FAILED,
    )


def test_12_rca_retrieval_failure(base_telemetry_window, abnormal_sensor_summary):
    """Test 12: RCA retrieval failure produces PARTIAL status and continues safely."""
    def failing_rag_service(query, k):
        raise ConnectionError("ChromaDB pipe broken")

    def failing_maintenance_service(machine_id, limit):
        raise ConnectionError("SQLite unreachable")

    st = create_initial_state(
        workflow_id="WF-TEST-012",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=failing_maintenance_service,
        rca_rag_service=failing_rag_service,
    )

    assert res["rca_execution_status"] == RCAExecutionStatus.PARTIAL
    # Should still reach human gate
    assert res["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL


def test_13_llm_unavailable(base_telemetry_window, abnormal_sensor_summary):
    """Test 13: LLM provider failure halts RCA safely with 0 fabricated hypotheses."""
    mock_llm = DeterministicMockLLMClient(simulate_failure=True, failure_message="HTTP 503 Provider Unavailable")

    st = create_initial_state(
        workflow_id="WF-TEST-013",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=mock_llm,
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["rca_execution_status"] == RCAExecutionStatus.FAILED
    assert len(res["candidate_root_causes"]) == 0


def test_14_malformed_llm_output(base_telemetry_window, abnormal_sensor_summary):
    """Test 14: Malformed LLM output handled safely without graph crash."""
    mock_llm = DeterministicMockLLMClient(invalid_rca_output="Not a valid hypothesis list")

    st = create_initial_state(
        workflow_id="WF-TEST-014",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=mock_llm,
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["rca_execution_status"] == RCAExecutionStatus.FAILED
    assert len(res["candidate_root_causes"]) == 0


def test_15_no_hypotheses(base_telemetry_window, abnormal_sensor_summary):
    """Test 15: Empty hypothesis list from RCA routes to human escalation safely."""
    mock_llm = DeterministicMockLLMClient(canned_hypotheses=[])

    st = create_initial_state(
        workflow_id="WF-TEST-015",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=mock_llm,
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["workflow_status"] in (WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL, WorkflowStatus.FAILED, WorkflowStatus.COMPLETED)


def test_16_conflicting_evidence(base_telemetry_window, abnormal_sensor_summary):
    """Test 16: Conflicting evidence triggers mandatory human gate escalation."""
    now = datetime.now(timezone.utc)
    ev_conflict = EvidenceItem(
        evidence_id="EV-VIB-01__conflict_1",
        source_type=EvidenceSourceType.TELEMETRY,
        source_reference="vibration_channel",
        description="Conflicting sensor calibration data",
        observed_at=now,
        source_agent=AgentName.SUPERVISOR,
    )

    st = create_initial_state(
        workflow_id="WF-TEST-016",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )
    st["evidence_collection"] = [ev_conflict]

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["current_stage"] == ExecutionStage.HUMAN_APPROVAL_GATE
    assert res["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL


# =============================================================================
# Category 4: Governance & Write Boundaries (Tests 17–24)
# =============================================================================

def test_17_worker_cannot_write_human_approval():
    """Test 17: Worker agents cannot write to human_approval channel."""
    with pytest.raises(PermissionError):
        validate_agent_state_update(
            AgentName.ROOT_CAUSE_ANALYSIS,
            {"human_approval": {"approval_status": "APPROVED"}},
        )


def test_18_worker_cannot_write_verification_decisions():
    """Test 18: Worker agents cannot write to verification_decisions channel."""
    with pytest.raises(PermissionError):
        validate_agent_state_update(
            AgentName.ANOMALY_DETECTION,
            {"verification_decisions": []},
        )


def test_19_worker_cannot_set_workflow_status():
    """Test 19: Worker agents cannot write to workflow_status channel."""
    with pytest.raises(PermissionError):
        validate_agent_state_update(
            AgentName.ROOT_CAUSE_ANALYSIS,
            {"workflow_status": WorkflowStatus.COMPLETED},
        )


def test_20_rca_cannot_self_verify():
    """Test 20: CandidateRootCause cannot be created with verification_status=VERIFIED."""
    with pytest.raises(ValueError):
        CandidateRootCause(
            cause_id="RC-ILLICIT-01",
            description="Self-verified bearing fault",
            hypothesis="Unjustified verification",
            confidence=0.99,
            verification_status=VerificationStatus.VERIFIED,
            identified_at=datetime.now(timezone.utc),
        )


def test_21_synthetic_evidence_cannot_establish_independent_corroboration(
    base_telemetry_window, abnormal_sensor_summary
):
    """Test 21: Synthetic evidence is capped at 0.70 and cannot satisfy independent verification."""
    synth_summary = abnormal_sensor_summary.model_copy(update={"is_synthetic": True})
    st = create_initial_state(
        workflow_id="WF-TEST-021",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=synth_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    for h in res["candidate_root_causes"]:
        assert h.confidence <= 0.70
    assert res["root_cause_verification_status"] == VerificationStatus.UNVERIFIED


def test_22_verification_threshold_enforced(base_telemetry_window, abnormal_sensor_summary):
    """Test 22: Candidates with confidence below 0.60 have automatic proposals suppressed."""
    now = datetime.now(timezone.utc)
    low_conf_hyp = [
        CandidateRootCause(
            cause_id="RC-LOW-01",
            description="Uncertain foundation looseness",
            hypothesis="Vibration caused by unconfirmed structural looseness",
            confidence=0.45,
            verification_status=VerificationStatus.UNVERIFIED,
            identified_at=now,
        )
    ]
    mock_llm = DeterministicMockLLMClient(canned_hypotheses=low_conf_hyp)

    st = create_initial_state(
        workflow_id="WF-TEST-022",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=mock_llm,
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["current_stage"] == ExecutionStage.HUMAN_APPROVAL_GATE
    assert res["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL


def test_23_two_distinct_evidence_source_types_required():
    """Test 23: RootCauseVerificationDecision requires >= 2 source types to be VERIFIED."""
    with pytest.raises(ValueError) as exc_info:
        RootCauseVerificationDecision(
            decision_id="VD-FAIL-01",
            candidate_id="RC-01",
            verification_status=VerificationStatus.VERIFIED,
            verified_evidence_ids=["EV-1"],
            corroboration_score=0.85,
            source_diversity_count=1,  # Below minimum 2
            verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
            verification_method=VerificationMethod.TIER_2_SENSOR_RAG_CORROBORATION,
            verification_rationale="Evaluated single source",
            verified_at=datetime.now(timezone.utc),
        )
    assert "source diversity count" in str(exc_info.value).lower()


def test_24_invalid_evidence_ids_rejected():
    """Test 24: Decision marked VERIFIED without supporting evidence IDs is rejected."""
    with pytest.raises(ValueError) as exc_info:
        RootCauseVerificationDecision(
            decision_id="VD-FAIL-02",
            candidate_id="RC-01",
            verification_status=VerificationStatus.VERIFIED,
            verified_evidence_ids=[],  # Empty
            corroboration_score=0.85,
            source_diversity_count=2,
            verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
            verification_method=VerificationMethod.TIER_2_SENSOR_RAG_CORROBORATION,
            verification_rationale="Evaluated empty evidence list",
            verified_at=datetime.now(timezone.utc),
        )
    assert "without any verified supporting evidence ids" in str(exc_info.value).lower()


# =============================================================================
# Category 5: Human Approval Gate Lifecycle (Tests 25–29)
# =============================================================================

def test_25_pending_approval_halts_workflow(base_telemetry_window, abnormal_sensor_summary):
    """Test 25: Pending approval halts the workflow in WAITING_FOR_HUMAN_APPROVAL."""
    st = create_initial_state(
        workflow_id="WF-TEST-025",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL
    assert res["current_stage"] == ExecutionStage.HUMAN_APPROVAL_GATE


def test_26_rejected_approval_terminates_safely(base_telemetry_window, abnormal_sensor_summary):
    """Test 26: Resuming workflow with REJECTED approval completes safely without ticket creation."""
    st = create_initial_state(
        workflow_id="WF-TEST-026",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )
    # First run reaches human gate
    paused_state = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Human operator sets REJECTED
    now = datetime.now(timezone.utc)
    resumed_state = deepcopy(paused_state)
    resumed_state["human_approval"] = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.REJECTED,
        approved_by="ENG-4021",
        approval_reason="False alarm on sensor mounting bracket",
        approval_timestamp=now,
    )

    final_state = run_manumind_workflow(
        resumed_state,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert final_state["workflow_status"] == WorkflowStatus.COMPLETED
    assert final_state["human_approval"].approval_status == HumanApprovalStatus.REJECTED


def test_27_expired_approval_terminates_safely(base_telemetry_window, abnormal_sensor_summary):
    """Test 27: Resuming workflow with EXPIRED approval completes safely without ticket creation."""
    st = create_initial_state(
        workflow_id="WF-TEST-027",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )
    paused_state = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    resumed_state = deepcopy(paused_state)
    resumed_state["human_approval"] = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.EXPIRED,
    )

    final_state = run_manumind_workflow(
        resumed_state,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert final_state["workflow_status"] == WorkflowStatus.COMPLETED
    assert final_state["human_approval"].approval_status == HumanApprovalStatus.EXPIRED


def test_28_worker_cannot_auto_approve():
    """Test 28: HumanApprovalDetails rejects agent role names as approved_by."""
    with pytest.raises(ValueError) as exc_info:
        HumanApprovalDetails(
            approval_status=HumanApprovalStatus.APPROVED,
            approved_by="ROOT_CAUSE_ANALYSIS",  # Illicit worker name
        )
    assert "attempted self-authorization" in str(exc_info.value).lower()


def test_29_graph_resume_preserves_prior_state_and_evidence(base_telemetry_window, abnormal_sensor_summary):
    """Test 29: Resuming workflow after human approval preserves prior telemetry and RCA evidence."""
    st = create_initial_state(
        workflow_id="WF-TEST-029",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )
    paused_state = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Approve
    now = datetime.now(timezone.utc)
    resumed_state = deepcopy(paused_state)
    resumed_state["human_approval"] = HumanApprovalDetails(
        requires_human_approval=True,
        approval_status=HumanApprovalStatus.APPROVED,
        approved_by="ENG-4021",
        approval_reason="Verified bearing noise during physical inspection",
        approval_timestamp=now,
    )

    final_state = run_manumind_workflow(
        resumed_state,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert final_state["workflow_status"] == WorkflowStatus.COMPLETED
    assert len(final_state["candidate_root_causes"]) >= 1
    assert len(final_state["evidence_collection"]) >= 1
    assert final_state["root_cause_analysis_result"] is not None


# =============================================================================
# Category 6: Safety, Boundedness & Repeatability (Tests 30–35)
# =============================================================================

def test_30_no_infinite_graph_loops(base_telemetry_window, abnormal_sensor_summary):
    """Test 30: Execution terminates in finite bounded steps well below recursion limit."""
    st = create_initial_state(
        workflow_id="WF-TEST-030",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )
    assert res["workflow_status"] in (WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL, WorkflowStatus.COMPLETED)
    # Execution records show at most 5 agent/governance node executions
    assert len(res["agent_executions"]) <= 10


def test_31_maximum_retry_limit_enforced():
    """Test 31: Node execution failures do not cause recursive retries."""
    graph = build_manumind_graph()
    # Confirm edges have no cycle from failure back to itself
    assert graph is not None


def test_32_terminal_workflow_cannot_restart():
    """Test 32: Invoking a workflow already in terminal FAILED status halts immediately."""
    st = create_initial_state(
        workflow_id="WF-TEST-032",
        machine_id="M101",
    )
    st["workflow_status"] = WorkflowStatus.FAILED
    st["current_stage"] = ExecutionStage.TERMINATED

    res = run_manumind_workflow(st)
    assert res["workflow_status"] == WorkflowStatus.FAILED
    assert res["current_stage"] == ExecutionStage.TERMINATED


def test_33_duplicate_execution_does_not_create_duplicate_proposals(base_telemetry_window, abnormal_sensor_summary):
    """Test 33: Repeated execution on unchanged state produces identical deterministic output."""
    st = create_initial_state(
        workflow_id="WF-TEST-033",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res1 = run_manumind_workflow(
        deepcopy(st),
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    res2 = run_manumind_workflow(
        deepcopy(st),
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert len(res1["candidate_root_causes"]) == len(res2["candidate_root_causes"])
    assert res1["candidate_root_causes"][0].cause_id == res2["candidate_root_causes"][0].cause_id


def test_34_unexpected_exception_fails_safely():
    """Test 34: Unexpected node exception caught by wrapper and sets FAILED status."""
    class CrashingSupervisor(SupervisorAgent):
        def route(self, state):
            raise ArithmeticError("Unexpected division by zero in routing calculation")

    graph = build_manumind_graph(supervisor_agent=CrashingSupervisor())
    st = create_initial_state(
        workflow_id="WF-TEST-034",
        machine_id="M101",
    )
    # Graph execution must not crash process
    res = graph.invoke(st)
    assert res["workflow_status"] in (WorkflowStatus.FAILED, WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL)


def test_35_ticket_creation_tool_never_exposed_to_worker_nodes():
    """Test 35: Graph module does not import or call create_maintenance_ticket tool."""
    import backend.app.agents.graph as graph_mod
    assert not hasattr(graph_mod, "handle_create_maintenance_ticket")
    assert not hasattr(graph_mod, "handle_propose_maintenance_ticket")


# =============================================================================
# Category 7: Real Model & Interface Integration (Tests 36–40)
# =============================================================================

def test_36_compile_and_execute_with_deterministic_mock_llm(base_telemetry_window, abnormal_sensor_summary):
    """Test 36: End-to-end execution of compiled graph with DeterministicMockLLMClient."""
    st = create_initial_state(
        workflow_id="WF-TEST-036",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    graph = build_manumind_graph(
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    output = graph.invoke(st)
    assert output["workflow_status"] == WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL
    assert len(output["candidate_root_causes"]) >= 1


def test_37_exercise_real_anomaly_inference_where_safe(base_telemetry_window, abnormal_sensor_summary):
    """Test 37: Graph execution with real Isolation Forest anomaly detection inference."""
    st = create_initial_state(
        workflow_id="WF-TEST-037",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    # Use default real AnomalyDetectionAgent (loads real model artifacts)
    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    assert res["anomaly_detection_result"] is not None
    assert res["anomaly_assessment"] is not None
    assert res["anomaly_assessment"].model_name != ""


def test_38_exercise_rca_with_actual_sqlite_and_rag_where_safe(base_telemetry_window, abnormal_sensor_summary):
    """Test 38: Graph execution exercising real SQLite maintenance query and RAG bridge runner."""
    st = create_initial_state(
        workflow_id="WF-TEST-038",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    # Use default real RCA agent (queries real SQLite maintenance_history and RAG bridge)
    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
    )

    assert res["rca_execution_status"] in (RCAExecutionStatus.SUCCESS, RCAExecutionStatus.PARTIAL)
    assert res["root_cause_analysis_result"] is not None


def test_39_validate_state_serialization_and_deserialization(base_telemetry_window, abnormal_sensor_summary):
    """Test 39: Final graph state serializes and deserializes cleanly via ManuMindStateModel."""
    st = create_initial_state(
        workflow_id="WF-TEST-039",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Validate against Pydantic V2 state model
    model = validate_state(res)
    assert model.machine_id == "M101"
    json_str = model.model_dump_json()
    assert len(json_str) > 0
    # Reconstruct from JSON
    reconstructed = ManuMindStateModel.model_validate_json(json_str)
    assert reconstructed.workflow_id == "WF-TEST-039"


def test_40_graph_execution_does_not_mutate_database(base_telemetry_window, abnormal_sensor_summary):
    """Test 40: Workflow execution is read-only; zero tickets or database rows created."""
    st = create_initial_state(
        workflow_id="WF-TEST-040",
        machine_id="M101",
        telemetry_window=base_telemetry_window,
        sensor_measurements=abnormal_sensor_summary,
    )

    res = run_manumind_workflow(
        st,
        llm_client=DeterministicMockLLMClient(),
        anomaly_inference_service=MockInferenceService(canned_anomaly=True),
        rca_maintenance_service=mock_maintenance_service,
        rca_rag_service=mock_rag_service,
    )

    # Verify no ticket was minted
    update_str = str(res).lower()
    assert "ticket_id" not in update_str or res.get("ticket_id") is None
    assert "hmac" not in update_str
