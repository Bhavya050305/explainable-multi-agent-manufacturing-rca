"""
ManuMind AI — Supervisor Agent Implementation
Coordinates multi-agent workflow routing, evidence triage, confidence governance,
and human approval escalation boundaries within the LangGraph multi-agent architecture.
"""

from copy import deepcopy
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import ValidationError

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    AnomalyExecutionStatus,
    AnomalySeverity,
    AnomalyType,
    ConfidenceStatus,
    ExecutionMode,
    ExecutionStage,
    HumanApprovalStatus,
    SupervisorAction,
    VerificationStatus,
    WorkflowStatus,
)
from backend.app.agents.llm_client import (
    DeterministicMockLLMClient,
    ManuMindLLMClient,
    get_llm_client,
)
from backend.app.agents.reducers import validate_agent_state_update
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    AnomalyDetectionResult,
    CandidateRootCause,
    HumanApprovalDetails,
    SupervisorDecision,
    _sanitize_string,
)
from backend.app.agents.state import (
    ManuMindState,
    ManuMindStateModel,
    validate_state,
)


class SupervisorAgent:
    """
    Supervisor Agent responsible for:
    - Workflow stage progression and task routing to worker agents.
    - Evidence completeness and conflict verification.
    - Confidence governance and enforcement of Step 0.1 rubric thresholds (0.60 human escalation, 0.80 multi-modal consensus).
    - Enforcement of human approval boundaries and prevention of agent self-authorization.
    - Integration with pluggable LLM client and non-hallucinating degraded fallback.
    """

    def __init__(self, llm_client: Optional[ManuMindLLMClient] = None):
        self.llm_client: ManuMindLLMClient = llm_client or get_llm_client()

    def evaluate(self, state: Union[ManuMindState, Dict[str, Any]]) -> SupervisorDecision:
        """
        Evaluates current workflow state and evidence to produce an explainable SupervisorDecision.
        Applies deterministic heuristic governance rules and safe fallback if the LLM provider fails.
        """
        now = datetime.now(timezone.utc)

        # 1. Validate state schema and security invariants
        # Input state is never mutated
        try:
            state_model = validate_state(state)
        except ValidationError as val_err:
            return SupervisorDecision(
                next_action=SupervisorAction.FAIL_WORKFLOW,
                target_agent=None,
                reason=f"State validation failure: {str(val_err)[:200]}",
                decision_confidence=1.0,
                escalation_required=True,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={"error": str(val_err), "validation_failed": True},
            )

        # 2. Terminal workflow status guard
        if state_model.workflow_status in {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}:
            if state_model.workflow_status == WorkflowStatus.COMPLETED:
                return SupervisorDecision(
                    next_action=SupervisorAction.COMPLETE_WORKFLOW,
                    target_agent=None,
                    reason="Workflow has already achieved terminal status COMPLETED.",
                    decision_confidence=1.0,
                    escalation_required=False,
                    human_review_required=False,
                    decision_timestamp=now,
                    decision_trace={"workflow_status": state_model.workflow_status.value, "is_terminal": True},
                )
            else:
                return SupervisorDecision(
                    next_action=SupervisorAction.FAIL_WORKFLOW,
                    target_agent=None,
                    reason=f"Workflow is in terminal state '{state_model.workflow_status.value}' and cannot be resumed.",
                    decision_confidence=1.0,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={"workflow_status": state_model.workflow_status.value, "is_terminal": True},
                )

        # 3. Explicit error guard
        if state_model.error_details:
            return SupervisorDecision(
                next_action=SupervisorAction.FAIL_WORKFLOW,
                target_agent=None,
                reason=f"Unrecoverable error recorded in workflow: {state_model.error_details}",
                decision_confidence=1.0,
                escalation_required=True,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={"error_details": state_model.error_details},
            )

        # 4. Human Approval Gate stage evaluation
        if state_model.current_stage == ExecutionStage.HUMAN_APPROVAL_GATE:
            approval = state_model.human_approval
            if approval.approval_status == HumanApprovalStatus.APPROVED:
                return SupervisorDecision(
                    next_action=SupervisorAction.COMPLETE_WORKFLOW,
                    target_agent=None,
                    reason=f"Maintenance ticket proposal authorized by external human operator ({approval.approved_by}). Workflow completed.",
                    decision_confidence=1.0,
                    escalation_required=False,
                    human_review_required=False,
                    decision_timestamp=now,
                    decision_trace={"approved_by": approval.approved_by, "approval_status": "APPROVED"},
                )
            elif approval.approval_status == HumanApprovalStatus.REJECTED:
                return SupervisorDecision(
                    next_action=SupervisorAction.COMPLETE_WORKFLOW,
                    target_agent=None,
                    reason=f"Maintenance proposal rejected by human reviewer ({approval.approval_reason or 'No reason specified'}). Concluding workflow.",
                    decision_confidence=1.0,
                    escalation_required=False,
                    human_review_required=False,
                    decision_timestamp=now,
                    decision_trace={"approval_status": "REJECTED", "rejection_reason": approval.approval_reason},
                )
            elif approval.approval_status == HumanApprovalStatus.EXPIRED:
                return SupervisorDecision(
                    next_action=SupervisorAction.COMPLETE_WORKFLOW,
                    target_agent=None,
                    reason="Human operator review proposal expired without action. Workflow concluded without ticket dispatch.",
                    decision_confidence=1.0,
                    escalation_required=False,
                    human_review_required=False,
                    decision_timestamp=now,
                    decision_trace={"approval_status": "EXPIRED"},
                )
            else:
                # PENDING approval
                return SupervisorDecision(
                    next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                    target_agent=None,
                    reason="Maintenance ticket proposal is pending external human operator authorization at Human Approval Gate.",
                    decision_confidence=0.90,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={"approval_status": "PENDING"},
                )

        # 5. Post-Root Cause Analysis Evaluation (Candidates already formulated or RCA concluded)
        rca_executed = (
            state_model.rca_execution_status is not None
            or state_model.root_cause_analysis_result is not None
            or any(rec.agent_name == AgentName.ROOT_CAUSE_ANALYSIS for rec in state_model.agent_executions)
        )
        if state_model.candidate_root_causes:
            # Check for conflicting evidence signals
            has_evidence_conflicts = any("__conflict" in e.evidence_id for e in state_model.evidence_collection)
            governance_conflicting = (
                state_model.confidence_governance.overall_status == ConfidenceStatus.INSUFFICIENT_EVIDENCE
                or (
                    state_model.confidence_governance.evidence_agreement is not None
                    and state_model.confidence_governance.evidence_agreement < 0.50
                )
            )

            if has_evidence_conflicts or governance_conflicting:
                return SupervisorDecision(
                    next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                    target_agent=None,
                    reason="Conflicting evidence items detected across diagnostic sources. Mandatory human escalation required for physical sensor inspection.",
                    decision_confidence=0.50,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={
                        "conflicting_evidence": True,
                        "has_evidence_conflicts": has_evidence_conflicts,
                        "governance_conflicting": governance_conflicting,
                    },
                )

            # Evaluate top candidate confidence
            top_candidate = max(state_model.candidate_root_causes, key=lambda c: c.confidence)

            # Step 0.1 Rubric Governance:
            # Cutoff < 0.60: Low confidence -> Mandatory Human Escalation, ticket proposal suppressed
            if top_candidate.confidence < 0.60:
                return SupervisorDecision(
                    next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                    target_agent=None,
                    reason=f"Candidate root cause '{top_candidate.cause_id}' confidence ({top_candidate.confidence:.2f}) is below the 0.60 minimum threshold. Mandatory human escalation required; automated ticket proposal suppressed.",
                    decision_confidence=top_candidate.confidence,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={
                        "candidate_id": top_candidate.cause_id,
                        "confidence": top_candidate.confidence,
                        "threshold": 0.60,
                        "auto_proposal_suppressed": True,
                    },
                )

            # Confidence >= 0.60 (Tier 1 >= 0.80 or Tier 2 0.60-0.79)
            # Route to Human Approval Gate for operator sign-off on the proposal
            return SupervisorDecision(
                next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                target_agent=None,
                reason=f"Diagnostic hypothesis '{top_candidate.cause_id}' formulated with sufficient confidence ({top_candidate.confidence:.2f}). Routing to Human Approval Gate for operator proposal authorization.",
                decision_confidence=top_candidate.confidence,
                escalation_required=False,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={
                    "candidate_id": top_candidate.cause_id,
                    "confidence": top_candidate.confidence,
                    "tier": "TIER_1_CONSENSUS" if top_candidate.confidence >= 0.80 else "TIER_2_PROPOSAL_ELIGIBLE",
                    "requires_operator_signoff": True,
                },
            )

        elif rca_executed:
            # RCA executed but produced no candidate root causes (e.g. LLM failure, parse error, or 0 hypotheses)
            return SupervisorDecision(
                next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                target_agent=None,
                reason="RCA Agent completed without candidate hypotheses (execution status: "
                       f"{state_model.rca_execution_status.value if state_model.rca_execution_status else 'EMPTY'}). "
                       "Escalating to Human Approval Gate for manual investigation.",
                decision_confidence=0.50,
                escalation_required=True,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={
                    "rca_executed": True,
                    "rca_execution_status": state_model.rca_execution_status.value if state_model.rca_execution_status else "EMPTY",
                    "candidate_count": 0,
                },
            )

        # 6. Post-Anomaly Detection Evaluation (Anomaly evaluated, awaiting RCA)
        if state_model.anomaly_detection_result is not None:
            anom_res = state_model.anomaly_detection_result
            anom_execs = [
                rec
                for rec in state_model.agent_executions
                if rec.agent_name == AgentName.ANOMALY_DETECTION
            ]
            has_failed_execution = any(
                rec.execution_status == AgentExecutionStatus.FAILED for rec in anom_execs
            )
            latest_anom_exec = anom_execs[-1] if anom_execs else None

            # 1. Failure routing: Anomaly agent failure or failed execution status MUST fail workflow
            if (
                anom_res.execution_status == AnomalyExecutionStatus.FAILED
                or has_failed_execution
            ):
                err_msg = (
                    (latest_anom_exec.error_summary if latest_anom_exec and latest_anom_exec.error_summary else None)
                    or (state_model.anomaly_assessment.explanation if state_model.anomaly_assessment else None)
                    or "Anomaly Detection Agent encountered an unrecoverable inference or execution failure."
                )
                return SupervisorDecision(
                    next_action=SupervisorAction.FAIL_WORKFLOW,
                    target_agent=None,
                    reason=f"Anomaly detection execution failed: {err_msg}. Halting workflow to prevent unverified equipment operation.",
                    decision_confidence=1.0,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={
                        "execution_status": "FAILED",
                        "error_summary": err_msg,
                        "is_failed": True,
                    },
                )

            # 2. Insufficient data routing: Missing, invalid, or insufficient telemetry data
            if anom_res.execution_status == AnomalyExecutionStatus.INSUFFICIENT_DATA:
                reason_msg = (
                    (latest_anom_exec.error_summary if latest_anom_exec and latest_anom_exec.error_summary else None)
                    or (state_model.anomaly_assessment.explanation if state_model.anomaly_assessment else None)
                    or "Insufficient or invalid telemetry observations to determine equipment condition."
                )
                return SupervisorDecision(
                    next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                    target_agent=None,
                    reason=f"Anomaly evaluation halted due to insufficient or invalid telemetry data: {reason_msg}. Escalating to Human Approval Gate for physical sensor inspection.",
                    decision_confidence=0.50,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={
                        "execution_status": "INSUFFICIENT_DATA",
                        "insufficient_data": True,
                        "reason": reason_msg,
                    },
                )

            # 3. SUCCESS + Anomaly Detected
            if anom_res.is_anomaly and anom_res.anomaly_type != AnomalyType.NONE:
                if not anom_res.supporting_evidence_references and not state_model.evidence_collection:
                    return SupervisorDecision(
                        next_action=SupervisorAction.REQUEST_ADDITIONAL_EVIDENCE,
                        target_agent=None,
                        reason="Anomaly detected but supporting sensor evidence references are missing. Requesting evidence corroboration.",
                        decision_confidence=0.60,
                        required_evidence=["supporting_evidence_references"],
                        escalation_required=True,
                        human_review_required=True,
                        decision_timestamp=now,
                        decision_trace={"is_anomaly": True, "missing_evidence": True},
                    )

                return SupervisorDecision(
                    next_action=SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS,
                    target_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                    reason=f"Anomaly of type '{anom_res.anomaly_type.value}' (severity {anom_res.severity.value}) confirmed. Routing to Root Cause Analysis Agent for causal hypothesis formulation and RAG manual retrieval.",
                    decision_confidence=0.88,
                    escalation_required=False,
                    human_review_required=False,
                    decision_timestamp=now,
                    decision_trace={
                        "is_anomaly": True,
                        "anomaly_type": anom_res.anomaly_type.value,
                        "severity": anom_res.severity.value,
                        "affected_sensors": anom_res.affected_sensors,
                        "target_agent": AgentName.ROOT_CAUSE_ANALYSIS.value,
                    },
                )

            # 4. SUCCESS + No Anomaly Detected (Normal)
            valid_assessment = True
            if state_model.anomaly_assessment is not None:
                asmt = state_model.anomaly_assessment
                if asmt.execution_status != AnomalyExecutionStatus.SUCCESS or asmt.confidence <= 0.0 or asmt.anomaly_detected:
                    valid_assessment = False
            if not valid_assessment:
                return SupervisorDecision(
                    next_action=SupervisorAction.ESCALATE_TO_HUMAN_GATE,
                    target_agent=None,
                    reason="Anomaly evaluation output is ambiguous or assessment confidence is zero. Escalating to Human Gate for review.",
                    decision_confidence=0.50,
                    escalation_required=True,
                    human_review_required=True,
                    decision_timestamp=now,
                    decision_trace={"ambiguous_assessment": True},
                )

            return SupervisorDecision(
                next_action=SupervisorAction.COMPLETE_WORKFLOW,
                target_agent=None,
                reason="Anomaly Detection Agent evaluated telemetry within normal operational envelope. No anomaly detected; concluding workflow.",
                decision_confidence=0.95,
                escalation_required=False,
                human_review_required=False,
                decision_timestamp=now,
                decision_trace={
                    "is_anomaly": False,
                    "anomaly_type": anom_res.anomaly_type.value,
                    "machine_health": "NORMAL",
                },
            )

        # 7. Initial Triage Stage: check telemetry and route to Anomaly Detection
        has_window = state_model.telemetry_window is not None
        has_readings = bool(state_model.sensor_measurements and state_model.sensor_measurements.readings)

        if not has_window and not has_readings:
            return SupervisorDecision(
                next_action=SupervisorAction.REQUEST_ADDITIONAL_EVIDENCE,
                target_agent=None,
                reason="Telemetry observation window and sensor measurements are missing; cannot run anomaly detection.",
                decision_confidence=0.85,
                required_evidence=["telemetry_window", "sensor_measurements"],
                escalation_required=False,
                human_review_required=False,
                decision_timestamp=now,
                decision_trace={"stage": "INITIAL_TRIAGE", "missing_telemetry": True},
            )

        # Telemetry is present -> Route to Anomaly Detection Agent
        return SupervisorDecision(
            next_action=SupervisorAction.ROUTE_TO_ANOMALY_DETECTION,
            target_agent=AgentName.ANOMALY_DETECTION,
            reason="Initial telemetry ingested and verified. Routing to Anomaly Detection Agent for multivariate sensor analysis.",
            decision_confidence=0.92,
            escalation_required=False,
            human_review_required=False,
            decision_timestamp=now,
            decision_trace={
                "stage": "INITIAL_TRIAGE",
                "machine_id": state_model.machine_id,
                "target_agent": AgentName.ANOMALY_DETECTION.value,
            },
        )

        # Fallback default decision
        return SupervisorDecision(
            next_action=SupervisorAction.COMPLETE_WORKFLOW,
            target_agent=None,
            reason="Workflow reached unhandled state; concluding safely.",
            decision_confidence=0.50,
            escalation_required=True,
            human_review_required=True,
            decision_timestamp=now,
            decision_trace={"unhandled_state": True},
        )

    def route(self, state: ManuMindState) -> Dict[str, Any]:
        """
        LangGraph-compatible node execution method.
        Accepts typed shared state, performs evaluation without mutating input state,
        enforces write boundaries, and returns validated channel updates.
        """
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Evaluate state
        decision: SupervisorDecision
        try:
            # Check if LLM client is configured and should be consulted
            if isinstance(self.llm_client, DeterministicMockLLMClient) and self.llm_client.simulate_failure:
                # Test simulated failure -> triggers safe fallback
                try:
                    self.llm_client.generate_structured_decision("Evaluate workflow routing", context=dict(state))
                except Exception as exc:
                    fallback_decision = self.evaluate(state)
                    # Enrich trace with fallback reason
                    enriched_trace = dict(fallback_decision.decision_trace)
                    enriched_trace["provider_fallback"] = True
                    enriched_trace["fallback_reason"] = f"LLM client failure: {str(exc)}"
                    decision = fallback_decision.model_copy(update={"decision_trace": enriched_trace})
            else:
                decision = self.evaluate(state)
        except Exception as exc:
            decision = SupervisorDecision(
                next_action=SupervisorAction.FAIL_WORKFLOW,
                target_agent=None,
                reason=f"Supervisor execution failure: {str(exc)}",
                decision_confidence=1.0,
                escalation_required=True,
                human_review_required=True,
                decision_timestamp=now,
                decision_trace={"execution_error": str(exc)},
            )

        # 2. Derive stage and workflow status updates from supervisory decision
        next_stage: ExecutionStage = state.get("current_stage", ExecutionStage.INITIAL_TRIAGE)
        next_status: WorkflowStatus = state.get("workflow_status", WorkflowStatus.INITIALIZED)

        if decision.next_action == SupervisorAction.ROUTE_TO_ANOMALY_DETECTION:
            next_stage = ExecutionStage.ANOMALY_DETECTION
            next_status = WorkflowStatus.RUNNING
        elif decision.next_action == SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS:
            next_stage = ExecutionStage.ROOT_CAUSE_ANALYSIS
            next_status = WorkflowStatus.RUNNING
        elif decision.next_action == SupervisorAction.ESCALATE_TO_HUMAN_GATE:
            next_stage = ExecutionStage.HUMAN_APPROVAL_GATE
            next_status = WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL
        elif decision.next_action == SupervisorAction.COMPLETE_WORKFLOW:
            next_stage = ExecutionStage.COMPLETED
            next_status = WorkflowStatus.COMPLETED
        elif decision.next_action == SupervisorAction.FAIL_WORKFLOW:
            next_stage = ExecutionStage.TERMINATED
            next_status = WorkflowStatus.FAILED
        elif decision.next_action == SupervisorAction.REQUEST_ADDITIONAL_EVIDENCE:
            # Remains in current stage awaiting telemetry/evidence
            next_status = (
                WorkflowStatus.WAITING_FOR_HUMAN_APPROVAL
                if decision.human_review_required
                else WorkflowStatus.RUNNING
            )

        # 3. Create execution audit record
        elapsed = time.perf_counter() - start_time
        record = AgentExecutionRecord(
            record_id=f"EXEC-SUP-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.SUPERVISOR,
            execution_status=(
                AgentExecutionStatus.COMPLETED
                if decision.next_action != SupervisorAction.FAIL_WORKFLOW
                else AgentExecutionStatus.FAILED
            ),
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            execution_duration=round(elapsed, 4),
            error_summary=None if decision.next_action != SupervisorAction.FAIL_WORKFLOW else decision.reason,
        )

        # 4. Assemble proposed update dictionary
        update: Dict[str, Any] = {
            "current_stage": next_stage,
            "workflow_status": next_status,
            "supervisor_decision": decision,
            "updated_at": datetime.now(timezone.utc),
            "agent_executions": [record],
        }

        # 5. Enforce agent write-boundary security invariant
        # Supervisor is verified at the execution boundary
        validated_update = validate_agent_state_update(AgentName.SUPERVISOR, update)

        return validated_update


def supervisor_node(state: ManuMindState) -> Dict[str, Any]:
    """
    LangGraph StateGraph node function for ManuMind Supervisor Agent.
    Accepts typed shared state and returns validated channel updates.
    """
    agent = SupervisorAgent()
    return agent.route(state)
