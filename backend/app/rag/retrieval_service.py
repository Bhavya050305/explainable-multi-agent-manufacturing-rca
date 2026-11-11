"""
ManuMind AI — RAG Retrieval Service
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import time
from typing import Any, Dict, List, Optional, Union
import numpy as np

from backend.app.rag.embedding_model import BGEEmbeddingModel
from backend.app.rag.metadata_filter import MetadataFilterCompiler, metadata_filter_compiler
from backend.app.rag.query_processor import QueryProcessor, query_processor
from backend.app.rag.retrieval_config import RetrievalConfig, retrieval_config
from backend.app.rag.retrieval_schemas import (
    RetrievalFilter,
    RetrievalMode,
    RetrievalQuery,
    RetrievalResponse,
    RetrievalResultItem,
)
from backend.app.rag.source_resolver import SourceResolver, source_resolver
from backend.app.rag.vector_store import ChromaVectorStore, chroma_vector_store


class RetrievalService:
    """
    Orchestrates query processing, dense BGE embedding inference, metadata-filtered
    vector search, score derivation, and provenance validation.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_model: Optional[BGEEmbeddingModel] = None,
        processor: Optional[QueryProcessor] = None,
        filter_compiler: Optional[MetadataFilterCompiler] = None,
        resolver: Optional[SourceResolver] = None,
        config: RetrievalConfig = retrieval_config,
    ):
        self.vector_store = vector_store or chroma_vector_store
        self._embedding_model = embedding_model
        self.query_processor = processor or query_processor
        self.filter_compiler = filter_compiler or metadata_filter_compiler
        self.source_resolver = resolver or source_resolver
        self.config = config

    @property
    def embedding_model(self) -> BGEEmbeddingModel:
        """Lazy initialization of CPU embedding model."""
        if self._embedding_model is None:
            self._embedding_model = BGEEmbeddingModel()
        return self._embedding_model

    def retrieve(
        self,
        query: Union[str, RetrievalQuery],
        filter: Optional[RetrievalFilter] = None,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[RetrievalMode] = None,
        min_similarity: Optional[float] = None,
        diversify_documents: bool = False,
    ) -> RetrievalResponse:
        """
        Execute semantic retrieval against the ChromaDB vector index.
        Args:
            query: Raw query string or validated RetrievalQuery model.
            filter: Optional metadata filtering criteria.
            top_k: Number of results to return (default: 5, max: 20).
            retrieval_mode: Explicit mode override (e.g. machine_specific, cross_machine).
            min_similarity: Optional minimum derived similarity cutoff [0.0, 1.0].
            diversify_documents: Limit segments from the same document.
        Returns:
            RetrievalResponse with ranked, provenance-verified results.
        """
        start_overall = time.perf_counter()

        # Enforce top_k boundaries early
        if top_k is not None:
            clamped_k = max(self.config.MIN_TOP_K, min(top_k, self.config.MAX_TOP_K))
        else:
            clamped_k = self.config.DEFAULT_TOP_K

        # 1. Parse and validate query model
        if isinstance(query, str):
            query_obj = RetrievalQuery(
                query_text=query,
                filter=filter,
                top_k=clamped_k,
                retrieval_mode=retrieval_mode,
                min_similarity=min_similarity,
                diversify_documents=diversify_documents,
            )
        else:
            query_obj = query
            if filter:
                query_obj.filter = filter
            if top_k is not None:
                query_obj.top_k = clamped_k
            if retrieval_mode is not None:
                query_obj.retrieval_mode = retrieval_mode
            if min_similarity is not None:
                query_obj.min_similarity = min_similarity

        effective_top_k = query_obj.top_k

        # 2. Process query text
        processed = self.query_processor.process_query(query_obj.query_text)

        # 3. Compile ChromaDB where clause
        where_filter, effective_mode = self.filter_compiler.compile_filter(
            filter_spec=query_obj.filter,
            extracted_machine_id=processed.extracted_machine_id,
            mode_override=query_obj.retrieval_mode,
        )

        # 4. Generate dense query embedding on CPU
        start_emb = time.perf_counter()
        query_vector = self.embedding_model.embed_single(
            processed.embedding_query,
            normalize=True,
        )
        emb_latency = time.perf_counter() - start_emb

        # 5. ChromaDB vector search
        start_search = time.perf_counter()
        search_top_k = (
            min(self.vector_store._collection.count(), effective_top_k * 3)
            if query_obj.diversify_documents
            else effective_top_k
        )
        search_top_k = max(1, search_top_k)

        raw_results = self.vector_store.search(
            query_embedding=query_vector,
            top_k=search_top_k,
            where_filter=where_filter,
        )
        search_latency = time.perf_counter() - start_search

        # 6. Result ranking, score derivation, and provenance resolution
        start_res = time.perf_counter()
        results: List[RetrievalResultItem] = []

        ids = raw_results.get("ids", [[]])[0]
        docs = raw_results.get("documents", [[]])[0]
        metas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        doc_segment_counts: Dict[str, int] = {}

        for sid, content, meta, dist in zip(ids, docs, metas, distances):
            doc_id = meta.get("document_id", "UNKNOWN")

            # Document diversification check
            if query_obj.diversify_documents:
                count = doc_segment_counts.get(doc_id, 0)
                if count >= self.config.DEFAULT_MAX_SEGMENTS_PER_DOC:
                    continue
                doc_segment_counts[doc_id] = count + 1

            # Cosine distance to similarity: similarity = 1.0 - distance
            # For unit-normalized vectors: cosine_dist = 1 - cosine_sim
            raw_dist_float = float(dist)
            derived_sim = max(0.0, min(1.0, 1.0 - raw_dist_float))

            # Apply optional minimum similarity cutoff
            if query_obj.min_similarity is not None and derived_sim < query_obj.min_similarity:
                continue

            # Provenance validation
            is_valid_prov, prov_msg = self.source_resolver.resolve_provenance(meta)

            # Clean null/empty string representations
            mach_id = meta.get("machine_id")
            if mach_id == "NONE":
                mach_id = None

            s_rec_id = meta.get("source_record_id")
            if s_rec_id == "NONE":
                s_rec_id = None

            row_idx = meta.get("original_row_index")
            if row_idx == -1:
                row_idx = None

            e_date = meta.get("event_date")
            if e_date == "NONE":
                e_date = None

            p_heading = meta.get("parent_heading")
            if p_heading == "NONE":
                p_heading = None

            item = RetrievalResultItem(
                rank=len(results) + 1,
                segment_id=sid,
                parent_chunk_id=meta.get("parent_chunk_id", sid.replace("_seg000", "")),
                document_id=doc_id,
                machine_id=mach_id,
                category=meta.get("category", "UNKNOWN"),
                source_type=meta.get("source_type", "UNKNOWN"),
                is_synthetic=bool(meta.get("is_synthetic", True)),
                is_safety_related=bool(meta.get("is_safety_related", False)),
                source_path=meta.get("source_path", "UNKNOWN"),
                source_record_id=s_rec_id,
                original_row_index=row_idx,
                event_date=e_date,
                section_heading=meta.get("section_heading", "General"),
                parent_heading=p_heading,
                raw_distance=round(raw_dist_float, 6),
                similarity_score=round(derived_sim, 6),
                content=content,
                content_hash=meta.get("content_hash", ""),
                raw_file_hash=meta.get("raw_file_hash", ""),
                provenance_validated=is_valid_prov,
                provenance_details=prov_msg,
            )
            results.append(item)

            if len(results) >= effective_top_k:
                break

        res_latency = time.perf_counter() - start_res
        total_duration = time.perf_counter() - start_overall

        return RetrievalResponse(
            query=query_obj.query_text,
            processed_query=processed.embedding_query,
            retrieval_mode=effective_mode.value,
            requested_top_k=effective_top_k,
            returned_count=len(results),
            results=results,
            applied_filters=where_filter or {},
            query_duration_seconds=round(total_duration, 4),
            embedding_latency_seconds=round(emb_latency, 4),
            search_latency_seconds=round(search_latency, 4),
            resolution_latency_seconds=round(res_latency, 4),
            embedding_model=f"{self.embedding_model.MODEL_NAME} ({self.embedding_model.REVISION_COMMIT_HASH})",
            collection_name=self.vector_store.collection_name,
        )

    # Specialized retrieval methods
    def retrieve_machine_specific(
        self,
        query_text: str,
        machine_id: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> RetrievalResponse:
        """Convenience method for machine-constrained retrieval."""
        filter_spec = RetrievalFilter(
            machine_id=machine_id,
            category=category,
            cross_machine=False,
            include_global=True,
        )
        return self.retrieve(query_text, filter=filter_spec, top_k=top_k)

    def retrieve_cross_machine(
        self,
        query_text: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> RetrievalResponse:
        """Convenience method for cross-machine retrieval."""
        filter_spec = RetrievalFilter(
            category=category,
            cross_machine=True,
        )
        return self.retrieve(query_text, filter=filter_spec, top_k=top_k)

    def retrieve_safety_procedures(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """Convenience method for safety-filtered retrieval."""
        filter_spec = RetrievalFilter(
            is_safety_related=True,
            cross_machine=True,
        )
        return self.retrieve(query_text, filter=filter_spec, top_k=top_k)

    def retrieve_historical_incidents(
        self,
        query_text: str,
        machine_id: Optional[str] = None,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """Convenience method for historical maintenance incident retrieval."""
        filter_spec = RetrievalFilter(
            category="INCIDENT",
            machine_id=machine_id,
            cross_machine=(machine_id is None),
        )
        return self.retrieve(query_text, filter=filter_spec, top_k=top_k)


retrieval_service = RetrievalService()
