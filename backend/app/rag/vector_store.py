"""
ManuMind AI — RAG ChromaDB Vector Store
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import numpy as np
import chromadb
from chromadb.config import Settings

from backend.app.rag.config import rag_config
from backend.app.rag.embedding_segment_schemas import EmbeddingSegment


class ChromaVectorStore:
    """
    Persistent ChromaDB vector index manager for BGE-small embeddings.
    Enforces cosine distance, explicit vectors, rich metadata, and idempotent indexing.
    """

    DEFAULT_PERSIST_DIR: Path = rag_config.BASE_DIR / "knowledge_base" / "index" / "chroma_bge_small_v1"
    COLLECTION_NAME: str = "manumind_bge_small_v1"
    DISTANCE_METRIC: str = "cosine"

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: str = COLLECTION_NAME,
    ):
        self.persist_dir = Path(persist_dir or self.DEFAULT_PERSIST_DIR).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.client_settings = Settings(
            is_persistent=True,
            persist_directory=str(self.persist_dir),
            anonymized_telemetry=False,
        )
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=self.client_settings,
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": self.DISTANCE_METRIC},
        )

    @property
    def client(self) -> chromadb.PersistentClient:
        """Access underlying PersistentClient."""
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        """Access underlying collection."""
        return self._collection

    def count(self) -> int:
        """Return total vectors currently indexed in the collection."""
        return self._collection.count()

    def index_segments(
        self,
        segments: List[EmbeddingSegment],
        embeddings: np.ndarray,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index embedding segments and their pre-computed dense embeddings idempotently.
        Prevents duplicate vector records, detects changed content, and records metrics.
        """
        start_time = time.perf_counter()
        if len(segments) != len(embeddings):
            raise ValueError(
                f"Mismatch between segments count ({len(segments)}) and embeddings count ({len(embeddings)})"
            )

        if len(embeddings.shape) != 2 or embeddings.shape[1] != 384:
            raise ValueError(
                f"Invalid embedding dimension: expected 384, got shape {embeddings.shape}"
            )

        total_records = len(segments)
        newly_inserted = 0
        updated = 0
        unchanged_skipped = 0

        # Query existing IDs and content hashes to enforce idempotency
        existing_ids = set()
        existing_hashes = {}
        if self._collection.count() > 0:
            existing_data = self._collection.get(include=["metadatas"])
            for eid, meta in zip(existing_data["ids"], existing_data["metadatas"]):
                existing_ids.add(eid)
                if meta and "content_hash" in meta:
                    existing_hashes[eid] = meta["content_hash"]

        # Process in batches
        for i in range(0, total_records, batch_size):
            batch_segs = segments[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]

            add_ids: List[str] = []
            add_embs: List[List[float]] = []
            add_docs: List[str] = []
            add_metas: List[Dict[str, Any]] = []

            for seg, emb in zip(batch_segs, batch_embs):
                sid = seg.embedding_segment_id
                c_hash = seg.content_hash

                if sid in existing_ids:
                    # Check if content has changed
                    if existing_hashes.get(sid) == c_hash:
                        unchanged_skipped += 1
                        continue
                    else:
                        updated += 1
                else:
                    newly_inserted += 1

                # Build flat metadata dictionary compliant with ChromaDB types (str, int, float, bool)
                m = seg.metadata
                meta_dict: Dict[str, Any] = {
                    "parent_chunk_id": m.parent_chunk_id,
                    "document_id": m.document_id,
                    "segment_index": m.segment_index,
                    "segment_count": m.segment_count,
                    "token_count_actual": m.token_count_actual,
                    "machine_id": m.machine_id or "NONE",
                    "source_record_id": m.source_record_id or "NONE",
                    "original_row_index": m.original_row_index if m.original_row_index is not None else -1,
                    "event_date": m.event_date or "NONE",
                    "source_type": m.source_type,
                    "is_synthetic": m.is_synthetic,
                    "category": m.category,
                    "section_heading": m.section_heading,
                    "parent_heading": m.parent_heading or "NONE",
                    "source_path": m.source_path,
                    "raw_file_hash": m.raw_file_hash,
                    "content_hash": m.content_hash,
                    "is_safety_related": m.is_safety_related,
                    "contains_spec_placeholder": m.contains_spec_placeholder,
                    "contains_synthetic_disclaimer": m.contains_synthetic_disclaimer,
                    "chunking_strategy": m.chunking_strategy,
                    "embedding_model": m.embedding_model,
                }

                add_ids.append(sid)
                add_embs.append(emb.tolist())
                add_docs.append(seg.content)
                add_metas.append(meta_dict)

            if add_ids:
                # Use upsert for idempotency
                self._collection.upsert(
                    ids=add_ids,
                    embeddings=add_embs,
                    documents=add_docs,
                    metadatas=add_metas,
                )

        duration = time.perf_counter() - start_time

        return {
            "total_segments_processed": total_records,
            "newly_inserted": newly_inserted,
            "updated": updated,
            "unchanged_skipped": unchanged_skipped,
            "final_collection_count": self._collection.count(),
            "duration_seconds": round(duration, 4),
        }

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return diagnostic statistics about the ChromaDB index."""
        count = self._collection.count()
        sample_meta = {}
        sample_id = None
        if count > 0:
            sample = self._collection.get(limit=1, include=["metadatas"])
            if sample["ids"]:
                sample_id = sample["ids"][0]
                sample_meta = sample["metadatas"][0] if sample["metadatas"] else {}

        return {
            "collection_name": self.collection_name,
            "persistence_directory": str(self.persist_dir),
            "distance_metric": self.DISTANCE_METRIC,
            "total_vectors": count,
            "sample_record_id": sample_id,
            "sample_metadata": sample_meta,
        }

    def verify_persistence(self) -> bool:
        """Verify index persistence by reopening in a new PersistentClient instance."""
        initial_count = self._collection.count()
        # Cleanly close and reopen new client
        reopened_client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=self.client_settings,
        )
        reopened_collection = reopened_client.get_collection(self.collection_name)
        reopened_count = reopened_collection.count()
        return initial_count == reopened_count and reopened_count > 0

    def search(
        self,
        query_embedding: Any,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute vector similarity search using explicit query embedding.
        Returns ChromaDB query output dictionary (ids, documents, metadatas, distances).
        """
        if isinstance(query_embedding, np.ndarray):
            if query_embedding.ndim == 1:
                emb_list = query_embedding.tolist()
            elif query_embedding.ndim == 2 and query_embedding.shape[0] == 1:
                emb_list = query_embedding[0].tolist()
            else:
                raise ValueError(f"Expected 1D query vector of length 384, got shape {query_embedding.shape}")
        else:
            emb_list = list(query_embedding)

        if len(emb_list) != 384:
            raise ValueError(f"Expected query vector dimension 384, got {len(emb_list)}")

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [emb_list],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        return self._collection.query(**query_kwargs)


# Singleton instance
chroma_vector_store = ChromaVectorStore()
