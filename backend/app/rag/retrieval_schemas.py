"""
ManuMind AI — RAG Retrieval Schemas
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RetrievalMode(str, Enum):
    """Retrieval operation modes."""
    MACHINE_SPECIFIC = "machine_specific"
    CROSS_MACHINE = "cross_machine"
    GLOBAL_ONLY = "global_only"


class RetrievalFilter(BaseModel):
    """Optional metadata filters applied during vector similarity search."""
    machine_id: Optional[str] = Field(None, description="Target machine identifier (e.g. M101-M110)")
    category: Optional[str] = Field(None, description="Document category (SOP, TROUBLESHOOTING, SAFETY, INCIDENT)")
    source_type: Optional[str] = Field(None, description="Provenance source type")
    is_synthetic: Optional[bool] = Field(None, description="Synthetic data filter flag")
    is_safety_related: Optional[bool] = Field(None, description="Filter for safety-critical procedures")
    document_id: Optional[str] = Field(None, description="Target document identifier")
    source_record_id: Optional[str] = Field(None, description="Incident source record ID (e.g. ROW-0001)")
    cross_machine: bool = Field(False, description="Whether cross-machine knowledge retrieval is enabled")
    include_global: bool = Field(True, description="Whether plant-wide/global documents are included in machine-specific mode")

    @field_validator("machine_id")
    @classmethod
    def normalize_machine_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.strip().upper()
        if not v_upper:
            return None
        return v_upper

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.strip().upper()
        valid = {"SOP", "TROUBLESHOOTING", "SAFETY", "INCIDENT"}
        if v_upper not in valid:
            raise ValueError(f"Invalid category '{v}'; must be one of {valid}")
        return v_upper


class RetrievalQuery(BaseModel):
    """Validated user or agent query request."""
    query_text: str = Field(..., min_length=1, max_length=2000, description="Natural language manufacturing query")
    filter: Optional[RetrievalFilter] = Field(None, description="Metadata filtering parameters")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to retrieve (default: 5, max: 20)")
    retrieval_mode: Optional[RetrievalMode] = Field(None, description="Explicit retrieval mode override")
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional minimum similarity cutoff")
    diversify_documents: bool = Field(False, description="Diversify results across distinct documents")

    @field_validator("query_text")
    @classmethod
    def reject_whitespace(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Query text cannot be empty or whitespace-only")
        return s


class RetrievalResultItem(BaseModel):
    """Single ranked retrieval result with full provenance lineage."""
    rank: int = Field(..., ge=1, description="Rank in retrieval results (1-indexed)")
    segment_id: str = Field(..., description="ChromaDB vector record ID")
    parent_chunk_id: str = Field(..., description="Canonical parent chunk ID")
    document_id: str = Field(..., description="Source corpus document ID")
    machine_id: Optional[str] = Field(None, description="Target machine ID if machine-specific, else None")
    category: str = Field(..., description="Corpus document category")
    source_type: str = Field(..., description="Data provenance classification")
    is_synthetic: bool = Field(..., description="Whether content is synthetic")
    is_safety_related: bool = Field(..., description="Whether content covers safety/LOTO/hazards")
    source_path: str = Field(..., description="Relative file path in repository")
    source_record_id: Optional[str] = Field(None, description="Maintenance CSV source record ID")
    original_row_index: Optional[int] = Field(None, description="Maintenance CSV row index")
    event_date: Optional[str] = Field(None, description="Recorded incident or procedure date")
    section_heading: str = Field(..., description="Markdown section heading")
    parent_heading: Optional[str] = Field(None, description="Parent markdown heading")
    raw_distance: float = Field(..., description="Raw ChromaDB cosine distance")
    similarity_score: float = Field(..., description="Derived similarity: max(0.0, 1.0 - raw_distance)")
    content: str = Field(..., description="Retrieved passage text")
    content_hash: str = Field(..., description="SHA-256 digest of passage text")
    raw_file_hash: str = Field(..., description="SHA-256 digest of original raw file")
    provenance_validated: bool = Field(True, description="Whether source file and row provenance was verified")
    provenance_details: Optional[str] = Field(None, description="Diagnostic notes on provenance validation")


class RetrievalResponse(BaseModel):
    """Complete traceable retrieval service response."""
    query: str = Field(..., description="Original user query")
    processed_query: str = Field(..., description="Processed query string passed to embedding model")
    retrieval_mode: str = Field(..., description="Execution retrieval mode")
    requested_top_k: int = Field(..., description="Requested top_k value")
    returned_count: int = Field(..., description="Actual number of results returned")
    results: List[RetrievalResultItem] = Field(default_factory=list, description="Ranked retrieval results")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="Compiled ChromaDB filter dict")
    query_duration_seconds: float = Field(..., description="Total retrieval duration in seconds")
    embedding_latency_seconds: float = Field(..., description="Query embedding forward pass latency")
    search_latency_seconds: float = Field(..., description="Vector index search latency")
    resolution_latency_seconds: float = Field(..., description="Source resolution and provenance latency")
    embedding_model: str = Field(..., description="Embedding model name and commit")
    collection_name: str = Field(..., description="Queried ChromaDB collection name")
