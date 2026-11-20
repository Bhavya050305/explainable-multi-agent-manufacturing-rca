"""
ManuMind AI — LangGraph Typed Shared State Architecture
Defines the central shared state schema for multi-agent orchestration,
including LangGraph StateGraph TypedDict channel definitions and
Pydantic V2 validation models enforcing security invariants.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, model_validator, ConfigDict

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
    RCAExecutionStatus,
    VerificationStatus,
    WorkflowStatus,
)
from backend.app.agents.reducers import (
    merge_agent_executions,
    merge_candidate_root_causes,
    merge_errors,
    merge_evidence,
    merge_human_approval,
    merge_rag_citations,
    merge_unique_strings,
    merge_verification_decisions,
    overwrite_supervisor_field,
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


class ManuMindState(TypedDict):
    """
    LangGraph-compatible TypedDict state channel schema.
    Annotated channels use deterministic reducers for multi-agent updates.
    """
    # -------------------------------------------------------------
    # A. Workflow Metadata (Supervisor-Owned)
    # -------------------------------------------------------------
    workflow_id: str
    machine_id: str
    workflow_status: Annotated[WorkflowStatus, overwrite_supervisor_field]
    current_stage: Annotated[ExecutionStage, overwrite_supervisor_field]
    supervisor_decision: Annotated[Optional[SupervisorDecision], overwrite_supervisor_field]
    created_at: datetime
    updated_at: Annotated[datetime, overwrite_supervisor_field]
    execution_mode: ExecutionMode
    error_details: Annotated[Optional[str], overwrite_supervisor_field]
    error_history: Annotated[List[str], merge_errors]

    # -------------------------------------------------------------
    # B. Telemetry and Anomaly Evidence
    # -------------------------------------------------------------
    telemetry_window: Annotated[Optional[TelemetryWindow], overwrite_supervisor_field]
    sensor_measurements: Annotated[Optional[SensorMeasurementsSummary], overwrite_supervisor_field]
    anomaly_detection_result: Annotated[Optional[AnomalyDetectionResult], overwrite_supervisor_field]
    anomaly_type: Annotated[Optional[AnomalyType], overwrite_supervisor_field]
    anomaly_severity: Annotated[Optional[AnomalySeverity], overwrite_supervisor_field]
    affected_sensors: Annotated[List[str], merge_unique_strings]
    detection_timestamp: Annotated[Optional[datetime], overwrite_supervisor_field]
    supporting_evidence_references: Annotated[List[str], merge_unique_strings]
    anomaly_assessment: Annotated[Optional[AnomalyAssessment], overwrite_supervisor_field]

    # -------------------------------------------------------------
    # C. Root Cause Analysis
    # -------------------------------------------------------------
    candidate_root_causes: Annotated[List[CandidateRootCause], merge_candidate_root_causes]
    supporting_evidence: Annotated[List[str], merge_unique_strings]
    contradicting_evidence: Annotated[List[str], merge_unique_strings]
    maintenance_history_references: Annotated[List[str], merge_unique_strings]
    relevant_rag_citation_ids: Annotated[List[str], merge_rag_citations]
    root_cause_hypothesis: Annotated[Optional[str], overwrite_supervisor_field]
    root_cause_verification_status: Annotated[VerificationStatus, overwrite_supervisor_field]
    verification_decisions: Annotated[List[RootCauseVerificationDecision], merge_verification_decisions]
    root_cause_analysis_result: Annotated[Optional[RootCauseAnalysisResult], overwrite_supervisor_field]
    rca_execution_status: Annotated[Optional[RCAExecutionStatus], overwrite_supervisor_field]

    # -------------------------------------------------------------
    # D. Confidence Governance
    # -------------------------------------------------------------
    confidence_governance: Annotated[ConfidenceGovernance, overwrite_supervisor_field]

    # -------------------------------------------------------------
    # E. Explainability and Provenance
    # -------------------------------------------------------------
    evidence_collection: Annotated[List[EvidenceItem], merge_evidence]

    # -------------------------------------------------------------
    # F. Human Approval Governance
    # -------------------------------------------------------------
    human_approval: Annotated[HumanApprovalDetails, merge_human_approval]

    # -------------------------------------------------------------
    # G. Agent Execution Metadata
    # -------------------------------------------------------------
    agent_executions: Annotated[List[AgentExecutionRecord], merge_agent_executions]


class ManuMindStateModel(BaseModel):
    """
    Pydantic V2 validation and serialization model for ManuMindState.
    Enforces cross-field architectural invariants, bounds, and security boundaries.
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Workflow Metadata
    workflow_id: str = Field(min_length=1, description="Unique workflow execution ID")
    machine_id: str = Field(min_length=1, description="Target machine identifier")
    workflow_status: WorkflowStatus = Field(default=WorkflowStatus.INITIALIZED)
    current_stage: ExecutionStage = Field(default=ExecutionStage.INITIAL_TRIAGE)
    supervisor_decision: Optional[SupervisorDecision] = Field(
        default=None, description="Most recent supervisory routing decision"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_mode: ExecutionMode = Field(default=ExecutionMode.HUMAN_IN_THE_LOOP)
    error_details: Optional[str] = Field(default=None)
    error_history: List[str] = Field(default_factory=list)

    # Telemetry and Anomaly Evidence
    telemetry_window: Optional[TelemetryWindow] = Field(default=None)
    sensor_measurements: Optional[SensorMeasurementsSummary] = Field(default=None)
    anomaly_detection_result: Optional[AnomalyDetectionResult] = Field(default=None)
    anomaly_type: Optional[AnomalyType] = Field(default=None)
    anomaly_severity: Optional[AnomalySeverity] = Field(default=None)
    affected_sensors: List[str] = Field(default_factory=list)
    detection_timestamp: Optional[datetime] = Field(default=None)
    supporting_evidence_references: List[str] = Field(default_factory=list)
    anomaly_assessment: Optional[AnomalyAssessment] = Field(
        default=None, description="Structured anomaly assessment produced by Anomaly Detection Agent"
    )

    # Root Cause Analysis
    candidate_root_causes: List[CandidateRootCause] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    maintenance_history_references: List[str] = Field(default_factory=list)
    relevant_rag_citation_ids: List[str] = Field(default_factory=list)
    root_cause_hypothesis: Optional[str] = Field(default=None)
    root_cause_verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    verification_decisions: List[RootCauseVerificationDecision] = Field(
        default_factory=list, description="Authoritative root cause verification decisions"
    )
    root_cause_analysis_result: Optional[RootCauseAnalysisResult] = Field(
        default=None, description="Structured root cause analysis outcome produced by RCA Agent"
    )
    rca_execution_status: Optional[RCAExecutionStatus] = Field(
        default=None, description="Operational execution status of RCA Agent"
    )

    # Confidence Governance
    confidence_governance: ConfidenceGovernance = Field(default_factory=ConfidenceGovernance)

    # Explainability and Provenance
    evidence_collection: List[EvidenceItem] = Field(default_factory=list)

    # Human Approval Governance
    human_approval: HumanApprovalDetails = Field(default_factory=HumanApprovalDetails)

    # Agent Execution Metadata
    agent_executions: List[AgentExecutionRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_security_and_integrity_invariants(self) -> "ManuMindStateModel":
        """
        Enforces Section 5 architectural and security invariants:
        1. No agent can authorize itself.
        2. Root cause cannot be marked VERIFIED without supporting evidence and an authoritative verification decision.
        3. Synthetic evidence indicator cannot be converted to real evidence.
        """
        # Invariant 1: Self-authorization check
        if self.human_approval.approval_status == HumanApprovalStatus.APPROVED:
            approver = (self.human_approval.approved_by or "").strip().upper()
            agent_names = {AgentName.SUPERVISOR.value, AgentName.ANOMALY_DETECTION.value, AgentName.ROOT_CAUSE_ANALYSIS.value}
            if approver in agent_names:
                raise ValueError(
                    f"Security Invariant 1 Violation: Agent '{self.human_approval.approved_by}' cannot self-authorize."
                )

        # Invariant 3: Root cause verification governance
        if self.root_cause_verification_status == VerificationStatus.VERIFIED:
            verified_decisions = [
                d for d in self.verification_decisions if d.verification_status == VerificationStatus.VERIFIED
            ]
            if not verified_decisions:
                raise ValueError(
                    "Security Invariant 3 Violation: root_cause_verification_status cannot be VERIFIED "
                    "without an authoritative RootCauseVerificationDecision with status VERIFIED."
                )

            # Collect all known evidence IDs from evidence_collection, supporting_evidence, and anomaly supporting evidence
            known_evidence_ids = {e.evidence_id for e in self.evidence_collection}
            known_evidence_ids.update(self.supporting_evidence)
            known_evidence_ids.update(self.supporting_evidence_references)

            # Ensure all verified decisions reference candidates that exist (if candidates are populated)
            # and that all verified_evidence_ids exist in state
            known_candidate_ids = {c.cause_id for c in self.candidate_root_causes}

            for vd in verified_decisions:
                if known_candidate_ids and vd.candidate_id not in known_candidate_ids:
                    raise ValueError(
                        f"Security Invariant 3 Violation: Verification decision '{vd.decision_id}' "
                        f"references candidate '{vd.candidate_id}' which does not exist in candidate_root_causes."
                    )
                for ev_id in vd.verified_evidence_ids:
                    if ev_id not in known_evidence_ids:
                        raise ValueError(
                            f"Security Invariant 3 Violation: Verification decision '{vd.decision_id}' "
                            f"references evidence ID '{ev_id}' which is not present in state evidence collection."
                        )

        return self

    def to_dict(self) -> ManuMindState:
        """Export as LangGraph-compatible state dict."""
        return self.model_dump()


def create_initial_state(
    workflow_id: str,
    machine_id: str,
    execution_mode: ExecutionMode = ExecutionMode.HUMAN_IN_THE_LOOP,
    telemetry_window: Optional[TelemetryWindow] = None,
    sensor_measurements: Optional[SensorMeasurementsSummary] = None,
) -> ManuMindState:
    """
    Factory helper to initialize a valid, fully typed ManuMindState instance.
    """
    now = datetime.now(timezone.utc)
    model = ManuMindStateModel(
        workflow_id=workflow_id,
        machine_id=machine_id,
        workflow_status=WorkflowStatus.INITIALIZED,
        current_stage=ExecutionStage.INITIAL_TRIAGE,
        created_at=now,
        updated_at=now,
        execution_mode=execution_mode,
        telemetry_window=telemetry_window,
        sensor_measurements=sensor_measurements,
        confidence_governance=ConfidenceGovernance(),
        human_approval=HumanApprovalDetails(
            requires_human_approval=(execution_mode != ExecutionMode.SIMULATION_TEST),
            approval_status=HumanApprovalStatus.PENDING,
        ),
    )
    return model.to_dict()


def validate_state(state: Union[ManuMindState, Dict[str, Any]]) -> ManuMindStateModel:
    """
    Validates any dictionary or ManuMindState instance against the full Pydantic V2 schema.
    """
    return ManuMindStateModel.model_validate(state)
