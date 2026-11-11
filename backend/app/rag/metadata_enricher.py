"""
ManuMind AI — RAG Chunk Metadata Enricher
Phase 3 Step 3: Document Chunking and Metadata-Aware Chunk Generation

Department of AI & Data Science — RMK Engineering College
"""

import hashlib
import re
from typing import List

from backend.app.rag.chunk_schemas import ChunkMetadata, ChunkRecord
from backend.app.rag.chunking_config import ChunkingConfig, chunking_config
from backend.app.rag.ingestion_service import IngestionService
from backend.app.rag.schemas import IngestionRecord
from backend.app.rag.text_splitter import SplitChunkResult


class MetadataEnricher:
    """Enriches split text fragments with rich, deterministic metadata sidecars."""

    def __init__(self, config: ChunkingConfig = chunking_config):
        self.config = config

    @staticmethod
    def strip_disclaimer_for_safety_scan(text: str) -> str:
        """
        Strip synthetic academic disclaimer banner solely for safety keyword evaluation.
        Ensures the disclaimer alone does not falsely classify a document as safety-related.
        The original text and disclaimer are preserved 100% intact in the chunk content.
        """
        return re.sub(
            r">\s*\*\*SAFETY NOTICE:\s*SYNTHETIC DEMONSTRATION MATERIAL[^\n]*",
            "",
            text,
            flags=re.IGNORECASE,
        )

    def enrich_chunks(
        self, doc: IngestionRecord, split_results: List[SplitChunkResult]
    ) -> List[ChunkRecord]:
        """
        Enrich a list of split chunk fragments from a document into ChunkRecord objects.
        Ensures continuous zero-based chunk indexing and deterministic IDs.
        """
        records: List[ChunkRecord] = []

        for idx, split_res in enumerate(split_results):
            chunk_id = f"{doc.document_id}_chk{idx:03d}"
            content = split_res.content.strip()

            # Normalized content hash
            norm_content = IngestionService.normalize_content(content)
            content_hash = hashlib.sha256(norm_content.encode("utf-8")).hexdigest()

            # Safety and disclaimer evaluation
            has_placeholder = "[SPEC_REQUIRED:" in content
            upper_content = content.upper()
            has_disclaimer = (
                "SYNTHETIC" in upper_content
                and (
                    "DEMONSTRATION" in upper_content
                    or "SAFETY NOTICE" in upper_content
                    or "HISTORICAL" in upper_content
                    or "NOT AN APPROVED" in upper_content
                )
            )

            # Substantive content for safety evaluation (excluding synthetic banner)
            substantive_text = self.strip_disclaimer_for_safety_scan(content)
            upper_substantive = substantive_text.upper()

            is_safety = (
                doc.document_type == "SAFETY"
                or split_res.is_safety_related
                or has_placeholder
                or any(kw in upper_substantive for kw in self.config.SAFETY_KEYWORDS)
            )

            metadata = ChunkMetadata(
                document_id=doc.document_id,
                chunk_index=idx,
                source_type=doc.source_type,
                is_synthetic=doc.is_synthetic,
                category=doc.document_type,
                machine_id=doc.machine_id,
                section_heading=split_res.section_heading,
                parent_heading=split_res.parent_heading,
                source_path=doc.source_path,
                raw_file_hash=doc.raw_file_hash,
                source_record_id=doc.metadata.source_record_id,
                original_row_index=doc.metadata.original_row_index,
                event_date=doc.metadata.event_date,
                token_count=split_res.token_count,
                is_safety_related=is_safety,
                contains_spec_placeholder=has_placeholder,
                contains_synthetic_disclaimer=has_disclaimer,
                chunking_strategy=self.config.CHUNKING_STRATEGY,
            )

            records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=doc.document_id,
                    chunk_index=idx,
                    content=content,
                    content_hash=content_hash,
                    metadata=metadata,
                )
            )

        return records
