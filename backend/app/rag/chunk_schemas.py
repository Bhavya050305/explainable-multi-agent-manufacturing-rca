"""
ManuMind AI — RAG Document Chunk Schemas
Phase 3 Step 3: Document Chunking and Metadata-Aware Chunk Generation

Department of AI & Data Science — RMK Engineering College
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.app.rag.schemas import ExecutionMode


class ChunkMetadata(BaseModel):
    """Rich, validated metadata sidecar attached to each chunk."""
    model_config = ConfigDict(extra="ignore")

    document_id: str
    chunk_index: int
    source_type: str
    is_synthetic: bool = True
    category: str
    machine_id: Optional[str] = None
    section_heading: str
    parent_heading: Optional[str] = None
    source_path: str
    raw_file_hash: str
    source_record_id: Optional[str] = None
    original_row_index: Optional[int] = None
    event_date: Optional[str] = None
    token_count: int
    is_safety_related: bool = False
    contains_spec_placeholder: bool = False
    contains_synthetic_disclaimer: bool = False
    chunking_strategy: str = "structural_markdown_v1"


class ChunkRecord(BaseModel):
    """Structured, metadata-aware chunk record."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    content_hash: str
    metadata: ChunkMetadata


class ChunkingQualityMetrics(BaseModel):
    """Quantitative quality metrics evaluated across the chunked corpus."""
    total_source_documents: int
    total_chunks_generated: int
    chunks_per_category: Dict[str, int] = Field(default_factory=dict)
    chunks_per_machine: Dict[str, int] = Field(default_factory=dict)
    chunks_per_machine_category: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    min_token_count: int
    max_token_count: int
    mean_token_count: float
    median_token_count: float
    chunks_exceeding_target: int
    chunks_below_minimum_preferred: int
    safety_related_chunks: int
    chunks_with_spec_placeholders: int
    chunks_with_synthetic_disclaimers: int
    incident_chunks: int
    duplicate_chunk_ids_count: int = 0
    empty_chunks_count: int = 0
    source_text_coverage_percentage: float = 100.0
    is_deterministic: bool = True


class ChunkingSummary(BaseModel):
    """Top-level summary of chunk generation execution."""
    execution_mode: ExecutionMode
    metrics: ChunkingQualityMetrics
    duration_seconds: float
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
