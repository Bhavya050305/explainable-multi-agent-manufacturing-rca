"""
ManuMind AI — Phase 3 Step 4: RAG ChromaDB Vector Store Tests
Verifies persistent ChromaDB index creation, cosine distance configuration, explicit vector insertion,
metadata storage, idempotency, changed content detection, and persistence after reopen.

Department of AI & Data Science — RMK Engineering College
"""

import shutil
import sys
import tempfile
import unittest
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.embedding_segment_schemas import (
    EmbeddingSegment,
    EmbeddingSegmentMetadata,
)
from backend.app.rag.vector_store import ChromaVectorStore


class TestRAGVectorStore(unittest.TestCase):
    """Authoritative test suite for persistent ChromaDB vector store."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="manumind_chroma_test_")
        self.vector_store = ChromaVectorStore(
            persist_dir=Path(self.test_dir),
            collection_name="test_manumind_v1",
        )

    def tearDown(self):
        del self.vector_store
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_dummy_segment(
        self,
        seg_id: str = "DOC-TEST-001_chk000_seg000",
        doc_id: str = "DOC-TEST-001",
        machine_id: str = "M101",
        content: str = "Sample content for vector indexing test.",
        content_hash: str = "hash123",
        is_safety: bool = False,
    ) -> EmbeddingSegment:
        meta = EmbeddingSegmentMetadata(
            parent_chunk_id=f"{doc_id}_chk000",
            document_id=doc_id,
            segment_index=0,
            segment_count=1,
            token_count_actual=25,
            machine_id=machine_id,
            source_record_id="ROW-0001",
            original_row_index=1,
            event_date="2026-11-11 10:00:00",
            source_type="SYNTHETIC_DEMONSTRATION",
            is_synthetic=True,
            category="SOP",
            section_heading="Test Section",
            parent_heading="Parent SOP",
            source_path="knowledge_base/sops/test.md",
            raw_file_hash="rawfilehash123",
            content_hash=content_hash,
            is_safety_related=is_safety,
            contains_spec_placeholder=False,
            contains_synthetic_disclaimer=False,
            chunking_strategy="structural_markdown_v1",
            embedding_model="BAAI/bge-small-en-v1.5",
        )
        return EmbeddingSegment(
            embedding_segment_id=seg_id,
            parent_chunk_id=f"{doc_id}_chk000",
            document_id=doc_id,
            segment_index=0,
            content=content,
            content_hash=content_hash,
            token_count=25,
            metadata=meta,
        )

    def test_01_persistent_collection_creation(self):
        """Verify collection is created with correct name and distance metric."""
        stats = self.vector_store.get_collection_stats()
        self.assertEqual(stats["collection_name"], "test_manumind_v1")
        self.assertEqual(stats["distance_metric"], "cosine")
        self.assertEqual(stats["total_vectors"], 0)

    def test_02_explicit_vector_insertion(self):
        """Verify explicit dense vector insertion into ChromaDB."""
        seg = self._make_dummy_segment("SEG_001")
        emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)

        res = self.vector_store.index_segments([seg], emb)
        self.assertEqual(res["newly_inserted"], 1)
        self.assertEqual(self.vector_store.count(), 1)

    def test_03_correct_record_ids_and_metadata(self):
        """Verify indexed record contains expected ID and all required metadata fields."""
        seg = self._make_dummy_segment("SEG_002", doc_id="DOC-M102", machine_id="M102")
        emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)

        self.vector_store.index_segments([seg], emb)
        rec = self.vector_store.collection.get(ids=["SEG_002"], include=["metadatas", "documents"])

        self.assertEqual(len(rec["ids"]), 1)
        self.assertEqual(rec["ids"][0], "SEG_002")
        meta = rec["metadatas"][0]
        self.assertEqual(meta["machine_id"], "M102")
        self.assertEqual(meta["document_id"], "DOC-M102")
        self.assertEqual(meta["source_record_id"], "ROW-0001")
        self.assertEqual(meta["original_row_index"], 1)
        self.assertTrue(meta["is_synthetic"])

    def test_04_vector_dimension_validation(self):
        """Verify vector store rejects vector inputs with mismatched dimensions."""
        seg = self._make_dummy_segment("SEG_003")
        wrong_emb = np.ones((1, 128), dtype=np.float32)  # Wrong dimension (128 vs 384)

        # Indexing must fail or Chroma collection will reject wrong dim
        with self.assertRaises(Exception):
            self.vector_store.index_segments([seg], wrong_emb)

    def test_05_idempotent_insertion(self):
        """Verify inserting identical segments twice skips unchanged records without error."""
        seg = self._make_dummy_segment("SEG_004", content_hash="hash_v1")
        emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)

        # Run 1
        res1 = self.vector_store.index_segments([seg], emb)
        self.assertEqual(res1["newly_inserted"], 1)
        self.assertEqual(res1["unchanged_skipped"], 0)

        # Run 2 (identical)
        res2 = self.vector_store.index_segments([seg], emb)
        self.assertEqual(res2["newly_inserted"], 0)
        self.assertEqual(res2["unchanged_skipped"], 1)
        self.assertEqual(self.vector_store.count(), 1)

    def test_06_changed_content_detection(self):
        """Verify updating existing record ID with new content hash triggers an update."""
        seg1 = self._make_dummy_segment("SEG_005", content="Original content", content_hash="hash_orig")
        emb1 = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)
        self.vector_store.index_segments([seg1], emb1)

        # Update with changed content hash
        seg2 = self._make_dummy_segment("SEG_005", content="Updated content", content_hash="hash_updated")
        emb2 = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)
        res = self.vector_store.index_segments([seg2], emb2)

        self.assertEqual(res["updated"], 1)
        self.assertEqual(self.vector_store.count(), 1)
        # Verify content was updated
        rec = self.vector_store.collection.get(ids=["SEG_005"], include=["documents", "metadatas"])
        self.assertEqual(rec["documents"][0], "Updated content")
        self.assertEqual(rec["metadatas"][0]["content_hash"], "hash_updated")

    def test_07_persistence_after_reopen(self):
        """Verify data persists when PersistentClient is closed and reopened."""
        seg = self._make_dummy_segment("SEG_PERSIST")
        emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)
        self.vector_store.index_segments([seg], emb)

        self.assertTrue(self.vector_store.verify_persistence())

    def test_08_metadata_filtering(self):
        """Verify querying with metadata filter ($and, $eq) returns exact target subset."""
        seg_m101 = self._make_dummy_segment("SEG_M101", machine_id="M101", is_safety=True)
        seg_m102 = self._make_dummy_segment("SEG_M102", machine_id="M102", is_safety=False)

        emb = np.ones((2, 384), dtype=np.float32) / np.sqrt(384)
        self.vector_store.index_segments([seg_m101, seg_m102], emb)

        # Query filtered by machine_id == M101
        res = self.vector_store.collection.get(where={"machine_id": "M101"})
        self.assertEqual(res["ids"], ["SEG_M101"])

        # Query filtered by is_safety_related == True
        res_safety = self.vector_store.collection.get(where={"is_safety_related": True})
        self.assertEqual(res_safety["ids"], ["SEG_M101"])

    def test_09_empty_collection_handling(self):
        """Verify safe operations on an empty collection."""
        self.assertEqual(self.vector_store.count(), 0)
        res = self.vector_store.get_collection_stats()
        self.assertEqual(res["total_vectors"], 0)
        self.assertIsNone(res["sample_record_id"])

    def test_10_batch_insertion_ordering(self):
        """Verify multi-record batch insertion maintains record IDs and count."""
        segs = [self._make_dummy_segment(f"SEG_BATCH_{i:03d}") for i in range(15)]
        embs = np.ones((15, 384), dtype=np.float32) / np.sqrt(384)

        res = self.vector_store.index_segments(segs, embs, batch_size=5)
        self.assertEqual(res["newly_inserted"], 15)
        self.assertEqual(self.vector_store.count(), 15)

    def test_11_none_metadata_safety(self):
        """Verify fields with None values (such as machine_id) are serialized safely without Chroma crash."""
        seg = self._make_dummy_segment("SEG_NONE_META", machine_id=None)
        emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)

        self.vector_store.index_segments([seg], emb)
        rec = self.vector_store.collection.get(ids=["SEG_NONE_META"], include=["metadatas"])
        self.assertEqual(rec["metadatas"][0]["machine_id"], "NONE")

    def test_12_isolation_from_production_index(self):
        """Verify test instance uses independent temporary directory and does not pollute production directory."""
        self.assertNotEqual(str(self.vector_store.persist_dir), str(ChromaVectorStore.DEFAULT_PERSIST_DIR))
        self.assertTrue(str(self.vector_store.persist_dir).startswith(self.test_dir))


if __name__ == "__main__":
    unittest.main()
