"""
ManuMind AI — Phase 3 Step 5: Retrieval Service Unit & Integration Tests
Tests for QueryProcessor, RetrievalService orchestration, distance-to-similarity conversion,
machine-constrained search, safety filtering, and incident lookup.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.query_processor import QueryProcessor, query_processor
from backend.app.rag.retrieval_config import retrieval_config
from backend.app.rag.retrieval_schemas import (
    RetrievalFilter,
    RetrievalMode,
    RetrievalQuery,
    RetrievalResponse,
)
from backend.app.rag.retrieval_service import RetrievalService, retrieval_service


class TestRAGRetrieval(unittest.TestCase):
    """Authoritative test suite for RetrievalService and QueryProcessor."""

    @classmethod
    def setUpClass(cls):
        # Service instance using production ChromaDB collection (read-only queries)
        cls.service = retrieval_service
        cls.processor = query_processor

    # --- QueryProcessor Tests ---

    def test_query_normalization_whitespace(self):
        """QueryProcessor collapses extraneous whitespace and trims strings."""
        raw = "   M104    spindle   bearing   wear   "
        proc = self.processor.process_query(raw)
        self.assertEqual(proc.normalized_query, "M104 spindle bearing wear")
        self.assertEqual(proc.extracted_machine_id, "M104")
        self.assertEqual(proc.detected_machine_ids, ["M104"])
        self.assertFalse(proc.has_conflicting_machines)

    def test_query_processor_bge_prefix(self):
        """QueryProcessor prepends official BGE search instruction prefix."""
        proc = self.processor.process_query("Bearing vibration analysis", apply_bge_prefix=True)
        self.assertTrue(proc.prefix_applied)
        self.assertTrue(proc.embedding_query.startswith("Represent this sentence for searching relevant passages: "))
        self.assertIn("Bearing vibration analysis", proc.embedding_query)

    def test_query_processor_multiple_machines(self):
        """QueryProcessor flags conflicting machines and does not select a single extracted machine."""
        proc = self.processor.process_query("Compare M101 and M105 temperature spikes")
        self.assertEqual(proc.detected_machine_ids, ["M101", "M105"])
        self.assertTrue(proc.has_conflicting_machines)
        self.assertIsNone(proc.extracted_machine_id)

    def test_query_processor_empty_rejection(self):
        """Empty or whitespace-only queries are rejected with ValueError."""
        for invalid in ["", "   ", "\t\n"]:
            with self.assertRaises(ValueError):
                self.processor.process_query(invalid)

    def test_query_processor_length_bounds(self):
        """Queries shorter than 2 chars or exceeding 2000 chars are rejected."""
        with self.assertRaises(ValueError):
            self.processor.process_query("a")
        with self.assertRaises(ValueError):
            self.processor.process_query("x" * 2001)

    # --- RetrievalService Tests ---

    def test_retrieval_top_k_clamping(self):
        """top_k is safely clamped between MIN_TOP_K (1) and MAX_TOP_K (20)."""
        res_low = self.service.retrieve("spindle lubrication", top_k=0)
        self.assertEqual(res_low.requested_top_k, 1)

        res_high = self.service.retrieve("spindle lubrication", top_k=50)
        self.assertEqual(res_high.requested_top_k, 20)

    def test_retrieval_distance_to_similarity_conversion(self):
        """Derived similarity is 1.0 - raw_distance and strictly within [0.0, 1.0]."""
        response = self.service.retrieve("M101 spindle vibration troubleshooting", top_k=5)
        self.assertGreater(response.returned_count, 0)

        for item in response.results:
            self.assertGreaterEqual(item.similarity_score, 0.0)
            self.assertLessEqual(item.similarity_score, 1.0)
            expected_sim = round(max(0.0, min(1.0, 1.0 - item.raw_distance)), 6)
            self.assertAlmostEqual(item.similarity_score, expected_sim, places=5)

    def test_retrieval_ranking_order(self):
        """Results are returned in strictly descending similarity score order."""
        response = self.service.retrieve("hydraulic pressure relief valve maintenance", top_k=5)
        self.assertGreater(response.returned_count, 1)

        scores = [item.similarity_score for item in response.results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_retrieval_provenance_verification(self):
        """All retrieved production results pass provenance verification."""
        response = self.service.retrieve("M104 spindle motor bearing SOP", top_k=5)
        self.assertGreater(response.returned_count, 0)

        for item in response.results:
            self.assertTrue(item.provenance_validated)
            self.assertEqual(item.provenance_details, "Provenance verified successfully")
            self.assertEqual(len(item.content_hash), 64)
            self.assertEqual(len(item.raw_file_hash), 64)

    def test_machine_specific_convenience_method(self):
        """retrieve_machine_specific restricts results strictly to target machine and global assets."""
        response = self.service.retrieve_machine_specific(
            query_text="daily startup inspection checklist",
            machine_id="M103",
            top_k=5,
        )
        self.assertEqual(response.retrieval_mode, RetrievalMode.MACHINE_SPECIFIC.value)
        self.assertGreater(response.returned_count, 0)

        for item in response.results:
            # Result machine_id must either be M103 or None (plant-wide global document)
            self.assertIn(item.machine_id, ["M103", None])

    def test_safety_procedures_convenience_method(self):
        """retrieve_safety_procedures retrieves strictly safety-related documents."""
        response = self.service.retrieve_safety_procedures(
            query_text="lockout tagout electrical hazard PPE requirements",
            top_k=5,
        )
        self.assertGreater(response.returned_count, 0)
        for item in response.results:
            self.assertTrue(item.is_safety_related)

    def test_historical_incidents_convenience_method(self):
        """retrieve_historical_incidents retrieves records strictly from INCIDENT category."""
        response = self.service.retrieve_historical_incidents(
            query_text="coolant leak pump seal failure",
            machine_id="M101",
            top_k=5,
        )
        self.assertGreater(response.returned_count, 0)
        for item in response.results:
            self.assertEqual(item.category, "INCIDENT")
            self.assertEqual(item.machine_id, "M101")
            self.assertTrue(item.source_record_id.startswith("ROW-"))
            self.assertIsNotNone(item.original_row_index)
            self.assertGreaterEqual(item.original_row_index, 1)
            self.assertLessEqual(item.original_row_index, 400)

    def test_min_similarity_cutoff(self):
        """min_similarity cutoff filters out low-scoring results."""
        # Query with high similarity threshold
        response = self.service.retrieve(
            query="spindle bearing wear",
            top_k=10,
            min_similarity=0.95,
        )
        # Any result returned must meet the threshold
        for item in response.results:
            self.assertGreaterEqual(item.similarity_score, 0.95)

    def test_document_diversification(self):
        """Diversification limits the number of segments from any single document."""
        response = self.service.retrieve(
            query="hydraulic pressure pump cavitation",
            top_k=6,
            diversify_documents=True,
        )
        doc_counts = {}
        for item in response.results:
            doc_counts[item.document_id] = doc_counts.get(item.document_id, 0) + 1

        for doc_id, count in doc_counts.items():
            self.assertLessEqual(
                count,
                retrieval_config.DEFAULT_MAX_SEGMENTS_PER_DOC,
                f"Document {doc_id} appeared {count} times (max allowed: {retrieval_config.DEFAULT_MAX_SEGMENTS_PER_DOC})",
            )


if __name__ == "__main__":
    unittest.main()
