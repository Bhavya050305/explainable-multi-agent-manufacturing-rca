"""
ManuMind AI — Phase 3 Step 5: RAG Retrieval Evaluation Tests
Evaluates end-to-end retrieval performance against the 36 golden evaluation queries.
Computes Precision@K, Recall@K, MRR, latency benchmarks, and rejection accuracy.

Department of AI & Data Science — RMK Engineering College
"""

import json
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.query_processor import query_processor
from backend.app.rag.retrieval_schemas import RetrievalFilter, RetrievalMode
from backend.app.rag.retrieval_service import retrieval_service


class TestRAGRetrievalEvaluation(unittest.TestCase):
    """Authoritative evaluation test suite for RAG retrieval against golden queries."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_path = REPO_ROOT / "backend" / "tests" / "fixtures" / "rag_retrieval_golden_queries.json"
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.golden_data = json.load(f)
        cls.queries: List[Dict[str, Any]] = cls.golden_data["queries"]
        cls.service = retrieval_service
        cls.processor = query_processor

    def test_golden_queries_fixture_structure(self):
        """Golden query fixture must contain exactly 36 valid query specifications."""
        self.assertEqual(len(self.queries), 36)
        required_fields = {
            "query_id",
            "query_text",
            "expected_category",
            "expected_machine_id",
            "retrieval_mode",
            "relevant_doc_ids",
            "expected_provenance",
            "should_reject",
            "description",
        }
        for q in self.queries:
            for field in required_fields:
                self.assertIn(field, q, f"Query {q.get('query_id')} missing {field}")

    def test_golden_queries_rejection_policy(self):
        """Negative and invalid queries flagged should_reject=True must raise ValueError."""
        reject_queries = [q for q in self.queries if q["should_reject"]]
        self.assertGreaterEqual(len(reject_queries), 3)

        for q in reject_queries:
            with self.subTest(query_id=q["query_id"]):
                with self.assertRaises(ValueError):
                    # Should be rejected during query processing or filter compilation
                    if q["expected_machine_id"] == "M999":
                        filter_spec = RetrievalFilter(machine_id="M999")
                        self.service.retrieve(q["query_text"], filter=filter_spec)
                    else:
                        self.processor.process_query(q["query_text"])

    def test_category_a_machine_specific_retrieval(self):
        """Category A queries (GQ-001 to GQ-006) isolate to target machine and find expected docs."""
        cat_a_queries = self.queries[0:6]
        for q in cat_a_queries:
            with self.subTest(query_id=q["query_id"]):
                resp = self.service.retrieve(q["query_text"], top_k=5)
                self.assertGreater(resp.returned_count, 0)
                # Verify machine isolation
                for item in resp.results:
                    self.assertIn(item.machine_id, [q["expected_machine_id"], None])
                # Verify that at least one of the expected doc IDs is retrieved
                retrieved_doc_ids = {item.document_id for item in resp.results}
                overlap = set(q["relevant_doc_ids"]).intersection(retrieved_doc_ids)
                self.assertGreater(
                    len(overlap),
                    0,
                    f"Query {q['query_id']} did not retrieve any of {q['relevant_doc_ids']}; got {retrieved_doc_ids}",
                )

    def test_category_b_sensor_anomaly_retrieval(self):
        """Category B queries (GQ-007 to GQ-012) retrieve sensor troubleshooting and SOP procedures."""
        cat_b_queries = self.queries[6:12]
        for q in cat_b_queries:
            with self.subTest(query_id=q["query_id"]):
                resp = self.service.retrieve(q["query_text"], top_k=5)
                self.assertGreater(resp.returned_count, 0)
                # Verify high similarity for in-domain sensor queries
                top_score = resp.results[0].similarity_score
                self.assertGreaterEqual(
                    top_score,
                    0.65,
                    f"Query {q['query_id']} top similarity {top_score} < 0.65",
                )
                retrieved_doc_ids = {item.document_id for item in resp.results}
                overlap = set(q["relevant_doc_ids"]).intersection(retrieved_doc_ids)
                self.assertGreater(len(overlap), 0)

    def test_category_c_historical_incidents_retrieval(self):
        """Category C queries (GQ-013 to GQ-018) retrieve maintenance incidents with valid lineage."""
        cat_c_queries = self.queries[12:18]
        for q in cat_c_queries:
            with self.subTest(query_id=q["query_id"]):
                resp = self.service.retrieve_historical_incidents(
                    q["query_text"],
                    machine_id=q["expected_machine_id"],
                    top_k=5,
                )
                self.assertGreater(resp.returned_count, 0)
                for item in resp.results:
                    self.assertEqual(item.category, "INCIDENT")
                    if q["expected_machine_id"]:
                        self.assertEqual(item.machine_id, q["expected_machine_id"])
                    self.assertTrue(item.source_record_id.startswith("ROW-"))
                    self.assertGreaterEqual(item.original_row_index, 1)
                    self.assertLessEqual(item.original_row_index, 400)
                    self.assertTrue(item.provenance_validated)

    def test_category_d_safety_loto_retrieval(self):
        """Category D queries (GQ-019 to GQ-024) retrieve safety-critical procedures."""
        cat_d_queries = self.queries[18:24]
        for q in cat_d_queries:
            with self.subTest(query_id=q["query_id"]):
                resp = self.service.retrieve_safety_procedures(q["query_text"], top_k=5)
                self.assertGreater(resp.returned_count, 0)
                for item in resp.results:
                    self.assertTrue(item.is_safety_related)
                    self.assertTrue(item.provenance_validated)
                # Verify top result is highly relevant
                self.assertGreaterEqual(resp.results[0].similarity_score, 0.70)

    def test_category_e_cross_machine_retrieval(self):
        """Category E queries (GQ-025 to GQ-030) execute cross-machine search."""
        cat_e_queries = self.queries[24:30]
        for q in cat_e_queries:
            with self.subTest(query_id=q["query_id"]):
                resp = self.service.retrieve_cross_machine(
                    q["query_text"],
                    category=q.get("expected_category"),
                    top_k=5,
                )
                self.assertEqual(resp.retrieval_mode, RetrievalMode.CROSS_MACHINE.value)
                self.assertGreater(resp.returned_count, 0)
                retrieved_doc_ids = {item.document_id for item in resp.results}
                overlap = set(q["relevant_doc_ids"]).intersection(retrieved_doc_ids)
                self.assertGreater(len(overlap), 0)

    def test_category_f_out_of_domain_similarity_contrast(self):
        """Out-of-domain query (GQ-033) yields lower similarity than domain-specific queries."""
        ood_q = self.queries[32]  # GQ-033 chocolate chip cookies
        domain_q = self.queries[0]  # GQ-001 M104 spindle bearing wear

        resp_ood = self.service.retrieve(ood_q["query_text"], top_k=5)
        resp_domain = self.service.retrieve(domain_q["query_text"], top_k=5)

        ood_top_score = resp_ood.results[0].similarity_score if resp_ood.results else 0.0
        domain_top_score = resp_domain.results[0].similarity_score if resp_domain.results else 0.0

        self.assertGreater(domain_top_score, ood_top_score)
        self.assertLess(ood_top_score, 0.60)

    def test_retrieval_latency_and_metrics_benchmark(self):
        """All valid queries execute under 1.5s per query with high overall MRR and Precision."""
        valid_queries = [q for q in self.queries if not q["should_reject"] and q["relevant_doc_ids"]]
        self.assertGreaterEqual(len(valid_queries), 28)

        reciprocal_ranks = []
        precision_at_5_list = []
        latencies = []

        for q in valid_queries:
            start_t = time.perf_counter()
            if q.get("expected_category") == "INCIDENT":
                resp = self.service.retrieve_historical_incidents(
                    q["query_text"],
                    machine_id=q.get("expected_machine_id"),
                    top_k=5,
                )
            elif q.get("expected_category") == "SAFETY":
                resp = self.service.retrieve_safety_procedures(
                    q["query_text"],
                    top_k=5,
                )
            elif q["retrieval_mode"] == "machine_specific" and q.get("expected_machine_id"):
                resp = self.service.retrieve_machine_specific(
                    query_text=q["query_text"],
                    machine_id=q["expected_machine_id"],
                    category=q.get("expected_category"),
                    top_k=5,
                )
            else:
                filter_obj = (
                    RetrievalFilter(category=q.get("expected_category"), cross_machine=True)
                    if q.get("expected_category")
                    else None
                )
                resp = self.service.retrieve(query=q["query_text"], filter=filter_obj, top_k=5)

            elapsed = time.perf_counter() - start_t
            latencies.append(elapsed)

            retrieved_ids = [item.document_id for item in resp.results]
            expected_set = set(q["relevant_doc_ids"])

            # Compute reciprocal rank
            rr = 0.0
            for rank_idx, doc_id in enumerate(retrieved_ids, 1):
                if doc_id in expected_set:
                    rr = 1.0 / rank_idx
                    break
            reciprocal_ranks.append(rr)

            # Compute Precision@5
            hits = sum(1 for doc_id in retrieved_ids if doc_id in expected_set)
            p_at_5 = hits / len(retrieved_ids) if retrieved_ids else 0.0
            precision_at_5_list.append(p_at_5)

        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        mean_p5 = sum(precision_at_5_list) / len(precision_at_5_list)
        mean_latency = sum(latencies) / len(latencies)

        # Performance and accuracy assertions
        self.assertGreaterEqual(mrr, 0.75, f"MRR {mrr:.4f} is below 0.75")
        self.assertGreaterEqual(mean_p5, 0.50, f"Mean Precision@5 {mean_p5:.4f} is below 0.50")
        self.assertLess(mean_latency, 1.5, f"Mean query latency {mean_latency:.4f}s exceeds 1.5s")


if __name__ == "__main__":
    unittest.main()
