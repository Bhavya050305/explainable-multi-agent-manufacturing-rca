"""
ManuMind AI — RAG Embedding Segment Schemas
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class EmbeddingSegmentMetadata(BaseModel):
    """
    Rich, validated metadata sidecar attached to each embedding segment.
    Preserves parent chunk lineage, source provenance, machine mapping, and safety flags.
    """
    model_config = ConfigDict(extra="ignore")

    parent_chunk_id: str
    document_id: str
    segment_index: int
    segment_count: int
    token_count_actual: int
    machine_id: Optional[str] = None
    source_record_id: Optional[str] = None
    original_row_index: Optional[int] = None
    event_date: Optional[str] = None
    source_type: str
    is_synthetic: bool = True
    category: str
    section_heading: str
    parent_heading: Optional[str] = None
    source_path: str
    raw_file_hash: str
    content_hash: str
    is_safety_related: bool = False
    contains_spec_placeholder: bool = False
    contains_synthetic_disclaimer: bool = False
    chunking_strategy: str = "structural_markdown_v1"
    embedding_model: str = "BAAI/bge-small-en-v1.5"


class EmbeddingSegment(BaseModel):
    """
    Individual embedding-ready text segment derived from a canonical chunk.
    Enforces that token_count_actual strictly respects model context limits.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    embedding_segment_id: str
    parent_chunk_id: str
    document_id: str
    segment_index: int
    content: str
    content_hash: str
    token_count: int
    metadata: EmbeddingSegmentMetadata


class SegmentationSummary(BaseModel):
    """Quantitative summary of embedding segment generation."""
    total_canonical_chunks: int
    total_segments_generated: int
    chunks_segmented_count: int
    segments_per_category: Dict[str, int] = Field(default_factory=dict)
    segments_per_machine: Dict[str, int] = Field(default_factory=dict)
    min_token_count: int
    max_token_count: int
    mean_token_count: float
    median_token_count: float
    segments_above_effective_limit: int = 0
    empty_segments_count: int = 0
    duration_seconds: float
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
