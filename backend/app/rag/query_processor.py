"""
ManuMind AI — RAG Query Processor
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.rag.retrieval_config import RetrievalConfig, retrieval_config


class ProcessedQuery(BaseModel):
    """Result of query normalization and parameter extraction."""
    original_query: str
    normalized_query: str
    embedding_query: str
    extracted_machine_id: Optional[str] = None
    detected_machine_ids: List[str] = Field(default_factory=list)
    has_conflicting_machines: bool = False
    prefix_applied: bool = False


class QueryProcessor:
    """
    Validates, normalizes, and extracts industrial metadata from natural-language queries.
    Preserves engineering symbols and applies official BGE search instruction prefixes.
    """

    MACHINE_PATTERN = re.compile(r"\b(M10[1-9]|M110)\b", re.IGNORECASE)

    def __init__(self, config: RetrievalConfig = retrieval_config):
        self.config = config

    def process_query(
        self,
        query_text: str,
        apply_bge_prefix: Optional[bool] = None,
    ) -> ProcessedQuery:
        """
        Validate, normalize, and prepare query for embedding.
        Args:
            query_text: Raw query text.
            apply_bge_prefix: Whether to prepend official BGE retrieval instruction.
        Returns:
            ProcessedQuery model.
        Raises:
            ValueError: If query is empty, whitespace-only, or invalid length.
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty or whitespace-only")

        cleaned = query_text.strip()
        if len(cleaned) < 2:
            raise ValueError("Query text must be at least 2 characters in length")
        if len(cleaned) > 2000:
            raise ValueError("Query text exceeds maximum allowed length of 2000 characters")

        # Collapse excessive internal whitespace while preserving newlines/content
        normalized = re.sub(r"[ \t]+", " ", cleaned)

        # Extract machine identifiers (M101-M110)
        matches = self.MACHINE_PATTERN.findall(normalized)
        unique_machines = sorted(list({m.upper() for m in matches}))

        has_conflict = len(unique_machines) > 1
        extracted_machine = unique_machines[0] if len(unique_machines) == 1 else None

        # Determine prefix policy
        should_prefix = (
            apply_bge_prefix
            if apply_bge_prefix is not None
            else self.config.USE_BGE_QUERY_PREFIX
        )

        prefix = self.config.BGE_QUERY_PREFIX if should_prefix else ""
        embedding_query = f"{prefix}{normalized}" if prefix else normalized

        return ProcessedQuery(
            original_query=query_text,
            normalized_query=normalized,
            embedding_query=embedding_query,
            extracted_machine_id=extracted_machine,
            detected_machine_ids=unique_machines,
            has_conflicting_machines=has_conflict,
            prefix_applied=bool(prefix),
        )


query_processor = QueryProcessor()
