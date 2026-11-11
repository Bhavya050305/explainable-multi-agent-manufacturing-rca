"""
ManuMind AI — RAG Retrieval Configuration
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from typing import Set


class RetrievalConfig:
    """Configuration parameters for the semantic vector retrieval engine."""

    # Top-K limits
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20
    MIN_TOP_K: int = 1

    # Corpus validation boundaries
    VALID_CATEGORIES: Set[str] = {"SOP", "TROUBLESHOOTING", "SAFETY", "INCIDENT"}
    VALID_MACHINES: Set[str] = {
        "M101", "M102", "M103", "M104", "M105",
        "M106", "M107", "M108", "M109", "M110"
    }

    # BGE Query instruction prefixing
    # Official BAAI bge-small-en-v1.5 retrieval instruction
    BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "
    USE_BGE_QUERY_PREFIX: bool = True

    # Provisional minimum similarity threshold (subject to golden evaluation validation)
    PROVISIONAL_SIMILARITY_CUTOFF: float = 0.40

    # Diversification parameters
    DEFAULT_MAX_SEGMENTS_PER_DOC: int = 2

    # Database targets
    COLLECTION_NAME: str = "manumind_bge_small_v1"


retrieval_config = RetrievalConfig()
