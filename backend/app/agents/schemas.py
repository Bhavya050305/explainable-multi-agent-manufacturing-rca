"""
ManuMind AI — Multi-Agent Typed State Sub-Schemas
Pydantic V2 data models for telemetry evidence, root cause hypotheses,
confidence governance, explainability provenance, human approval gates,
and agent execution records.
"""

from datetime import datetime, timezone
import math
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from backend.app.agents.enums import (
    AgentName,
    AgentExecutionStatus,
    AnomalyExecutionStatus,
    AnomalySeverity,
    AnomalyType,
    ConfidenceStatus,
    EvidenceSourceAvailability,
    EvidenceSourceType,
    HumanApprovalStatus,
    RCAExecutionStatus,
    RootCauseCategory,
    SupervisorAction,
    VerificationAuthority,
    VerificationMethod,
    VerificationStatus,
)


def _sanitize_string(val: Optional[str]) -> Optional[str]:
    """Sanitize secrets, passwords, or connection URIs from string fields."""
    if not val:
        return val
    # Mask database passwords in connection URLs
    sanitized = re.sub(r":([^/@:]+)@", ":********@", val)
    # Mask Bearer or API tokens
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", r"\1********", sanitized)
    # Mask common JWT or Supabase key patterns
    sanitized = re.sub(r"(eyJ[A-Za-z0-9_\-\.]{20,})", "********", sanitized)
    return sanitized


class TelemetryWindow(BaseModel):
    """Temporal window of machine sensor readings evaluated during analysis."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    start_time: datetime = Field(description="Start timestamp of the telemetry observation window")
    end_time: datetime = Field(description="End timestamp of the telemetry observation window")
    sample_count: int = Field(ge=0, description="Total number of telemetry samples in window")
    sampling_interval_seconds: Optional[float] = Field(
        default=None, gt=0, description="Nominal interval between consecutive samples in seconds"
    )

    @model_validator(mode="after")
    def validate_window_bounds(self) -> "TelemetryWindow":
        if self.start_time > self.end_time:
            raise ValueError(f"start_time ({self.start_time}) cannot be later than end_time ({self.end_time})")
        return self


class SensorMeasurementsSummary(BaseModel):
    """Snapshot or aggregate summary of key machine sensors."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    readings: Dict[str, float] = Field(default_factory=dict, description="Sensor metric readings (e.g., vibration, temperature)")
    units: Dict[str, str] = Field(default_factory=dict, description="Measurement units per sensor")
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp")
    is_synthetic: bool = Field(default=False, description="Flag indicating synthetic/simulated readings")


class AnomalyDetectionResult(BaseModel):
    """Structured output produced by the Anomaly Detection Agent."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_anomaly: bool = Field(description="Whether telemetry indicates anomalous behavior")
    execution_status: AnomalyExecutionStatus = Field(
        default=AnomalyExecutionStatus.SUCCESS,
        description="Operational execution status: SUCCESS, FAILED, or INSUFFICIENT_DATA"
    )
    anomaly_type: AnomalyType = Field(default=AnomalyType.NONE, description="Classified anomaly taxonomy type")
    severity: AnomalySeverity = Field(default=AnomalySeverity.INFO, description="Severity ranking of anomaly")
    affected_sensors: List[str] = Field(default_factory=list, description="List of sensors demonstrating anomalous readings")
    detection_timestamp: Optional[datetime] = Field(default=None, description="Timestamp when anomaly was detected")
    supporting_evidence_references: List[str] = Field(default_factory=list, description="IDs of supporting evidence items")
    raw_model_scores: Dict[str, float] = Field(default_factory=dict, description="Raw model or reconstruction error scores")


class EvidenceItem(BaseModel):
    """
    Atomic evidence item tracking provenance, source agent, and citation references.
    External text is marked as untrusted data.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1, description="Unique identifier for the evidence item")
    source_type: EvidenceSourceType = Field(description="Provenance category of evidence source")
    source_reference: str = Field(min_length=1, description="Pointer to source document, sensor channel, or record")
    description: str = Field(min_length=1, description="Observational description of the evidence")
    observed_at: datetime = Field(description="Timestamp when evidence was observed or recorded")
    source_agent: AgentName = Field(description="Agent responsible for discovering or asserting this evidence")
    synthetic_data_indicator: bool = Field(
        default=False, description="Explicit indicator if evidence is synthetic or placeholder"
    )
    citation_ids: List[str] = Field(
        default_factory=list, description="RAG citation identifiers, e.g. ['[CIT-1]']"
    )
    relevance_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Bounded relevance score [0.0, 1.0]"
    )
    relevance_explanation: Optional[str] = Field(
        default=None, description="Rationale for evidence relevance to the diagnosis"
    )

    @field_validator("description", "source_reference", "relevance_explanation")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_string(v)

    @field_validator("citation_ids")
    @classmethod
    def validate_citation_format(cls, citations: List[str]) -> List[str]:
        """Ensure RAG citation identifiers adhere to standardized bracketed format [CIT-X]."""
        validated = []
        for cit in citations:
            cit_clean = cit.strip()
            if not cit_clean:
                continue
            validated.append(cit_clean)
        return validated


class CandidateRootCause(BaseModel):
    """
    Candidate root cause hypothesis generated by Root Cause Analysis Agent.
    Maintains a strict distinction between an initial hypothesis and a verified cause.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    cause_id: str = Field(min_length=1, description="Unique candidate root cause identifier")
    description: str = Field(min_length=1, description="Detailed description of proposed mechanical failure")
    hypothesis: str = Field(min_length=1, description="Diagnostic hypothesis explaining observed telemetry")
    confidence: float = Field(ge=0.0, le=1.0, description="Bounded confidence score in [0.0, 1.0]")
    confidence_category: ConfidenceStatus = Field(
        default=ConfidenceStatus.UNCALIBRATED, description="Categorical confidence status"
    )
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="List of supporting evidence IDs")
    contradicting_evidence_ids: List[str] = Field(default_factory=list, description="List of contradicting evidence IDs")
    maintenance_history_references: List[str] = Field(default_factory=list, description="Historical work order references")
    citation_ids: List[str] = Field(default_factory=list, description="Preserved RAG citation identifiers")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED, description="Current verification lifecycle status"
    )
    proposed_by_agent: AgentName = Field(
        default=AgentName.ROOT_CAUSE_ANALYSIS, description="Agent proposing this hypothesis"
    )
    category: Optional[RootCauseCategory] = Field(
        default=None, description="Diagnostic failure taxonomy category"
    )
    subsystem: Optional[str] = Field(
        default=None, description="Candidate affected machine subsystem"
    )
    identified_at: datetime = Field(description="Timestamp when root cause was formulated")

    @field_validator("description", "hypothesis", "subsystem")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_string(v) if v is not None else None

    @model_validator(mode="after")
    def validate_candidate_integrity(self) -> "CandidateRootCause":
        """
        Phase 5 Step 2.2 Security Invariant:
        Candidate root causes formulated by worker agents or parsed from LLM completions
        represent diagnostic hypotheses and CANNOT directly self-assert VERIFIED status.
        Authoritative verification requires a distinct RootCauseVerificationDecision.
        """
        if self.verification_status == VerificationStatus.VERIFIED:
            raise ValueError(
                f"Security Invariant Violation: Candidate root cause '{self.cause_id}' cannot be directly "
                f"instantiated with verification_status=VERIFIED. Candidates represent unverified hypotheses "
                f"(permit UNVERIFIED or HYPOTHESIS_PENDING). Verification requires an authoritative "
                f"RootCauseVerificationDecision from the Supervisor corroboration engine."
            )
        return self


class RootCauseVerificationDecision(BaseModel):
    """
    Authoritative decision verifying or refuting a candidate root cause hypothesis.
    Enforces multi-source evidence corroboration and strict provenance boundaries.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(min_length=1, description="Unique identifier for this verification decision")
    candidate_id: str = Field(min_length=1, description="ID of the CandidateRootCause being evaluated")
    verification_status: VerificationStatus = Field(description="Decision outcome (VERIFIED, REFUTED, or INSUFFICIENT_DATA)")
    verified_evidence_ids: List[str] = Field(default_factory=list, description="IDs of corroborating evidence items")
    corroboration_score: float = Field(ge=0.0, le=1.0, description="Corroboration score [0.0, 1.0] from rubric")
    source_diversity_count: int = Field(ge=0, description="Count of distinct evidence source types corroborating")
    verified_by: str = Field(min_length=1, description="Authorized verification component identity")
    verification_method: VerificationMethod = Field(description="Corroboration method from rubric")
    verification_rationale: str = Field(min_length=1, description="Technical rationale supporting the verification decision")
    rubric_version: str = Field(default="STEP_0_1_TIERED_RUBRIC_v1", description="Corroboration rubric specification version")
    verified_at: datetime = Field(description="Timestamp when verification decision was rendered")

    @field_validator("decision_id", "candidate_id", "verified_by", "verification_rationale", "rubric_version")
    @classmethod
    def sanitize_decision_text(cls, v: str) -> str:
        return _sanitize_string(v) or ""

    @model_validator(mode="after")
    def validate_decision_integrity(self) -> "RootCauseVerificationDecision":
        """
        Enforces verification decision integrity:
        1. Worker agents (ANOMALY_DETECTION, ROOT_CAUSE_ANALYSIS) cannot render verification decisions.
        2. VERIFIED outcome requires non-empty verified_evidence_ids.
        3. VERIFIED outcome requires corroboration_score >= 0.60 (Step 0.1 rubric threshold).
        4. VERIFIED outcome requires source_diversity_count >= 2 for multi-source corroboration.
        """
        worker_agents = {AgentName.ANOMALY_DETECTION.value, AgentName.ROOT_CAUSE_ANALYSIS.value}
        if self.verified_by.strip().upper() in worker_agents:
            raise ValueError(
                f"Security Invariant Violation: Worker agent '{self.verified_by}' cannot render "
                f"an authoritative verification decision. Only Supervisor or authorized human may verify."
            )

        if self.verification_status == VerificationStatus.VERIFIED:
            if not self.verified_evidence_ids:
                raise ValueError(
                    f"Verification Decision Violation: Decision '{self.decision_id}' marked as VERIFIED "
                    f"without any verified supporting evidence IDs."
                )
            if self.corroboration_score < 0.60:
                raise ValueError(
                    f"Verification Decision Violation: Corroboration score ({self.corroboration_score}) "
                    f"is below the minimum corroboration threshold (0.60) required for VERIFIED status."
                )
            if self.source_diversity_count < 2:
                raise ValueError(
                    f"Verification Decision Violation: Source diversity count ({self.source_diversity_count}) "
                    f"is below minimum (>= 2 distinct evidence source types) required for multi-modal verification."
                )

        return self


class RootCauseAnalysisResult(BaseModel):
    """
    Structured diagnostic outcome produced by the Root Cause Analysis (RCA) Agent.
    Enforces multi-hypothesis formulation, multi-source evidence corroboration,
    transparent source availability, and strict separation from verification decisions.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    machine_id: str = Field(min_length=1, description="Target machine identifier")
    execution_status: RCAExecutionStatus = Field(description="Operational RCA execution status")
    anomaly_reference: Optional[str] = Field(default=None, description="Reference ID or summary of the anomaly investigated")
    anomaly_type: AnomalyType = Field(default=AnomalyType.NONE, description="Investigated anomaly taxonomy type")
    hypotheses: List[CandidateRootCause] = Field(default_factory=list, description="Ranked candidate root cause hypotheses")
    primary_hypothesis_id: Optional[str] = Field(default=None, description="ID of the best-supported hypothesis")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="All supporting evidence IDs across hypotheses")
    contradicting_evidence_ids: List[str] = Field(default_factory=list, description="All contradicting evidence IDs across hypotheses")
    rag_citations: List[str] = Field(default_factory=list, description="Preserved RAG citation IDs e.g. ['[CIT-1]']")
    maintenance_history_findings: List[str] = Field(default_factory=list, description="Summarized maintenance history findings")
    evidence_source_availability: Dict[str, EvidenceSourceAvailability] = Field(
        default_factory=dict, description="Availability status per evidence source"
    )
    corroboration_summary: str = Field(description="Summary of multi-source corroboration")
    uncertainty_and_limitations: str = Field(description="Honest statement of uncertainty and limitations")
    recommended_diagnostic_actions: List[str] = Field(default_factory=list, description="Recommended physical checks")
    human_review_recommended: bool = Field(default=True, description="Whether human review is recommended")
    is_synthetic: bool = Field(default=False, description="Whether synthetic evidence was involved")
    analysis_timestamp: datetime = Field(description="Timestamp when analysis was concluded")

    @field_validator("machine_id", "corroboration_summary", "uncertainty_and_limitations")
    @classmethod
    def sanitize_result_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_string(v) if v is not None else None


class ConfidenceGovernance(BaseModel):
    """
    Multi-dimensional confidence governance model.
    Maintains distinct orthogonal confidence dimensions without naive averaging.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    anomaly_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence of anomaly detection [0.0, 1.0]"
    )
    root_cause_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence of root cause diagnosis [0.0, 1.0]"
    )
    evidence_completeness: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Completeness of supporting evidence [0.0, 1.0]"
    )
    evidence_agreement: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Consensus degree across evidence sources [0.0, 1.0]"
    )
    overall_status: ConfidenceStatus = Field(
        default=ConfidenceStatus.UNCALIBRATED, description="Categorical governance status"
    )
    calibration_notice: str = Field(
        default="Confidence values are dimensional bounded metrics and not automatically calibrated probabilities.",
        description="Mandatory methodological governance disclosure"
    )


class HumanApprovalDetails(BaseModel):
    """
    Human approval governance details.
    Enforces security invariant that agents cannot self-authorize ticket creation.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    requires_human_approval: bool = Field(
        default=True, description="Whether human approval is required for maintenance action"
    )
    approval_status: HumanApprovalStatus = Field(
        default=HumanApprovalStatus.PENDING, description="Current governance approval status"
    )
    approval_reference: Optional[str] = Field(
        default=None, description="External human approval proposal token or reference ID"
    )
    approval_reason: Optional[str] = Field(
        default=None, description="Human reviewer justification for approval or rejection"
    )
    approval_timestamp: Optional[datetime] = Field(
        default=None, description="Timestamp when human approval or rejection was recorded"
    )
    approved_by: Optional[str] = Field(
        default=None, description="Authorized human operator identifier. Strictly cannot be an AI agent."
    )

    @field_validator("approval_reason", "approval_reference")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_string(v)

    def validate_transition_to(self, new_status: HumanApprovalStatus) -> None:
        """
        Enforces valid human approval lifecycle transitions:
        - PENDING -> APPROVED
        - PENDING -> REJECTED
        - PENDING -> EXPIRED
        - Terminal states (APPROVED, REJECTED, EXPIRED) cannot transition.
        - REJECTED -> APPROVED is strictly rejected.
        - EXPIRED -> APPROVED is strictly rejected.
        """
        curr_val = self.approval_status.value if hasattr(self.approval_status, "value") else str(self.approval_status)
        new_val = new_status.value if hasattr(new_status, "value") else str(new_status)
        terminal_states = {HumanApprovalStatus.APPROVED, HumanApprovalStatus.REJECTED, HumanApprovalStatus.EXPIRED}
        if self.approval_status in terminal_states:
            if new_status != self.approval_status:
                raise ValueError(
                    f"Invalid approval transition: Cannot transition from terminal state "
                    f"'{curr_val}' to '{new_val}'."
                )
        if self.approval_status == HumanApprovalStatus.PENDING:
            if new_status not in {
                HumanApprovalStatus.APPROVED,
                HumanApprovalStatus.REJECTED,
                HumanApprovalStatus.EXPIRED,
                HumanApprovalStatus.PENDING,
            }:
                raise ValueError(
                    f"Invalid approval transition: Cannot transition from PENDING to '{new_val}'."
                )
        if self.approval_status == HumanApprovalStatus.NOT_REQUIRED:
            if new_status != HumanApprovalStatus.NOT_REQUIRED:
                raise ValueError(
                    f"Invalid approval transition: Cannot transition from NOT_REQUIRED to '{new_val}'."
                )

    @model_validator(mode="after")
    def validate_approval_boundary(self) -> "HumanApprovalDetails":
        """
        Security Invariant 1: No agent can authorize itself.
        If approval_status is APPROVED, approved_by must be specified and must NOT be an AI agent.
        """
        if self.approval_status == HumanApprovalStatus.APPROVED:
            if not self.approved_by or not self.approved_by.strip():
                raise ValueError(
                    "Security Invariant 1 Violation: approval_status is APPROVED but approved_by is missing."
                )
            # Ensure approved_by is not an AI agent role
            agent_names = {AgentName.SUPERVISOR.value, AgentName.ANOMALY_DETECTION.value, AgentName.ROOT_CAUSE_ANALYSIS.value}
            if self.approved_by.strip().upper() in agent_names:
                raise ValueError(
                    f"Security Invariant 1 Violation: Agent '{self.approved_by}' attempted self-authorization. "
                    f"Only external human operators may approve ticket creation."
                )
        if self.approval_status == HumanApprovalStatus.NOT_REQUIRED:
            if self.requires_human_approval:
                raise ValueError(
                    "Approval Consistency Violation: approval_status is NOT_REQUIRED but requires_human_approval is True."
                )
        return self


class AgentExecutionRecord(BaseModel):
    """Audit log entry capturing individual agent execution lifecycle."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str = Field(min_length=1, description="Unique execution record identifier")
    agent_name: AgentName = Field(description="Name of the executing agent")
    execution_status: AgentExecutionStatus = Field(
        default=AgentExecutionStatus.PENDING, description="Agent execution lifecycle status"
    )
    started_at: datetime = Field(description="Timestamp when agent execution started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when agent execution finished")
    execution_duration: Optional[float] = Field(
        default=None, ge=0.0, description="Execution duration in seconds"
    )
    error_summary: Optional[str] = Field(
        default=None, description="Sanitized error summary if execution failed"
    )
    evidence_references: List[str] = Field(
        default_factory=list, description="IDs of evidence generated during this execution"
    )

    @field_validator("error_summary")
    @classmethod
    def sanitize_error(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_string(v)

    @model_validator(mode="after")
    def validate_duration_consistency(self) -> "AgentExecutionRecord":
        if self.completed_at and self.started_at:
            if self.completed_at < self.started_at:
                raise ValueError("completed_at cannot be earlier than started_at")
        return self


class SupervisorDecision(BaseModel):
    """
    Structured, explainable routing and governance decision generated by the Supervisor Agent.
    Enforces validation across conflicting or incompatible operational parameters.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    next_action: SupervisorAction = Field(description="Selected next action by supervisor")
    target_agent: Optional[AgentName] = Field(default=None, description="Target agent for execution, if applicable")
    reason: str = Field(min_length=1, description="Explainable technical justification for the decision")
    decision_confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this supervisory routing decision [0.0, 1.0]")
    required_evidence: List[str] = Field(default_factory=list, description="IDs or categories of additional required evidence")
    escalation_required: bool = Field(default=False, description="Whether escalation is required due to low confidence, conflict, or risk")
    human_review_required: bool = Field(default=False, description="Whether human review at human approval gate is required")
    decision_timestamp: datetime = Field(description="Timestamp when supervisor decision was generated")
    decision_trace: Dict[str, Any] = Field(default_factory=dict, description="Metadata trace capturing the factors influencing this decision")

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, v: str) -> str:
        return _sanitize_string(v) or ""

    @model_validator(mode="after")
    def validate_decision_invariants(self) -> "SupervisorDecision":
        """
        Enforces Section 3 and Section 4 supervisory invariants:
        1. Terminal workflow cannot route to a worker agent.
        2. A human-review decision must not claim that human approval has already occurred.
        3. Missing evidence must not be represented as successful verification.
        4. A failed workflow must not be silently marked successful.
        5. Action and target agent consistency.
        """
        worker_agents = {AgentName.ANOMALY_DETECTION, AgentName.ROOT_CAUSE_ANALYSIS}

        # Invariant 1: Terminal workflow cannot route to a worker agent
        if self.next_action in {SupervisorAction.COMPLETE_WORKFLOW, SupervisorAction.FAIL_WORKFLOW}:
            if self.target_agent in worker_agents:
                raise ValueError(
                    f"Supervisory Invariant Violation: Terminal action '{self.next_action.value}' "
                    f"cannot route to worker agent '{self.target_agent.value}'."
                )

        # Invariant 2: Action and target_agent consistency
        if self.next_action == SupervisorAction.ROUTE_TO_ANOMALY_DETECTION:
            if self.target_agent != AgentName.ANOMALY_DETECTION:
                raise ValueError(
                    f"Supervisory Invariant Violation: Action '{self.next_action.value}' "
                    f"requires target_agent=ANOMALY_DETECTION."
                )
        elif self.next_action == SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS:
            if self.target_agent != AgentName.ROOT_CAUSE_ANALYSIS:
                raise ValueError(
                    f"Supervisory Invariant Violation: Action '{self.next_action.value}' "
                    f"requires target_agent=ROOT_CAUSE_ANALYSIS."
                )
        elif self.next_action in {
            SupervisorAction.ESCALATE_TO_HUMAN_GATE,
            SupervisorAction.REQUEST_ADDITIONAL_EVIDENCE,
            SupervisorAction.COMPLETE_WORKFLOW,
            SupervisorAction.FAIL_WORKFLOW
        }:
            if self.target_agent in worker_agents:
                raise ValueError(
                    f"Supervisory Invariant Violation: Action '{self.next_action.value}' "
                    f"cannot have worker target_agent '{self.target_agent.value}'."
                )

        # Invariant 3: Human review decision must not claim approval has occurred
        if self.human_review_required or self.next_action == SupervisorAction.ESCALATE_TO_HUMAN_GATE:
            if self.decision_trace.get("approval_status") == "APPROVED" or self.decision_trace.get("human_approved") is True:
                raise ValueError(
                    "Security Invariant Violation: A decision requiring human review cannot claim "
                    "that human approval has already occurred."
                )

        # Invariant 4: Missing evidence must not be represented as verified
        if self.required_evidence and (self.decision_trace.get("verification_status") == "VERIFIED" or self.decision_trace.get("is_verified") is True):
            raise ValueError(
                "Supervisory Invariant Violation: Decision requiring additional evidence cannot "
                "represent root cause as verified."
            )

        # Invariant 5: Failed workflow cannot be silently marked successful
        if self.next_action == SupervisorAction.COMPLETE_WORKFLOW:
            if self.decision_trace.get("workflow_status") == "FAILED" or self.decision_trace.get("is_failed") is True:
                raise ValueError(
                    "Supervisory Invariant Violation: Cannot complete workflow when trace indicates failure."
                )

        # Invariant 6: Escalation consistency
        if self.next_action == SupervisorAction.ESCALATE_TO_HUMAN_GATE:
            if not self.human_review_required:
                raise ValueError(
                    "Supervisory Invariant Violation: ESCALATE_TO_HUMAN_GATE action requires human_review_required=True."
                )

        return self


class AnomalyAssessment(BaseModel):
    """
    Structured, explainable anomaly assessment produced by Anomaly Detection Agent.
    Contains model inference findings, sensor attribution, expected baseline envelopes,
    and evidence provenance without asserting causal root causes.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    machine_id: str = Field(min_length=1, description="Machine identifier (e.g. M104)")
    anomaly_detected: bool = Field(description="Whether telemetry indicates anomalous behavior")
    execution_status: AnomalyExecutionStatus = Field(
        default=AnomalyExecutionStatus.SUCCESS,
        description="Operational execution status: SUCCESS, FAILED, or INSUFFICIENT_DATA"
    )
    anomaly_type: AnomalyType = Field(default=AnomalyType.NONE, description="Classified anomaly taxonomy type")
    severity: AnomalySeverity = Field(default=AnomalySeverity.INFO, description="Severity ranking of detected anomaly")
    confidence: float = Field(ge=0.0, le=1.0, description="Inference model confidence score [0.0, 1.0]")
    affected_sensors: List[str] = Field(default_factory=list, description="List of sensors demonstrating anomalous readings")
    observed_values: Dict[str, float] = Field(default_factory=dict, description="Observed sensor readings at point or sequence of anomaly")
    expected_ranges: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Normal baseline envelope [min, max] per sensor")
    evidence_ids: List[str] = Field(default_factory=list, description="Generated evidence IDs supporting this assessment")
    model_name: str = Field(min_length=1, description="Name of the inference model(s) evaluated")
    model_version: str = Field(default="v1.0.0", description="Version of the inference model pipeline")
    inference_timestamp: datetime = Field(description="Timestamp when inference evaluation was completed")
    explanation: str = Field(min_length=1, description="Analytical explanation of why the anomaly was flagged")
    limitations: str = Field(
        default="Model detection indicates statistical/reconstruction divergence, not confirmed equipment failure or physical root cause.",
        description="Epistemic disclaimer distinguishing detection from causation"
    )
    telemetry_window: Optional[TelemetryWindow] = Field(default=None, description="Observation window evaluated")
    is_synthetic: bool = Field(default=False, description="Flag indicating synthetic/simulated telemetry provenance")
    raw_scores: Dict[str, float] = Field(default_factory=dict, description="Raw model or reconstruction error scores")
    attribution_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed feature or MSE attribution metrics")

    @field_validator("explanation", "limitations")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return _sanitize_string(v) or ""

    @field_validator("confidence")
    @classmethod
    def validate_finite_confidence(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Confidence must be a finite float (NaN and Inf are rejected).")
        return v

    @field_validator("observed_values")
    @classmethod
    def validate_finite_observed(cls, v: Dict[str, float]) -> Dict[str, float]:
        for k, val in v.items():
            if not math.isfinite(val):
                raise ValueError(f"Observed value for sensor '{k}' must be finite (NaN and Inf are rejected).")
        return v

    @field_validator("expected_ranges")
    @classmethod
    def validate_finite_ranges(cls, v: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        for k, rng in v.items():
            for bound_key, bound_val in rng.items():
                if not math.isfinite(bound_val):
                    raise ValueError(f"Expected range '{bound_key}' for sensor '{k}' must be finite (NaN and Inf are rejected).")
        return v

    @model_validator(mode="after")
    def validate_assessment_invariants(self) -> "AnomalyAssessment":
        if not self.machine_id or not self.machine_id.strip():
            raise ValueError("machine_id cannot be empty or blank.")
        if self.execution_status == AnomalyExecutionStatus.SUCCESS:
            if not self.anomaly_detected and self.anomaly_type != AnomalyType.NONE:
                raise ValueError("When anomaly_detected is False, anomaly_type must be NONE.")
            if self.anomaly_detected and self.anomaly_type == AnomalyType.NONE:
                raise ValueError("When anomaly_detected is True, anomaly_type cannot be NONE.")
        elif self.execution_status in {AnomalyExecutionStatus.FAILED, AnomalyExecutionStatus.INSUFFICIENT_DATA}:
            if self.anomaly_detected:
                raise ValueError(
                    f"Invariant Violation: Assessment with execution_status={self.execution_status.value} "
                    f"cannot assert anomaly_detected=True."
                )
            if self.anomaly_type != AnomalyType.NONE:
                raise ValueError(
                    f"Invariant Violation: Assessment with execution_status={self.execution_status.value} "
                    f"must have anomaly_type=NONE."
                )
        return self
