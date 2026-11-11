"""
ManuMind AI — RAG Ingestion Pipeline Schemas
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExecutionMode(str, Enum):
    """Pipeline execution modes."""
    VALIDATION_ONLY = "validation_only"
    IN_MEMORY_INGESTION = "in_memory_ingestion"


class DocumentType(str, Enum):
    """Recognized document categories."""
    SOP = "SOP"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    SAFETY = "SAFETY"
    INCIDENT = "INCIDENT"


class SourceType(str, Enum):
    """Permitted provenance types."""
    SYNTHETIC_DEMONSTRATION = "SYNTHETIC_DEMONSTRATION"
    DERIVED_SYNTHETIC = "DERIVED_SYNTHETIC"


class RawDocument(BaseModel):
    """Raw document loaded from disk prior to parsing."""
    model_config = ConfigDict(frozen=True)

    source_path: str
    file_name: str
    raw_content: str
    size_bytes: int
    raw_file_hash: str


class DocumentMetadata(BaseModel):
    """Validated metadata extracted from YAML front matter."""
    model_config = ConfigDict(extra="ignore")

    document_id: str
    title: str
    document_type: str
    document_version: str = "1.0.0"
    source_type: str
    is_synthetic: bool = True
    machine_id: Optional[str] = None
    machine_type: Optional[str] = None
    component: Optional[str] = None
    fault_category: Optional[str] = None
    target_machine: Optional[str] = None
    applicable_scope: Optional[str] = None
    source_name: Optional[str] = None
    source_record_id: Optional[str] = None
    original_row_index: Optional[int] = None
    event_date: Optional[str] = None
    created_at: Optional[str] = None
    generation_method: Optional[str] = None
    review_status: Optional[str] = None
    operational_disclaimer: Optional[str] = None
    criticality: Optional[int] = None
    production_impact: Optional[int] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionRecord(BaseModel):
    """Structured, validated in-memory document ingestion record."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    document_id: str
    title: str
    document_type: str
    source_type: str
    is_synthetic: bool
    machine_id: Optional[str] = None
    machine_type: Optional[str] = None
    component: Optional[str] = None
    fault_category: Optional[str] = None
    version: str
    source_path: str
    content: str  # Preserved original body content
    content_hash: str  # SHA-256 of normalized body content
    raw_file_hash: str  # SHA-256 of entire raw file bytes on disk
    metadata: DocumentMetadata


class RejectedDocument(BaseModel):
    """Details of any document rejected during loading or validation."""
    source_path: str
    document_id: Optional[str] = None
    rejection_reason: str
    error_details: Optional[str] = None
    phase: str


class ManifestReconciliationResult(BaseModel):
    """Detailed reconciliation against corpus_manifest.json."""
    total_manifest_entries: int
    matched_entries: int
    missing_on_disk: List[str] = Field(default_factory=list)
    untracked_on_disk: List[str] = Field(default_factory=list)
    hash_mismatches: List[str] = Field(default_factory=list)
    size_mismatches: List[str] = Field(default_factory=list)
    is_reconciled: bool = False


class IncidentMappingResult(BaseModel):
    """Detailed reconciliation of incidents against maintenance CSV."""
    total_csv_rows: int
    mapped_documents: int
    mismatches: List[str] = Field(default_factory=list)
    is_reconciled: bool = False


class IngestionSummary(BaseModel):
    """Overall summary of document discovery, validation, and ingestion."""
    execution_mode: ExecutionMode
    total_discovered: int = 0
    total_parsed: int = 0
    total_valid: int = 0
    total_rejected: int = 0
    duplicate_ids_count: int = 0
    provenance_passed: int = 0
    disclaimer_passed: int = 0
    incident_mappings_reconciled: int = 0
    manifest_reconciliation: ManifestReconciliationResult
    incident_mapping_result: IncidentMappingResult
    document_type_distribution: Dict[str, int] = Field(default_factory=dict)
    machine_distribution: Dict[str, int] = Field(default_factory=dict)
    fault_category_distribution: Dict[str, int] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    rejected_documents: List[RejectedDocument] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
