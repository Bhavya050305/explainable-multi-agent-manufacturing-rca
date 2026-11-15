"""
ManuMind AI — Grounded Answer Generation Schemas
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    """Calibrated confidence category for manufacturing decision support."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"
    ABSTAINED = "ABSTAINED"


class AbstentionReason(str, Enum):
    """Explicit, auditable reason for generation abstention."""
    NO_EVALUATED_EVIDENCE = "NO_EVALUATED_EVIDENCE"
    MACHINE_MISMATCH = "MACHINE_MISMATCH"
    MISSING_SPECIFICATION = "MISSING_SPECIFICATION"
    CONTRADICTORY_SOURCES = "CONTRADICTORY_SOURCES"
    UNSUPPORTED_NUMERICAL_QUERY = "UNSUPPORTED_NUMERICAL_QUERY"
    SAFETY_CRITICAL_INCOMPLETE = "SAFETY_CRITICAL_INCOMPLETE"
    UNAUTHORIZED_OPERATIONAL_COMMAND = "UNAUTHORIZED_OPERATIONAL_COMMAND"
    SAFETY_INTERLOCK_VIOLATION = "SAFETY_INTERLOCK_VIOLATION"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    OUT_OF_DOMAIN_QUERY = "OUT_OF_DOMAIN_QUERY"


class Citation(BaseModel):
    """Grounding citation linking a generated statement directly to retrieved evidence."""
    citation_id: str = Field(..., description="Unique citation token, e.g., '[CIT-1]'")
    document_id: str = Field(..., description="Canonical document ID, e.g., 'DOC-SOP-M104-001'")
    segment_id: str = Field(..., description="Vector segment identifier")
    parent_chunk_id: str = Field(..., description="Parent chunk identifier")
    source_path: str = Field(..., description="File path relative to repository or knowledge_base")
    section_heading: str = Field(default="General", description="Section heading from markdown")
    category: str = Field(..., description="SOP, TROUBLESHOOTING, SAFETY, or INCIDENT")
    machine_id: Optional[str] = Field(default=None, description="Fleet machine ID if machine-specific")
    original_row_index: Optional[int] = Field(default=None, description="CSV row index for incidents")
    source_record_id: Optional[str] = Field(default=None, description="Incident source record ID")
    snippet: str = Field(..., description="Exact textual excerpt supporting the citation")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Derived cosine similarity")
    is_synthetic: bool = Field(default=True, description="Indicates synthetic provenance")


class GroundedAnswer(BaseModel):
    """
    Structured, fully grounded response for explainable manufacturing anomaly investigation.
    Strictly forbids presenting correlational attribution as verified physical causality.
    """
    query: str = Field(..., description="Original user / agent query")
    answer: str = Field(..., description="Comprehensive grounded response text")
    summary: str = Field(..., description="Concise executive summary")
    observed_evidence: List[str] = Field(
        default_factory=list,
        description="List of factual observations directly supported by retrieved evidence",
    )
    possible_explanations: List[str] = Field(
        default_factory=list,
        description="Engineering hypotheses and possible root causes under investigation",
    )
    recommended_investigations: List[str] = Field(
        default_factory=list,
        description="Recommended physical diagnostic steps (not operational commands)",
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Known unknowns, missing data, or unverified sensor assumptions",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Direct citations linking claims to retrieved segments",
    )
    confidence_label: ConfidenceLabel = Field(
        default=ConfidenceLabel.MEDIUM,
        description="Qualitative confidence label (not statistical probability)",
    )
    abstained: bool = Field(
        default=False,
        description="Whether the system abstained from providing an authoritative answer",
    )
    abstention_reason: Optional[AbstentionReason] = Field(
        default=None,
        description="Specific justification when abstained is True",
    )
    is_synthetic: bool = Field(
        default=True,
        description="Discloses synthetic demonstration provenance",
    )
    source_provenance: str = Field(
        default="SYNTHETIC_DEMONSTRATION",
        description="Lineage classification of evidence corpus",
    )
    provider: str = Field(
        default="mock",
        description="LLM provider name (e.g., 'mock', 'gemini', 'openai')",
    )
    model_identifier: str = Field(
        default="manumind-grounded-mock-v1",
        description="Specific model version or mock simulator name",
    )
    generation_latency_ms: float = Field(default=0.0, ge=0.0)
    retrieval_latency_ms: float = Field(default=0.0, ge=0.0)
    total_latency_ms: float = Field(default=0.0, ge=0.0)
    validation_passed: bool = Field(default=True)
    validation_notes: List[str] = Field(default_factory=list)
