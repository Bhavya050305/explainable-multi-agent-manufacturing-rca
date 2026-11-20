"""
ManuMind AI — MCP Server Pydantic Schemas
Phase 4 Step 2: Read-Only Manufacturing MCP Tools

Department of AI & Data Science — RMK Engineering College
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Tool 1: get_machine_data Schemas
# ---------------------------------------------------------------------------

class MachineProfile(BaseModel):
    """Machine asset metadata profile."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique machine identifier (M101-M110)")
    name: str = Field(..., description="Human-readable machine name")
    type: str = Field(..., description="Machine category/type")
    criticality: int = Field(..., description="Criticality rating (1 to 5)")
    production_impact: int = Field(..., description="Production impact rating (1 to 5)")


class TelemetryRecord(BaseModel):
    """Point-in-time 5-channel sensor telemetry record."""
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(..., description="ISO 8601 timestamp of sensor observation")
    vibration: float = Field(..., description="Vibration velocity RMS in mm/s")
    temperature: float = Field(..., description="Bearing/motor housing temperature in °C")
    pressure: float = Field(..., description="Hydraulic/pneumatic line pressure in bar")
    current: float = Field(..., description="Motor load current in Amperes")
    rpm: float = Field(..., description="Spindle/motor speed in RPM")


class GetMachineDataResponse(BaseModel):
    """Structured response for get_machine_data MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Query outcome status (SUCCESS, NO_DATA, ERROR)")
    machine_id: str = Field(..., description="Queried machine identifier")
    machine_profile: Optional[MachineProfile] = Field(None, description="Asset metadata profile")
    telemetry_count: int = Field(..., description="Number of telemetry observations returned")
    telemetry: List[TelemetryRecord] = Field(default_factory=list, description="Chronological sensor readings")
    window_applied: Optional[Dict[str, Any]] = Field(None, description="Details of applied time window filter")
    message: Optional[str] = Field(None, description="Diagnostic message or warning")


# ---------------------------------------------------------------------------
# Tool 2: detect_anomaly Schemas
# ---------------------------------------------------------------------------

class IsolationForestResult(BaseModel):
    """Point-in-time tabular anomaly scoring result from Isolation Forest."""
    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., description="Continuous anomaly intensity (-decision_function)")
    threshold: float = Field(..., description="Frozen calibrated decision threshold (0.0269)")
    is_anomaly: bool = Field(..., description="True if score > threshold")
    explanation_status: Optional[str] = Field(None, description="SHAP explanation availability status")
    shap_explanation: Optional[Dict[str, Any]] = Field(None, description="Game-theoretic SHAP attributions")


class LSTMSAutoencoderResult(BaseModel):
    """Sequence reconstruction anomaly detection result from LSTM Autoencoder."""
    model_config = ConfigDict(extra="forbid")

    reconstruction_error: float = Field(..., description="Mean squared reconstruction error over 30 steps")
    threshold: float = Field(..., description="Frozen calibrated p99 threshold (0.901464)")
    is_anomaly: bool = Field(..., description="True if reconstruction_error > threshold")
    attribution_status: Optional[str] = Field(None, description="Sensor attribution availability status")
    sensor_attribution: Optional[Dict[str, Any]] = Field(None, description="Per-channel MSE reconstruction attribution")


class DetectAnomalyResponse(BaseModel):
    """Structured response for detect_anomaly MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Inference outcome status (SUCCESS, INSUFFICIENT_DATA, INVALID_INPUT, ERROR)")
    machine_id: str = Field(..., description="Evaluated machine identifier")
    classification: str = Field(..., description="Overall anomaly classification (NORMAL, ANOMALY_DETECTED, INSUFFICIENT_DATA)")
    is_anomaly: Optional[bool] = Field(None, description="Composite anomaly flag")
    analysis_window: Dict[str, Any] = Field(..., description="Metadata describing analyzed telemetry window")
    isolation_forest: Optional[IsolationForestResult] = Field(None, description="Isolation Forest inference details")
    lstm_autoencoder: Optional[LSTMSAutoencoderResult] = Field(None, description="LSTM Autoencoder inference details")
    warnings: List[str] = Field(default_factory=list, description="Data quality or execution warnings")
    disclaimer: str = Field(
        default="Anomaly score indicates statistical deviation from baseline operational patterns. "
                "It does NOT represent failure probability, remaining useful life (RUL), or physical root cause.",
        description="Mandatory interpretation safety disclaimer"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of inference execution")


# ---------------------------------------------------------------------------
# Tool 3: predict_failure_risk Schemas
# ---------------------------------------------------------------------------

class PredictFailureRiskResponse(BaseModel):
    """Formal capability-status stub response for predict_failure_risk MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="NOT_AVAILABLE", description="Formal capability status: strictly NOT_AVAILABLE")
    machine_id: str = Field(..., description="Queried machine identifier")
    model_available: bool = Field(default=False, description="Explicit indicator of model absence")
    horizon_hours: int = Field(default=288, description="Requested forecast horizon in hours (H=288)")
    reason: str = Field(
        default="Phase 2 Step 5 recorded a formal NO-GO decision for the H=288 failure-risk regression task. "
                "Quantitative evaluation demonstrated insufficient calibration (R^2 < 0.20, high forecast uncertainty), "
                "failing feasibility criteria for automated failure risk prediction.",
        description="Formal audit justification for capability status"
    )
    recommendation: str = Field(
        default="Use the 'detect_anomaly' tool for unsupervised statistical and sequence-level anomaly detection. "
                "Note: Anomaly scores reflect statistical pattern deviation and do NOT constitute calibrated failure probability "
                "or Remaining Useful Life (RUL).",
        description="Guidance on valid alternative condition monitoring tools"
    )
    disclaimer: str = Field(
        default="The absence of a failure risk model does not imply that the machine is healthy or free of defects. "
                "Routine maintenance schedules and operator inspections should be maintained.",
        description="Safety interpretation disclaimer"
    )


# ---------------------------------------------------------------------------
# Tool 5: search_manuals Schemas (Phase 4 Step 3)
# ---------------------------------------------------------------------------

class ManualSearchResult(BaseModel):
    """Ranked knowledge passage result with provenance and similarity scores."""
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1, description="Ranking position (1-indexed)")
    document_id: str = Field(..., description="Source document identifier")
    category: str = Field(..., description="Corpus category (SOP, TROUBLESHOOTING, SAFETY, INCIDENT)")
    section_heading: str = Field(..., description="Markdown section heading")
    parent_heading: Optional[str] = Field(None, description="Parent section heading")
    similarity_score: float = Field(..., description="Derived cosine similarity score [0.0, 1.0]")
    content: str = Field(..., description="Retrieved excerpt text")
    source_path: str = Field(..., description="Relative file path in repository")
    is_synthetic: bool = Field(..., description="Flag indicating synthetic demonstration origin")
    is_safety_related: bool = Field(..., description="Flag indicating safety/lockout procedure")
    source_type: str = Field(..., description="Provenance classification")
    segment_id: str = Field(..., description="Unique vector store segment ID")
    parent_chunk_id: str = Field(..., description="Canonical parent chunk ID")
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of segment content")
    provenance_validated: Optional[bool] = Field(True, description="Flag indicating provenance hash matched source document")



class SearchManualsResponse(BaseModel):
    """Structured response for search_manuals MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Search outcome status (SUCCESS, NO_RESULTS, ERROR)")
    query: str = Field(..., description="Original search query text")
    requested_k: int = Field(..., description="Requested top_k results count")
    returned_count: int = Field(..., description="Number of results returned")
    results: List[ManualSearchResult] = Field(default_factory=list, description="Ranked knowledge excerpts")
    disclaimer: str = Field(
        default="Retrieved excerpts are for reference and troubleshooting assistance only. "
                "Material derived from synthetic incident logs is clearly identified and does NOT constitute "
                "approved operational directives or verified physical root cause.",
        description="Mandatory knowledge and provenance disclaimer"
    )
    collection_name: Optional[str] = Field(None, description="Queried ChromaDB collection identifier")
    embedding_model: Optional[str] = Field(None, description="Embedding model identifier and revision")


# ---------------------------------------------------------------------------
# Tool 4: get_maintenance_history Schemas (Phase 4 Step 4)
# ---------------------------------------------------------------------------

class MaintenanceRecordItem(BaseModel):
    """Historical maintenance log entry from production maintenance_history database."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Unique maintenance record identifier (primary key)")
    machine_id: str = Field(..., description="Target machine identifier (M101 to M110)")
    date: str = Field(..., description="ISO 8601 timestamp of maintenance event")
    issue: str = Field(..., description="Reported failure, operational symptom, or maintenance reason")
    action: str = Field(..., description="Corrective maintenance action, replacement, or procedure executed")
    outcome: str = Field(..., description="Recorded event outcome ('Resolved', 'Monitoring', 'Temporary Fix')")


class GetMaintenanceHistoryResponse(BaseModel):
    """Structured response for get_maintenance_history MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Retrieval outcome status (SUCCESS, NO_DATA, ERROR)")
    machine_id: str = Field(..., description="Target machine identifier queried")
    total_returned: int = Field(..., ge=0, description="Total number of maintenance records returned")
    records: List[MaintenanceRecordItem] = Field(default_factory=list, description="Chronological maintenance records")
    message: Optional[str] = Field(None, description="Diagnostic summary or data status message")
    disclaimer: str = Field(
        default="Historical maintenance records represent past interventions and reported resolutions. "
                "Past maintenance outcomes do not guarantee current physical asset health, absence of new degradation, "
                "or remaining useful life (RUL).",
        description="Mandatory operational safety and interpretation disclaimer"
    )


# ---------------------------------------------------------------------------
# Tool 5: check_defect_image Schemas (Phase 4 Step 5)
# ---------------------------------------------------------------------------

class CheckDefectImageResponse(BaseModel):
    """Structured response for check_defect_image MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Classification outcome status ('SUCCESS', 'ERROR')")
    image_name: str = Field(..., description="Filename of the analyzed workpiece image")
    image_path: str = Field(..., description="Normalized repository-relative path to the analyzed image")
    predicted_class: str = Field(..., description="Raw predicted class identifier (surface_crack, spalling, dent, normal_surface)")
    defect_type: str = Field(..., description="Human-readable defect title (Surface Crack, Spalling, Dent, Normal Surface)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Softmax output probability float [0.0, 1.0]")
    confidence_interpretation: str = Field(
        default="Softmax output float [0.0, 1.0] representing model classification likelihood across the 4 synthetic classes. "
                "This value is uncalibrated and does NOT constitute a mathematical probability guarantee or physical inspection certification.",
        description="Mandatory confidence interpretation and limitations notice"
    )
    is_defective: bool = Field(..., description="True if predicted defect is surface_crack, spalling, or dent; False if normal_surface")
    affected_machine_id: Optional[str] = Field(None, description="Confounded candidate machine identifier (e.g. M104, M102, M101)")
    batch_number: Optional[str] = Field(None, description="Associated manufacturing batch code (e.g. B-8821, B-7740, B-9910)")
    recommendation: str = Field(..., description="Actionable manufacturing operational recommendation")
    class_probabilities: Dict[str, float] = Field(default_factory=dict, description="Softmax probabilities across all 4 classes")
    is_synthetic: bool = Field(default=True, description="Flag indicating image is from synthetic demonstration dataset")
    disclaimer: str = Field(
        default="Visual inspection results are produced by Compact ResNet-18 trained exclusively on a synthetic "
                "demonstration dataset (600 BMP images). Predictions are intended strictly for supervisory advisory "
                "assistance and troubleshooting workflows. They do NOT guarantee physical asset integrity, absence of unmodeled "
                "micro-defects, or replace certified non-destructive testing (NDT).",
        description="Mandatory synthetic demonstration and operational safety disclaimer"
    )
    message: Optional[str] = Field(None, description="Optional diagnostic or error message")


# ---------------------------------------------------------------------------
# Tools 8 & 9: Secure Maintenance Ticket Creation Schemas (Phase 4 Step 6)
# ---------------------------------------------------------------------------

class ProposeMaintenanceTicketResponse(BaseModel):
    """Structured response for propose_maintenance_ticket MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Proposal outcome status ('PENDING_APPROVAL', 'ERROR')")
    proposal_id: str = Field(..., description="Unique ticket proposal identifier (e.g. 'PROP-2026-0001')")
    machine_id: str = Field(..., description="Target machine identifier (M101 to M110)")
    alert_id: Optional[str] = Field(None, description="Linked alert identifier if matched/specified")
    recommendation: str = Field(..., description="Actionable maintenance recommendation proposed by agent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Proposal confidence score [0.0, 1.0]")
    payload_hash: str = Field(..., description="SHA-256 canonical hash of the proposal payload")
    requires_human_approval: bool = Field(default=True, description="Strict human-in-the-loop requirement flag")
    is_synthetic: bool = Field(default=True, description="Flag indicating synthetic demonstration environment")
    created_at: str = Field(..., description="ISO 8601 proposal creation timestamp")
    expires_at: str = Field(..., description="ISO 8601 proposal validity expiration timestamp")
    approval_instructions: str = Field(
        default="To create this maintenance ticket, an authenticated human engineer must review the proposal, "
                "verify the recommendation and evidence, and authorize ticket creation via the trusted human approval "
                "interface to obtain a signed cryptographic approval token. Pass proposal_id and approval_token to "
                "create_maintenance_ticket.",
        description="Clear instructions for completing human authorization"
    )
    message: str = Field(..., description="Operational status summary message")
    disclaimer: str = Field(
        default="Ticket proposals do NOT create active maintenance work orders. An active ticket is only created "
                "after explicit review and cryptographic authorization by an authenticated human engineer. AI agents "
                "are strictly prohibited from authorizing their own ticket proposals.",
        description="Mandatory governance and human boundary disclaimer"
    )


class CreateMaintenanceTicketResponse(BaseModel):
    """Structured response for create_maintenance_ticket MCP tool."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Ticket creation status ('APPROVED', 'ERROR')")
    ticket_id: str = Field(..., description="Unique created maintenance ticket identifier (e.g. 'TCK-2026-002')")
    proposal_id: str = Field(..., description="Associated ticket proposal identifier")
    machine_id: str = Field(..., description="Target machine identifier")
    alert_id: str = Field(..., description="Associated manufacturing alert identifier")
    recommendation: str = Field(..., description="Approved maintenance recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Ticket confidence score [0.0, 1.0]")
    approved_by: str = Field(..., description="Authenticated human engineer identifier who authorized ticket creation")
    approved_at: str = Field(..., description="ISO 8601 timestamp of human approval")
    created_at: str = Field(..., description="ISO 8601 timestamp of ticket creation in authoritative database")
    is_synthetic: bool = Field(default=True, description="Flag indicating synthetic demonstration environment")
    message: str = Field(..., description="Operational outcome summary message")
    disclaimer: str = Field(
        default="Maintenance ticket created following verified human authorization. AI agent proposed recommendations "
                "and supporting telemetry are advisory. Certified plant personnel remain responsible for physical maintenance execution.",
        description="Mandatory operational safety and supervisory disclaimer"
    )



