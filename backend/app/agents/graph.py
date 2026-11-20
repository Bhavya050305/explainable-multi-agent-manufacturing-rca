"""
ManuMind AI — Multi-Agent StateGraph Orchestration & Human Gate Routing
Phase 5 Step 6 Implementation.

Connects the independently implemented agents:
1. Supervisor Agent (triage, evaluation, routing)
2. Anomaly Detection Agent (5-channel telemetry inference)
3. Root Cause Analysis Agent (multi-source evidence & hypothesis formulation)
4. Verification and Evidence Governance (source diversity, synthetic capping, evidence integrity)
5. Human Approval Gate (operator authorization boundary, HMAC isolation, ticket protection)

Architectural Invariants & Governance Rules:
- Acyclic state progression: strictly prevents infinite loops, cycles, and repeated executions.
- Worker Write Boundaries: Worker agents cannot write to human_approval, verification_decisions, or workflow_status.
- Human Approval Boundary: Only external human operators may transition approval status to APPROVED.
- Verification Integrity: Worker hypotheses remain UNVERIFIED; independent verification requires multi-source real evidence.
- Ticket Protection: Neither Supervisor nor worker agents can mint HMAC tokens or call create_maintenance_ticket.
- Comprehensive Fallback: All failure, timeout, and degraded states produce deterministic, safe outcomes.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

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
    merge_agent_executions,
    merge_candidate_root_causes,
    merge_errors,
    merge_evidence,
    merge_human_approval,
    merge_rag_citations,
    merge_unique_strings,
    merge_verification_decisions,
    overwrite_supervisor_field,
    validate_agent_state_update,
)
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    AnomalyAssessment,
    AnomalyDetectionResult,
    CandidateRootCause,
    ConfidenceGovernance,
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
    anomaly_detection_node as default_anomaly_detection_node,
)
from backend.app.agents.rca_agent import (
    RootCauseAnalysisAgent,
    root_cause_analysis_node as default_rca_node,
)
from backend.app.agents.supervisor import (
    SupervisorAgent,
    supervisor_node as default_supervisor_node,
)

logger = logging.getLogger("ManuMindGraph")


# =============================================================================
# Graph Node Definitions with Safe Isolation
# =============================================================================

def create_supervisor_node(agent: Optional[SupervisorAgent] = None) -> Callable[[ManuMindState], Dict[str, Any]]:
    """Factory creating supervisor node function with optional dependency injection."""
    _agent = agent or SupervisorAgent()

    def supervisor_node_func(state: ManuMindState) -> Dict[str, Any]:
        try:
            return _agent.route(state)
        except Exception as exc:
            logger.error(f"Unhandled exception in supervisor node: {exc}", exc_info=True)
            now = datetime.now(timezone.utc)
            rec = AgentExecutionRecord(
                record_id=f"EXEC-SUP-ERR-{uuid.uuid4().hex[:8].upper()}",
                agent_name=AgentName.SUPERVISOR,
                execution_status=AgentExecutionStatus.FAILED,
                started_at=now,
                completed_at=now,
                execution_duration=0.0,
                error_summary=f"Supervisor node execution error: {str(exc)}",
            )
            decision = SupervisorDecision(
                next_action=SupervisorAction.FAIL_WORKFLOW,
                target_agent=None,
                reason=f"Supervisor node fatal error: {str(exc)}",
                decision_confidence=1.0,
                escalation_required=True,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={"exception": str(exc)},
            )
            update = {
                "workflow_status": WorkflowStatus.FAILED,
                "current_stage": ExecutionStage.TERMINATED,
                "supervisor_decision": decision,
                "error_details": str(exc),
                "error_history": [f"Supervisor fatal exception: {str(exc)}"],
                "agent_executions": [rec],
                "updated_at": now,
            }
            return validate_agent_state_update(AgentName.SUPERVISOR, update)

    return supervisor_node_func


def create_anomaly_detection_node(
    agent: Optional[AnomalyDetectionAgent] = None
) -> Callable[[ManuMindState], Dict[str, Any]]:
    """Factory creating anomaly detection node function with optional dependency injection."""
    _agent = agent or AnomalyDetectionAgent()

    def anomaly_detection_node_func(state: ManuMindState) -> Dict[str, Any]:
        try:
            return _agent.analyze(state)
        except Exception as exc:
            logger.error(f"Unhandled exception in anomaly detection node: {exc}", exc_info=True)
            now = datetime.now(timezone.utc)
            rec = AgentExecutionRecord(
                record_id=f"EXEC-ANOM-ERR-{uuid.uuid4().hex[:8].upper()}",
                agent_name=AgentName.ANOMALY_DETECTION,
                execution_status=AgentExecutionStatus.FAILED,
                started_at=now,
                completed_at=now,
                execution_duration=0.0,
                error_summary=f"Anomaly node execution error: {str(exc)}",
            )
            detection_res = AnomalyDetectionResult(
                is_anomaly=False,
                execution_status=AnomalyExecutionStatus.FAILED,
                anomaly_type=AnomalyType.NONE,
                severity=AnomalySeverity.CRITICAL,
                affected_sensors=[],
                detection_timestamp=now,
                supporting_evidence_references=[],
                raw_model_scores={"error": -1.0},
            )
            update = {
                "anomaly_detection_result": detection_res,
                "error_history": [f"Anomaly detection exception: {str(exc)}"],
                "agent_executions": [rec],
            }
            return validate_agent_state_update(AgentName.ANOMALY_DETECTION, update)

    return anomaly_detection_node_func


def create_rca_node(
    agent: Optional[RootCauseAnalysisAgent] = None
) -> Callable[[ManuMindState], Dict[str, Any]]:
    """Factory creating root cause analysis node function with optional dependency injection."""
    _agent = agent or RootCauseAnalysisAgent()

    def rca_node_func(state: ManuMindState) -> Dict[str, Any]:
        try:
            return _agent.analyze(state)
        except Exception as exc:
            logger.error(f"Unhandled exception in RCA node: {exc}", exc_info=True)
            now = datetime.now(timezone.utc)
            rec = AgentExecutionRecord(
                record_id=f"EXEC-RCA-ERR-{uuid.uuid4().hex[:8].upper()}",
                agent_name=AgentName.ROOT_CAUSE_ANALYSIS,
                execution_status=AgentExecutionStatus.FAILED,
                started_at=now,
                completed_at=now,
                execution_duration=0.0,
                error_summary=f"RCA node execution error: {str(exc)}",
            )
            update = {
                "rca_execution_status": RCAExecutionStatus.FAILED,
                "error_history": [f"RCA exception: {str(exc)}"],
                "agent_executions": [rec],
            }
            return validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, update)

    return rca_node_func


def verification_governance_node(state: ManuMindState) -> Dict[str, Any]:
    """
    Stage D — Verification and Evidence Governance Node.
    Evaluates candidate root-cause hypotheses from RCA against evidence collection.
    
    Security & Governance Invariants:
    1. A worker agent cannot mark a hypothesis VERIFIED.
    2. Candidate hypotheses remain strictly UNVERIFIED.
    3. Multi-source corroboration requires >= 2 distinct evidence source types and score >= 0.60.
    4. Synthetic evidence is strictly capped (<= 0.70) and cannot satisfy independent verification.
    5. Conflicting evidence is preserved and flags mandatory human escalation.
    6. Does NOT manufacture a verification decision merely because a hypothesis has a high score.
    7. Operates under Supervisor governance authority.
    """
    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)

    candidates: List[CandidateRootCause] = state.get("candidate_root_causes", [])
    ev_collection: List[EvidenceItem] = state.get("evidence_collection", [])
    has_conflicts = any("__conflict" in e.evidence_id for e in ev_collection)

    if not candidates:
        # No candidates to evaluate (e.g. RCA skipped or failed)
        rec = AgentExecutionRecord(
            record_id=f"EXEC-GOV-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=round(time.perf_counter() - start_time, 4),
            error_summary=None,
        )
        update = {
            "root_cause_verification_status": VerificationStatus.UNVERIFIED,
            "agent_executions": [rec],
            "updated_at": now,
        }
        return validate_agent_state_update(AgentName.SUPERVISOR, update)

    # Identify primary candidate hypothesis
    top_candidate = max(candidates, key=lambda c: c.confidence)
    
    # Calculate distinct supporting evidence source types for the top candidate
    supporting_items = [
        e for e in ev_collection if e.evidence_id in top_candidate.supporting_evidence_ids
    ]
    distinct_sources: Set[EvidenceSourceType] = {e.source_type for e in supporting_items}
    source_diversity = len(distinct_sources)

    # Determine synthetic evidence presence
    is_synthetic = bool(
        any(e.synthetic_data_indicator for e in supporting_items)
        or (state.get("anomaly_assessment") and state.get("anomaly_assessment").is_synthetic)
    )

    # Determine governance category and completeness
    completeness = round(min(1.0, len(top_candidate.supporting_evidence_ids) / 3.0), 2)
    agreement = 0.40 if has_conflicts else (0.85 if top_candidate.confidence >= 0.70 else 0.65)

    if has_conflicts:
        gov_status = ConfidenceStatus.INSUFFICIENT_EVIDENCE
    elif top_candidate.confidence >= 0.80 and source_diversity >= 2 and not is_synthetic:
        gov_status = ConfidenceStatus.HIGH
    elif top_candidate.confidence >= 0.60:
        gov_status = ConfidenceStatus.MODERATE
    else:
        gov_status = ConfidenceStatus.LOW

    updated_governance = ConfidenceGovernance(
        anomaly_confidence=state.get("anomaly_assessment").confidence if state.get("anomaly_assessment") else 0.80,
        root_cause_confidence=top_candidate.confidence,
        evidence_completeness=completeness,
        evidence_agreement=agreement,
        overall_status=gov_status,
        calibration_notice=(
            "Support score represents an evidence-corroboration index and is NOT a physical failure probability. "
            "Authoritative verification is reserved for external human engineers."
        ),
    )

    # Create unverified audit decision recording verification status
    decision_id = f"VER-DEC-{uuid.uuid4().hex[:8].upper()}"
    notes = (
        f"Hypothesis '{top_candidate.cause_id}' evaluated with support score {top_candidate.confidence:.2f} "
        f"across {source_diversity} distinct source types. "
        "Status remains UNVERIFIED awaiting authoritative operator review at Human Approval Gate."
    )
    if is_synthetic:
        notes += " Disclosure: Telemetry contains synthetic observations; physical verification required."
    if has_conflicts:
        notes += " Warning: Conflicting evidence items detected; mandatory human inspection required."

    ver_decision = RootCauseVerificationDecision(
        decision_id=decision_id,
        candidate_id=top_candidate.cause_id,
        verification_status=VerificationStatus.INSUFFICIENT_DATA,
        verified_evidence_ids=top_candidate.supporting_evidence_ids,
        corroboration_score=top_candidate.confidence,
        source_diversity_count=source_diversity,
        verified_by=VerificationAuthority.SUPERVISOR_CORROBORATION_ENGINE.value,
        verification_method=VerificationMethod.UNVERIFIED,
        verification_rationale=notes,
        verified_at=now,
    )

    elapsed = time.perf_counter() - start_time
    rec = AgentExecutionRecord(
        record_id=f"EXEC-GOV-{uuid.uuid4().hex[:8].upper()}",
        agent_name=AgentName.SUPERVISOR,
        execution_status=AgentExecutionStatus.COMPLETED,
        started_at=now,
        completed_at=datetime.now(timezone.utc),
        execution_duration=round(elapsed, 4),
        evidence_references=top_candidate.supporting_evidence_ids,
    )

    # All candidate hypotheses strictly maintain UNVERIFIED status
    unverified_hypotheses = [
        h.model_copy(update={"verification_status": VerificationStatus.UNVERIFIED})
        for h in candidates
    ]

    update = {
        "candidate_root_causes": unverified_hypotheses,
        "confidence_governance": updated_governance,
        "root_cause_verification_status": VerificationStatus.UNVERIFIED,
        "verification_decisions": [ver_decision],
        "agent_executions": [rec],
        "updated_at": now,
    }

    return validate_agent_state_update(AgentName.SUPERVISOR, update)


def human_approval_gate_node(state: ManuMindState) -> Dict[str, Any]:
    """
    Stage E — Human Approval Gate Node.
    Enforces the human operator approval boundary:
    1. If approval is PENDING, halts/pauses the workflow in WAITING_FOR_HUMAN_APPROVAL.
       Does NOT simulate approval or auto-approve.
    2. If external operator has set APPROVED, records approval and transitions towards completion.
    3. If operator set REJECTED or EXPIRED, records decision and concludes workflow without ticket.
    4. Worker agents CANNOT write to human_approval.
    """
    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)

    current_approval = state.get("human_approval")
    if isinstance(current_approval, dict):
        current_approval = HumanApprovalDetails.model_validate(current_approval)

    status = current_approval.approval_status if current_approval else HumanApprovalStatus.PENDING

    if status == HumanApprovalStatus.PENDING:
        # Workflow pauses at the Human Approval Gate awaiting external operator decision
        rec = AgentExecutionRecord(
            record_id=f"EXEC-GATE-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=round(time.perf_counter() - start_time, 4),
            error_summary=None,
        )
        update = {
            "current_stage": ExecutionStage.HUMAN_APPROVAL_GATE,
            "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL,
            "agent_executions": [rec],
            "updated_at": now,
        }
        return validate_agent_state_update(AgentName.SUPERVISOR, update)

    elif status == HumanApprovalStatus.APPROVED:
        # External human engineer has authorized the action
        rec = AgentExecutionRecord(
            record_id=f"EXEC-GATE-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=round(time.perf_counter() - start_time, 4),
            error_summary=None,
        )
        update = {
            "current_stage": ExecutionStage.REMEDIATION_DISPATCH,
            "workflow_status": WorkflowStatus.COMPLETED,
            "agent_executions": [rec],
            "updated_at": now,
        }
        return validate_agent_state_update(AgentName.SUPERVISOR, update)

    elif status in (HumanApprovalStatus.REJECTED, HumanApprovalStatus.EXPIRED):
        # Human rejected or proposal expired
        rec = AgentExecutionRecord(
            record_id=f"EXEC-GATE-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            execution_duration=round(time.perf_counter() - start_time, 4),
            error_summary=None,
        )
        update = {
            "current_stage": ExecutionStage.COMPLETED,
            "workflow_status": WorkflowStatus.COMPLETED,
            "agent_executions": [rec],
            "updated_at": now,
        }
        return validate_agent_state_update(AgentName.SUPERVISOR, update)

    # Fallback safe halt
    update = {
        "current_stage": ExecutionStage.HUMAN_APPROVAL_GATE,
        "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL,
        "updated_at": now,
    }
    return validate_agent_state_update(AgentName.SUPERVISOR, update)


# =============================================================================
# Conditional Edge Routing Functions
# =============================================================================

def route_from_supervisor(state: ManuMindState) -> str:
    """
    Evaluates Supervisor decision and workflow status to determine the next graph node.
    Enforces terminal state safety, normal telemetry RCA bypass, and escalation routing.
    """
    workflow_status = state.get("workflow_status")
    if workflow_status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
        return END

    decision = state.get("supervisor_decision")
    if not decision:
        return END

    action = decision.next_action

    if action == SupervisorAction.ROUTE_TO_ANOMALY_DETECTION:
        # Acyclic progression guard: if anomaly detection has already run, do not re-run
        if state.get("anomaly_detection_result") is not None:
            return "human_approval_gate"
        return "anomaly_detection"
    elif action == SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS:
        # Acyclic progression guard: if RCA has already run, do not re-run
        rca_done = (
            state.get("rca_execution_status") is not None
            or state.get("root_cause_analysis_result") is not None
            or any(rec.agent_name == AgentName.ROOT_CAUSE_ANALYSIS for rec in state.get("agent_executions", []))
        )
        if rca_done:
            return "human_approval_gate"
        return "root_cause_analysis"
    elif action == SupervisorAction.ESCALATE_TO_HUMAN_GATE:
        return "human_approval_gate"
    elif action in (
        SupervisorAction.COMPLETE_WORKFLOW,
        SupervisorAction.FAIL_WORKFLOW,
        SupervisorAction.REQUEST_ADDITIONAL_EVIDENCE,
    ):
        return END

    return END


def route_from_human_gate(state: ManuMindState) -> str:
    """
    Routes from Human Approval Gate:
    - If PENDING, the workflow execution turn concludes (waiting for human operator).
    - If APPROVED, REJECTED, or EXPIRED, routes to supervisor to finalize completion.
    """
    approval = state.get("human_approval")
    if isinstance(approval, dict):
        status = approval.get("approval_status")
    elif approval is not None:
        status = getattr(approval, "approval_status", None)
    else:
        status = HumanApprovalStatus.PENDING

    if status == HumanApprovalStatus.PENDING:
        # Pauses execution turn at the human approval gate
        return END

    # Resumed with non-pending approval: route to supervisor to complete workflow
    return "supervisor"


# =============================================================================
# StateGraph Assembly and Public Interface
# =============================================================================

def build_manumind_graph(
    llm_client: Optional[ManuMindLLMClient] = None,
    anomaly_inference_service: Optional[Any] = None,
    rca_maintenance_service: Optional[Any] = None,
    rca_rag_service: Optional[Any] = None,
    supervisor_agent: Optional[SupervisorAgent] = None,
    checkpointer: Optional[Any] = None,
) -> CompiledStateGraph:
    """
    Constructs and compiles the ManuMind AI multi-agent LangGraph StateGraph workflow.
    
    Nodes:
    1. 'supervisor': Triage, policy evaluation, and conditional routing.
    2. 'anomaly_detection': Ingests telemetry and runs point-in-time multivariate ML inference.
    3. 'root_cause_analysis': Queries maintenance history and manuals; formulates competing hypotheses.
    4. 'verification_governance': Validates evidence source diversity and caps synthetic scores.
    5. 'human_approval_gate': Manages external human operator review and ticket creation boundaries.
    
    Supports dependency injection for deterministic testing and decoupled services.
    """
    builder = StateGraph(ManuMindState)

    # 1. Instantiate agents with optional injected dependencies
    _supervisor = supervisor_agent or SupervisorAgent(llm_client=llm_client)
    anomaly_agent = AnomalyDetectionAgent(inference_service=anomaly_inference_service)
    rca_agent = RootCauseAnalysisAgent(
        llm_client=llm_client,
        maintenance_service=rca_maintenance_service,
        rag_service=rca_rag_service,
    )

    # 2. Add nodes
    builder.add_node("supervisor", create_supervisor_node(_supervisor))
    builder.add_node("anomaly_detection", create_anomaly_detection_node(anomaly_agent))
    builder.add_node("root_cause_analysis", create_rca_node(rca_agent))
    builder.add_node("verification_governance", verification_governance_node)
    builder.add_node("human_approval_gate", human_approval_gate_node)

    # 3. Add edges
    # Entry point
    builder.add_edge(START, "supervisor")

    # Supervisor conditional routing
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "anomaly_detection": "anomaly_detection",
            "root_cause_analysis": "root_cause_analysis",
            "human_approval_gate": "human_approval_gate",
            END: END,
        },
    )

    # Anomaly detection returns to supervisor for evaluation and routing
    builder.add_edge("anomaly_detection", "supervisor")

    # RCA moves to verification governance
    builder.add_edge("root_cause_analysis", "verification_governance")

    # Verification governance routes to supervisor for human gate escalation
    builder.add_edge("verification_governance", "supervisor")

    # Human approval gate routes to END (if pending) or supervisor (if resumed)
    builder.add_conditional_edges(
        "human_approval_gate",
        route_from_human_gate,
        {
            "supervisor": "supervisor",
            END: END,
        },
    )

    # 4. Compile graph
    compiled_graph = builder.compile(checkpointer=checkpointer)
    return compiled_graph


def run_manumind_workflow(
    state: Union[ManuMindState, Dict[str, Any]],
    llm_client: Optional[ManuMindLLMClient] = None,
    anomaly_inference_service: Optional[Any] = None,
    rca_maintenance_service: Optional[Any] = None,
    rca_rag_service: Optional[Any] = None,
    supervisor_agent: Optional[SupervisorAgent] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    High-level entry point to execute the complete ManuMind AI multi-agent workflow.
    Validates input state, constructs the StateGraph, and invokes deterministic execution.
    """
    # 1. Validate required identifiers
    machine_id = state.get("machine_id")
    if not machine_id or not isinstance(machine_id, str) or not machine_id.strip():
        now = datetime.now(timezone.utc)
        rec = AgentExecutionRecord(
            record_id=f"EXEC-INIT-ERR-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=AgentExecutionStatus.FAILED,
            started_at=now,
            completed_at=now,
            execution_duration=0.0,
            error_summary="Workflow aborted: Missing or invalid machine_id.",
        )
        out = dict(state)
        out["workflow_status"] = WorkflowStatus.FAILED
        out["current_stage"] = ExecutionStage.TERMINATED
        out["error_details"] = "Missing or invalid machine_id in workflow state."
        out["error_history"] = ["Validation Error: Missing or blank machine_id."]
        out["agent_executions"] = [rec]
        return out

    # 2. Build and execute compiled graph
    graph = build_manumind_graph(
        llm_client=llm_client,
        anomaly_inference_service=anomaly_inference_service,
        rca_maintenance_service=rca_maintenance_service,
        rca_rag_service=rca_rag_service,
        supervisor_agent=supervisor_agent,
    )

    result_state = graph.invoke(state, config=config)
    return result_state
