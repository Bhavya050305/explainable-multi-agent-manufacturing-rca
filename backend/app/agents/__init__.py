"""
ManuMind AI — Multi-Agent Orchestration Package
Exports typed state models, LangGraph State channels, reducers, and enums.
"""

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
    sanitize_error_message,
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
    anomaly_detection_node,
)
from backend.app.agents.graph import (
    build_manumind_graph,
    human_approval_gate_node,
    run_manumind_workflow,
    verification_governance_node,
)
from backend.app.agents.rca_agent import (
    RootCauseAnalysisAgent,
    root_cause_analysis_node,
)
from backend.app.agents.supervisor import (
    SupervisorAgent,
    supervisor_node,
)

__all__ = [
    # Enums
    "AgentExecutionStatus",
    "AgentName",
    "AnomalyExecutionStatus",
    "AnomalySeverity",
    "AnomalyType",
    "ConfidenceStatus",
    "EvidenceSourceAvailability",
    "EvidenceSourceType",
    "ExecutionMode",
    "ExecutionStage",
    "HumanApprovalStatus",
    "RCAExecutionStatus",
    "RootCauseCategory",
    "SupervisorAction",
    "VerificationAuthority",
    "VerificationMethod",
    "VerificationStatus",
    "WorkflowStatus",
    # LLM Client
    "DeterministicMockLLMClient",
    "ManuMindLLMClient",
    "get_llm_client",
    # Schemas
    "AgentExecutionRecord",
    "AnomalyAssessment",
    "AnomalyDetectionResult",
    "CandidateRootCause",
    "ConfidenceGovernance",
    "EvidenceItem",
    "HumanApprovalDetails",
    "RootCauseAnalysisResult",
    "RootCauseVerificationDecision",
    "SensorMeasurementsSummary",
    "SupervisorDecision",
    "TelemetryWindow",
    # Reducers
    "FORBIDDEN_WORKER_FIELDS",
    "merge_agent_executions",
    "merge_candidate_root_causes",
    "merge_errors",
    "merge_evidence",
    "merge_human_approval",
    "merge_rag_citations",
    "merge_unique_strings",
    "merge_verification_decisions",
    "overwrite_supervisor_field",
    "sanitize_error_message",
    "validate_agent_state_update",
    # State
    "ManuMindState",
    "ManuMindStateModel",
    "create_initial_state",
    "validate_state",
    # Supervisor
    "SupervisorAgent",
    "supervisor_node",
    # Anomaly Agent
    "AnomalyDetectionAgent",
    "MockInferenceService",
    "anomaly_detection_node",
    # Root Cause Analysis Agent
    "RootCauseAnalysisAgent",
    "root_cause_analysis_node",
    # Graph Orchestration
    "build_manumind_graph",
    "human_approval_gate_node",
    "run_manumind_workflow",
    "verification_governance_node",
]
