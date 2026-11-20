"""
ManuMind AI — Multi-Agent Orchestration Enums
Defines typed enumerations for workflow lifecycle, agent identification,
evidence classification, confidence governance, and human approval gates.
"""

from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    WAITING_FOR_HUMAN_APPROVAL = "WAITING_FOR_HUMAN_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionStage(str, Enum):
    """Current active stage of the multi-agent workflow."""
    INITIAL_TRIAGE = "INITIAL_TRIAGE"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    HUMAN_APPROVAL_GATE = "HUMAN_APPROVAL_GATE"
    REMEDIATION_DISPATCH = "REMEDIATION_DISPATCH"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class ExecutionMode(str, Enum):
    """Operational execution mode for the workflow."""
    AUTONOMOUS_DIAGNOSTIC = "AUTONOMOUS_DIAGNOSTIC"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"
    SIMULATION_TEST = "SIMULATION_TEST"


class AgentName(str, Enum):
    """Identifier for multi-agent actors in ManuMind AI."""
    SUPERVISOR = "SUPERVISOR"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"


class AgentExecutionStatus(str, Enum):
    """Execution status for individual agent invocations."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AnomalyExecutionStatus(str, Enum):
    """Operational execution status for anomaly detection inference."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AnomalyType(str, Enum):
    """Taxonomy of manufacturing telemetry anomalies."""
    VIBRATION_SPIKE = "VIBRATION_SPIKE"
    OVERHEATING = "OVERHEATING"
    PRESSURE_DROP = "PRESSURE_DROP"
    ELECTRICAL_FAULT = "ELECTRICAL_FAULT"
    BEARING_DEGRADATION = "BEARING_DEGRADATION"
    MULTIVARIATE_ANOMALY = "MULTIVARIATE_ANOMALY"
    UNKNOWN = "UNKNOWN"
    NONE = "NONE"


class AnomalySeverity(str, Enum):
    """Severity classification for detected anomalies."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceStatus(str, Enum):
    """Categorical classification of confidence evaluation."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNCALIBRATED = "UNCALIBRATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceSourceType(str, Enum):
    """Source provenance classification for evidence items."""
    TELEMETRY = "TELEMETRY"
    SHAP_ANALYSIS = "SHAP_ANALYSIS"
    MAINTENANCE_LOG = "MAINTENANCE_LOG"
    RAG_DOCUMENT = "RAG_DOCUMENT"
    DEFECT_IMAGE = "DEFECT_IMAGE"
    SUPERVISOR_ASSESSMENT = "SUPERVISOR_ASSESSMENT"
    HUMAN_OBSERVATION = "HUMAN_OBSERVATION"


class VerificationStatus(str, Enum):
    """Verification status for root cause hypotheses."""
    UNVERIFIED = "UNVERIFIED"
    HYPOTHESIS_PENDING = "HYPOTHESIS_PENDING"
    VERIFIED = "VERIFIED"
    REFUTED = "REFUTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HumanApprovalStatus(str, Enum):
    """Governance gate status for human-in-the-loop decisions."""
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class VerificationMethod(str, Enum):
    """Corroboration method used to verify or refute a root-cause hypothesis."""
    TIER_1_MULTI_MODAL_CONSENSUS = "TIER_1_MULTI_MODAL_CONSENSUS"
    TIER_2_SENSOR_RAG_CORROBORATION = "TIER_2_SENSOR_RAG_CORROBORATION"
    TIER_3_HUMAN_EXPERT_ESCALATION = "TIER_3_HUMAN_EXPERT_ESCALATION"
    HISTORICAL_MAINTENANCE_MATCH = "HISTORICAL_MAINTENANCE_MATCH"
    UNVERIFIED = "UNVERIFIED"


class VerificationAuthority(str, Enum):
    """Authorized component or entity producing a verification decision."""
    SUPERVISOR_CORROBORATION_ENGINE = "Supervisor:CorroborationEngine"
    HUMAN_MAINTENANCE_ENGINEER = "Human:MaintenanceEngineer"
    NONE = "NONE"


class SupervisorAction(str, Enum):
    """Routing and governance actions determined by the Supervisor Agent."""
    ROUTE_TO_ANOMALY_DETECTION = "ROUTE_TO_ANOMALY_DETECTION"
    ROUTE_TO_ROOT_CAUSE_ANALYSIS = "ROUTE_TO_ROOT_CAUSE_ANALYSIS"
    REQUEST_ADDITIONAL_EVIDENCE = "REQUEST_ADDITIONAL_EVIDENCE"
    ESCALATE_TO_HUMAN_GATE = "ESCALATE_TO_HUMAN_GATE"
    COMPLETE_WORKFLOW = "COMPLETE_WORKFLOW"
    FAIL_WORKFLOW = "FAIL_WORKFLOW"


class RCAExecutionStatus(str, Enum):
    """Operational execution status for Root Cause Analysis Agent."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class EvidenceSourceAvailability(str, Enum):
    """Availability status for individual evidence sources queried by RCA."""
    AVAILABLE = "AVAILABLE"
    EMPTY = "EMPTY"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class RootCauseCategory(str, Enum):
    """Domain taxonomy of manufacturing machine root-cause failure mechanisms."""
    MECHANICAL_WEAR = "MECHANICAL_WEAR"
    BEARING_DEGRADATION = "BEARING_DEGRADATION"
    LUBRICATION_FAILURE = "LUBRICATION_FAILURE"
    MISALIGNMENT = "MISALIGNMENT"
    ELECTRICAL_FAULT = "ELECTRICAL_FAULT"
    MOTOR_DEGRADATION = "MOTOR_DEGRADATION"
    COOLING_FAILURE = "COOLING_FAILURE"
    PRESSURE_SYSTEM_FAULT = "PRESSURE_SYSTEM_FAULT"
    SENSOR_MALFUNCTION = "SENSOR_MALFUNCTION"
    OPERATIONAL_OVERLOAD = "OPERATIONAL_OVERLOAD"
    UNKNOWN = "UNKNOWN"


