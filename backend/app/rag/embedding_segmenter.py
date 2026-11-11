"""
ManuMind AI — RAG Embedding Segmenter
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

import hashlib
import re
import statistics
import time
from typing import List, Optional, Tuple

from backend.app.rag.chunk_schemas import ChunkRecord
from backend.app.rag.embedding_segment_schemas import (
    EmbeddingSegment,
    EmbeddingSegmentMetadata,
    SegmentationSummary,
)
from backend.app.rag.ingestion_service import IngestionService
from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service


class EmbeddingSegmenter:
    """
    Dedicated segmentation service that prepares canonical Step 3 chunks for embedding.
    Ensures zero silent truncation by splitting any oversized chunks across paragraph/sentence boundaries
    while preserving parent-chunk lineage, incident traceability, and safety context.
    """

    def __init__(
        self,
        tokenizer_svc: Optional[TokenizerService] = None,
        max_segment_tokens: int = 500,  # Safe effective budget below 512
    ):
        self.tokenizer = tokenizer_svc or tokenizer_service
        self.max_segment_tokens = max_segment_tokens

    def segment_chunk(self, chunk: ChunkRecord) -> List[EmbeddingSegment]:
        """
        Segment a single canonical ChunkRecord into one or more EmbeddingSegment objects.
        If actual BGE token count fits within max_segment_tokens, keeps chunk intact (1:1).
        """
        content = chunk.content.strip()
        actual_tokens_with_special = self.tokenizer.count_tokens(content, add_special_tokens=True)

        # 1. Nominal path: chunk fits within safe effective budget
        if actual_tokens_with_special <= self.max_segment_tokens:
            norm_content = IngestionService.normalize_content(content)
            content_hash = hashlib.sha256(norm_content.encode("utf-8")).hexdigest()

            meta = EmbeddingSegmentMetadata(
                parent_chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                segment_index=0,
                segment_count=1,
                token_count_actual=actual_tokens_with_special,
                machine_id=chunk.metadata.machine_id,
                source_record_id=chunk.metadata.source_record_id,
                original_row_index=chunk.metadata.original_row_index,
                event_date=chunk.metadata.event_date,
                source_type=chunk.metadata.source_type,
                is_synthetic=chunk.metadata.is_synthetic,
                category=chunk.metadata.category,
                section_heading=chunk.metadata.section_heading,
                parent_heading=chunk.metadata.parent_heading,
                source_path=chunk.metadata.source_path,
                raw_file_hash=chunk.metadata.raw_file_hash,
                content_hash=content_hash,
                is_safety_related=chunk.metadata.is_safety_related,
                contains_spec_placeholder=chunk.metadata.contains_spec_placeholder,
                contains_synthetic_disclaimer=chunk.metadata.contains_synthetic_disclaimer,
                chunking_strategy=chunk.metadata.chunking_strategy,
                embedding_model=self.tokenizer.model_name,
            )

            return [
                EmbeddingSegment(
                    embedding_segment_id=f"{chunk.chunk_id}_seg000",
                    parent_chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    segment_index=0,
                    content=content,
                    content_hash=content_hash,
                    token_count=actual_tokens_with_special,
                    metadata=meta,
                )
            ]

        # 2. Oversized path: structural splitting along paragraphs and sentences
        raw_sub_texts = self._split_oversized_chunk_content(chunk)
        segment_count = len(raw_sub_texts)
        segments: List[EmbeddingSegment] = []

        for idx, sub_text in enumerate(raw_sub_texts):
            clean_sub = sub_text.strip()
            norm_sub = IngestionService.normalize_content(clean_sub)
            sub_hash = hashlib.sha256(norm_sub.encode("utf-8")).hexdigest()
            sub_tokens = self.tokenizer.count_tokens(clean_sub, add_special_tokens=True)

            has_placeholder = "[SPEC_REQUIRED:" in clean_sub
            upper_sub = clean_sub.upper()
            has_disclaimer = "SYNTHETIC DEMONSTRATION MATERIAL" in upper_sub

            sub_meta = EmbeddingSegmentMetadata(
                parent_chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                segment_index=idx,
                segment_count=segment_count,
                token_count_actual=sub_tokens,
                machine_id=chunk.metadata.machine_id,
                source_record_id=chunk.metadata.source_record_id,
                original_row_index=chunk.metadata.original_row_index,
                event_date=chunk.metadata.event_date,
                source_type=chunk.metadata.source_type,
                is_synthetic=chunk.metadata.is_synthetic,
                category=chunk.metadata.category,
                section_heading=f"{chunk.metadata.section_heading} (Part {idx+1}/{segment_count})",
                parent_heading=chunk.metadata.parent_heading,
                source_path=chunk.metadata.source_path,
                raw_file_hash=chunk.metadata.raw_file_hash,
                content_hash=sub_hash,
                is_safety_related=chunk.metadata.is_safety_related or has_placeholder,
                contains_spec_placeholder=has_placeholder,
                contains_synthetic_disclaimer=has_disclaimer,
                chunking_strategy="embedding_segmentation_v1",
                embedding_model=self.tokenizer.model_name,
            )

            segments.append(
                EmbeddingSegment(
                    embedding_segment_id=f"{chunk.chunk_id}_seg{idx:03d}",
                    parent_chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    segment_index=idx,
                    content=clean_sub,
                    content_hash=sub_hash,
                    token_count=sub_tokens,
                    metadata=sub_meta,
                )
            )

        return segments

    def _split_oversized_chunk_content(self, chunk: ChunkRecord) -> List[str]:
        """
        Split an oversized chunk along Markdown section/paragraph/sentence boundaries.
        Prepends heading context to subsequent segments to maintain semantic grounding.
        """
        lines = chunk.content.splitlines()
        header_prefix = ""
        body_text = chunk.content

        # Capture top-level heading if present
        if lines and lines[0].startswith("## "):
            header_prefix = lines[0] + "\n\n"
            body_text = "\n".join(lines[1:]).strip()

        if not body_text:
            return [chunk.content.strip()]

        paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
        sub_chunks: List[str] = []
        current_paras: List[str] = []

        budget = self.max_segment_tokens - 10  # safety margin

        for p_strip in paragraphs:
            candidate = "\n\n".join(current_paras + [p_strip])
            candidate_with_hdr = f"{header_prefix}{candidate}".strip() if header_prefix else candidate

            c_tokens = self.tokenizer.count_tokens(candidate_with_hdr, add_special_tokens=True)

            if c_tokens <= budget:
                current_paras.append(p_strip)
            else:
                p_with_hdr = f"{header_prefix}{p_strip}".strip() if header_prefix else p_strip
                p_tokens = self.tokenizer.count_tokens(p_with_hdr, add_special_tokens=True)

                if p_tokens > budget:
                    # Flush current buffer first
                    if current_paras:
                        text_to_add = f"{header_prefix}{chr(10).join(current_paras)}".strip() if header_prefix else "\n\n".join(current_paras).strip()
                        sub_chunks.append(text_to_add)
                        current_paras = []

                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p_strip) if s.strip()]
                    current_sents: List[str] = []
                    for s in sentences:
                        s_candidate = " ".join(current_sents + [s])
                        s_with_hdr = f"{header_prefix}{s_candidate}".strip() if header_prefix else s_candidate
                        if self.tokenizer.count_tokens(s_with_hdr, add_special_tokens=True) <= budget:
                            current_sents.append(s)
                        else:
                            if current_sents:
                                text_seg = f"{header_prefix}{' '.join(current_sents)}".strip() if header_prefix else " ".join(current_sents).strip()
                                sub_chunks.append(text_seg)
                            current_sents = [s]
                    if current_sents:
                        text_seg = f"{header_prefix}{' '.join(current_sents)}".strip() if header_prefix else " ".join(current_sents).strip()
                        sub_chunks.append(text_seg)
                else:
                    if current_paras:
                        text_to_add = f"{header_prefix}{chr(10).join(current_paras)}".strip() if header_prefix else "\n\n".join(current_paras).strip()
                        sub_chunks.append(text_to_add)
                    current_paras = [p_strip]

        if current_paras:
            text_to_add = f"{header_prefix}{chr(10).join(current_paras)}".strip() if header_prefix else "\n\n".join(current_paras).strip()
            sub_chunks.append(text_to_add)

        return sub_chunks

    def segment_corpus(self, chunks: List[ChunkRecord]) -> Tuple[List[EmbeddingSegment], SegmentationSummary]:
        """
        Segment a list of canonical ChunkRecord objects.
        Returns all generated EmbeddingSegment instances and a quantitative summary.
        """
        start_time = time.perf_counter()
        all_segments: List[EmbeddingSegment] = []
        chunks_segmented_count = 0
        warnings: List[str] = []
        errors: List[str] = []

        for chunk in chunks:
            segs = self.segment_chunk(chunk)
            if len(segs) > 1:
                chunks_segmented_count += 1
            all_segments.extend(segs)

        # Quantitative metrics
        total_segs = len(all_segments)
        token_counts = [s.token_count for s in all_segments]
        min_tokens = min(token_counts) if token_counts else 0
        max_tokens = max(token_counts) if token_counts else 0
        mean_tokens = round(statistics.mean(token_counts), 2) if token_counts else 0.0
        median_tokens = round(statistics.median(token_counts), 2) if token_counts else 0.0

        segs_above_limit = sum(1 for s in all_segments if s.token_count > self.tokenizer.model_max_length)
        empty_segs = sum(1 for s in all_segments if not s.content.strip())

        cat_counts = {}
        machine_counts = {}
        for s in all_segments:
            cat = s.metadata.category
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            if s.metadata.machine_id:
                mid = s.metadata.machine_id
                machine_counts[mid] = machine_counts.get(mid, 0) + 1

        duration = time.perf_counter() - start_time

        summary = SegmentationSummary(
            total_canonical_chunks=len(chunks),
            total_segments_generated=total_segs,
            chunks_segmented_count=chunks_segmented_count,
            segments_per_category=cat_counts,
            segments_per_machine=machine_counts,
            min_token_count=min_tokens,
            max_token_count=max_tokens,
            mean_token_count=mean_tokens,
            median_token_count=median_tokens,
            segments_above_effective_limit=segs_above_limit,
            empty_segments_count=empty_segs,
            duration_seconds=round(duration, 4),
            warnings=warnings,
            errors=errors,
        )

        return all_segments, summary


# Singleton instance
embedding_segmenter = EmbeddingSegmenter()
