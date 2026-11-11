"""
ManuMind AI — RAG Embedding & Indexing Pipeline Service
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.rag.chunk_schemas import ChunkRecord
from backend.app.rag.chunking_service import ChunkingService
from backend.app.rag.embedding_model import BGEEmbeddingModel, bge_embedding_model
from backend.app.rag.embedding_segment_schemas import EmbeddingSegment, SegmentationSummary
from backend.app.rag.embedding_segmenter import EmbeddingSegmenter, embedding_segmenter
from backend.app.rag.schemas import ExecutionMode
from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service
from backend.app.rag.vector_store import ChromaVectorStore, chroma_vector_store


class EmbeddingService:
    """
    High-level orchestrator coordinating BGE tokenizer verification, segment generation,
    CPU embedding computation, and persistent ChromaDB vector indexing.
    """

    def __init__(
        self,
        tokenizer_svc: Optional[TokenizerService] = None,
        segmenter: Optional[EmbeddingSegmenter] = None,
        embedding_model: Optional[BGEEmbeddingModel] = None,
        vector_store: Optional[ChromaVectorStore] = None,
        chunking_svc: Optional[ChunkingService] = None,
    ):
        self.tokenizer = tokenizer_svc or tokenizer_service
        self.segmenter = segmenter or embedding_segmenter
        self.model = embedding_model or bge_embedding_model
        self.vector_store = vector_store or chroma_vector_store
        self.chunking_svc = chunking_svc or ChunkingService()

    def run_pipeline(
        self,
        chunks: Optional[List[ChunkRecord]] = None,
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """
        Execute the complete embedding and vector database indexing pipeline.
        1. Segments canonical chunks (preserving parent-chunk lineage).
        2. Generates 384-dimensional BGE embeddings on CPU.
        3. Indexes segments into persistent ChromaDB collection.
        4. Verifies index persistence and returns quantitative audit metrics.
        """
        overall_start = time.perf_counter()

        # 1. Obtain canonical chunks
        if chunks is None:
            self.chunking_svc.chunk_corpus(execution_mode=ExecutionMode.VALIDATION_ONLY)
            canonical_chunks = []
            docs = list(self.chunking_svc.ingestion_service.registry.values())
            for d in sorted(docs, key=lambda x: x.document_id):
                canonical_chunks.extend(self.chunking_svc.chunk_document(d))
        else:
            canonical_chunks = chunks

        # 2. Embedding-specific segmentation
        seg_start = time.perf_counter()
        segments, seg_summary = self.segmenter.segment_corpus(canonical_chunks)
        seg_duration = time.perf_counter() - seg_start

        # 3. CPU dense embedding generation
        emb_start = time.perf_counter()
        texts_to_embed = [s.content for s in segments]
        embeddings = self.model.embed_texts(texts_to_embed, batch_size=batch_size, normalize=True)
        emb_duration = time.perf_counter() - emb_start

        # Verify embedding outputs
        if len(embeddings) != len(segments):
            raise RuntimeError(f"Embedding count ({len(embeddings)}) mismatch with segments ({len(segments)})")
        if embeddings.shape[1] != 384:
            raise RuntimeError(f"Unexpected embedding dimension: {embeddings.shape[1]}")

        throughput_embs_per_sec = round(len(segments) / max(0.001, emb_duration), 2)

        # 4. ChromaDB vector indexing
        index_start = time.perf_counter()
        index_results = self.vector_store.index_segments(segments, embeddings, batch_size=100)
        index_duration = time.perf_counter() - index_start

        # 5. Verify persistence
        persistence_verified = self.vector_store.verify_persistence()
        overall_duration = time.perf_counter() - overall_start

        return {
            "status": "SUCCESS",
            "pipeline_milestone": "Phase 3 Step 4 — Embedding Generation and Vector Database Indexing",
            "model_name": self.model.MODEL_NAME,
            "revision_hash": self.model.REVISION_COMMIT_HASH,
            "embedding_dimension": self.model.EMBEDDING_DIM,
            "total_canonical_chunks": len(canonical_chunks),
            "total_segments_generated": len(segments),
            "chunks_segmented_count": seg_summary.chunks_segmented_count,
            "max_segment_tokens": seg_summary.max_token_count,
            "mean_segment_tokens": seg_summary.mean_token_count,
            "median_segment_tokens": seg_summary.median_token_count,
            "segments_above_effective_limit": seg_summary.segments_above_effective_limit,
            "empty_segments_count": seg_summary.empty_segments_count,
            "embedding_duration_seconds": round(emb_duration, 4),
            "embedding_throughput_per_sec": throughput_embs_per_sec,
            "indexing_results": index_results,
            "persistence_verified": persistence_verified,
            "total_pipeline_duration_seconds": round(overall_duration, 4),
            "segmentation_summary": seg_summary.model_dump(),
        }


# Singleton instance
embedding_service = EmbeddingService()
