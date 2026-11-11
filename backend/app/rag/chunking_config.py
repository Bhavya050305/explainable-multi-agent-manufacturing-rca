"""
ManuMind AI — RAG Document Chunking Configuration
Phase 3 Step 3: Document Chunking and Metadata-Aware Chunk Generation

Department of AI & Data Science — RMK Engineering College
"""

from typing import Set


class ChunkingConfig:
    """Configuration settings for document chunking."""

    # Target token parameters
    TARGET_CHUNK_SIZE_TOKENS: int = 400
    MIN_PREFERRED_CHUNK_SIZE_TOKENS: int = 150
    MAX_CHUNK_SIZE_TOKENS: int = 450
    CHUNK_OVERLAP_TOKENS: int = 50

    # Strategy and versioning identifiers
    CHUNKING_STRATEGY: str = "structural_markdown_v1"
    TOKEN_ESTIMATION_METHOD: str = "deterministic_subword_heuristic_v1"

    # Safety classification keywords
    SAFETY_KEYWORDS: Set[str] = {
        "SAFETY",
        "DANGER",
        "WARNING",
        "CAUTION",
        "HAZARD",
        "LOTO",
        "LOCKOUT",
        "TAGOUT",
        "ISOLATION",
        "DEPRESSURIZATION",
        "DE-ENERGIZATION",
        "PPE",
        "ELECTRICAL",
        "HYDRAULIC",
        "ARC-FLASH",
        "SPEC_REQUIRED",
    }


chunking_config = ChunkingConfig()
