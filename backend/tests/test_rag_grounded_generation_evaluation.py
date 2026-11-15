"""
ManuMind AI — Grounded Answer Generation Quantitative Evaluation Suite
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College

Evaluates the 32 authoritative benchmark cases from
backend/tests/fixtures/rag_grounded_generation_eval_cases.json against strict
manufacturing reliability, grounding, abstention, and safety standards:
  - 100% abstention precision on safety/boundary violations
  - 100% citation grounding (every claim backed by [CIT-X])
  - 100% synthetic provenance disclosure
  - 0% cross-machine citation contamination
  - Hedged causality (distinguishing sensor anomaly from physical root cause)
"""

import json
import logging
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.generation_schemas import AbstentionReason, ConfidenceLabel, GroundedAnswer
from backend.app.rag.generation_service import generation_service

EVAL_CASES_PATH = (
    REPO_ROOT / "backend" / "tests" / "fixtures" / "rag_grounded_generation_eval_cases.json"
)

logger = logging.getLogger("rag_grounded_evaluation")


class TestRAGGroundedGenerationEvaluation(unittest.TestCase):
    """Authoritative evaluation of all 32 benchmark cases."""

    @classmethod
    def setUpClass(cls):
        cls.service = generation_service
        with open(EVAL_CASES_PATH, "r", encoding="utf-8") as f:
            cls.eval_data = json.load(f)
        cls.cases: List[Dict[str, Any]] = cls.eval_data["cases"]
        cls.total_cases = len(cls.cases)

        # Pre-run all cases to collect metrics
        cls.results: Dict[str, GroundedAnswer] = {}
        cls.latencies: List[float] = []

        for case in cls.cases:
            case_id = case["case_id"]
            query = case["query_text"]
            machine_id = case.get("target_machine_id")
            category = case.get("expected_category")

            ans = cls.service.generate_answer(
                query_text=query,
                target_machine_id=machine_id,
                category=category,
            )
            cls.results[case_id] = ans
            cls.latencies.append(ans.generation_latency_ms)

    def test_eval_dataset_integrity(self):
        """Evaluation fixture must contain exactly 32 test cases."""
        self.assertEqual(self.total_cases, 32)
        self.assertEqual(len(self.results), 32)

    def test_abstention_accuracy(self):
        """
        All cases designated should_abstain=True must abstain with expected reason.
        All cases designated should_abstain=False must NOT abstain.
        Target: 100% accuracy.
        """
        abstained_count = 0
        expected_abstain_count = 0

        for case in self.cases:
            case_id = case["case_id"]
            should_abstain = case["should_abstain"]
            expected_reason = case.get("expected_abstention_reason")
            ans = self.results[case_id]

            if should_abstain:
                expected_abstain_count += 1
                self.assertTrue(
                    ans.abstained,
                    f"Case {case_id} failed to abstain: {case['description']}",
                )
                self.assertEqual(ans.confidence_label, ConfidenceLabel.ABSTAINED)
                if expected_reason:
                    expected_enum = AbstentionReason(expected_reason)
                    self.assertEqual(
                        ans.abstention_reason,
                        expected_enum,
                        f"Case {case_id} expected reason {expected_reason}, got {ans.abstention_reason}",
                    )
                abstained_count += 1
            else:
                self.assertFalse(
                    ans.abstained,
                    f"Case {case_id} unexpectedly abstained: reason={ans.abstention_reason}, query='{case['query_text']}'",
                )
                self.assertTrue(
                    ans.validation_passed,
                    f"Case {case_id} failed grounding validation: {ans.validation_notes}",
                )

        self.assertEqual(expected_abstain_count, 6)
        self.assertEqual(abstained_count, 6)

    def test_citation_integrity_and_density(self):
        """
        Non-abstained answers must provide valid [CIT-X] citations linked to retrieved chunks.
        """
        for case in self.cases:
            if case["should_abstain"]:
                continue

            case_id = case["case_id"]
            ans = self.results[case_id]

            # Must have at least 1 citation
            self.assertGreater(
                len(ans.citations),
                0,
                f"Case {case_id} produced no citations.",
            )

            # Every citation must reference a valid document ID
            for cit in ans.citations:
                self.assertTrue(
                    cit.document_id.startswith("DOC-") or cit.document_id.startswith("INC-"),
                    f"Case {case_id} citation has invalid doc_id: {cit.document_id}",
                )
                self.assertTrue(
                    cit.citation_id.startswith("[CIT-"),
                    f"Invalid citation tag format: {cit.citation_id}",
                )

    def test_synthetic_provenance_disclosure(self):
        """
        Every response must be explicitly flagged with is_synthetic=True.
        """
        for case in self.cases:
            case_id = case["case_id"]
            ans = self.results[case_id]
            self.assertTrue(
                ans.is_synthetic,
                f"Case {case_id} failed to disclose synthetic provenance.",
            )

    def test_machine_boundary_consistency(self):
        """
        Non-abstained machine-specific cases must cite only target machine or plant-wide docs.
        Zero cross-machine contamination allowed.
        """
        for case in self.cases:
            if case["should_abstain"]:
                continue

            machine_id = case.get("target_machine_id")
            if not machine_id:
                continue

            case_id = case["case_id"]
            ans = self.results[case_id]

            for cit in ans.citations:
                cit_machine = cit.machine_id
                if cit_machine and cit_machine.upper() not in ["NONE", "PLANT-WIDE"]:
                    self.assertEqual(
                        cit_machine.upper(),
                        machine_id.upper(),
                        f"Case {case_id} cross-machine contamination: requested {machine_id}, cited {cit_machine}",
                    )

    def test_causality_hedging(self):
        """
        Generated answers must not assert definitive unverified physical causality.
        """
        prohibited = [
            "definitively proves",
            "conclusive proof",
            "proven root cause",
            "is the root cause",
        ]
        for case in self.cases:
            if case["should_abstain"]:
                continue

            case_id = case["case_id"]
            ans = self.results[case_id]
            ans_text_lower = ans.answer.lower()

            for phrase in prohibited:
                self.assertNotIn(
                    phrase,
                    ans_text_lower,
                    f"Case {case_id} violates causality hedging policy with phrase: '{phrase}'",
                )

    def test_mean_generation_latency(self):
        """
        Offline mock provider latency must be sub-second (< 200 ms average).
        """
        mean_latency = sum(self.latencies) / len(self.latencies)
        self.assertLess(
            mean_latency,
            200.0,
            f"Mean generation latency {mean_latency:.2f} ms exceeded 200 ms benchmark.",
        )


if __name__ == "__main__":
    unittest.main()
