"""
ManuMind AI — Phase 3 Step 5: Metadata Filter Compiler Tests
Tests for query metadata compilation, ChromaDB where-clause formatting, machine isolation,
cross-machine policies, and category validation.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.metadata_filter import MetadataFilterCompiler, metadata_filter_compiler
from backend.app.rag.retrieval_config import RetrievalConfig, retrieval_config
from backend.app.rag.retrieval_schemas import RetrievalFilter, RetrievalMode


class TestMetadataFilterCompiler(unittest.TestCase):
    """Test suite for MetadataFilterCompiler."""

    def setUp(self):
        self.compiler = MetadataFilterCompiler()

    def test_default_empty_filter(self):
        """Empty filter specification returns None where-clause and CROSS_MACHINE mode."""
        where_clause, mode = self.compiler.compile_filter()
        self.assertIsNone(where_clause)
        self.assertEqual(mode, RetrievalMode.CROSS_MACHINE)

    def test_machine_specific_with_global_fallback_default(self):
        """Machine-specific filter defaults to including global documents ('NONE')."""
        filt = RetrievalFilter(machine_id="M104")
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(mode, RetrievalMode.MACHINE_SPECIFIC)
        self.assertEqual(where_clause, {"machine_id": {"$in": ["M104", "NONE"]}})

    def test_machine_specific_strictly_isolated(self):
        """Machine-specific filter with include_global=False isolates strictly to target machine."""
        filt = RetrievalFilter(machine_id="M104", include_global=False)
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(mode, RetrievalMode.MACHINE_SPECIFIC)
        self.assertEqual(where_clause, {"machine_id": "M104"})

    def test_extracted_machine_id_fallback(self):
        """Machine ID extracted from query text is used when filter_spec machine is not provided."""
        where_clause, mode = self.compiler.compile_filter(
            filter_spec=None,
            extracted_machine_id="M102",
        )
        self.assertEqual(mode, RetrievalMode.MACHINE_SPECIFIC)
        self.assertEqual(where_clause, {"machine_id": {"$in": ["M102", "NONE"]}})

    def test_filter_spec_machine_precedence_over_extracted(self):
        """filter_spec.machine_id overrides extracted_machine_id."""
        filt = RetrievalFilter(machine_id="M105")
        where_clause, mode = self.compiler.compile_filter(
            filter_spec=filt,
            extracted_machine_id="M101",
        )
        self.assertEqual(mode, RetrievalMode.MACHINE_SPECIFIC)
        self.assertEqual(where_clause, {"machine_id": {"$in": ["M105", "NONE"]}})

    def test_global_only_mode_override(self):
        """RetrievalMode.GLOBAL_ONLY restricts machine_id strictly to 'NONE'."""
        where_clause, mode = self.compiler.compile_filter(
            mode_override=RetrievalMode.GLOBAL_ONLY
        )
        self.assertEqual(mode, RetrievalMode.GLOBAL_ONLY)
        self.assertEqual(where_clause, {"machine_id": "NONE"})

    def test_cross_machine_mode(self):
        """Explicit cross_machine flag sets mode to CROSS_MACHINE and skips machine filter."""
        filt = RetrievalFilter(cross_machine=True, category="SOP")
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(mode, RetrievalMode.CROSS_MACHINE)
        self.assertEqual(where_clause, {"category": "SOP"})

    def test_invalid_machine_id_rejection(self):
        """Unknown machine ID outside fleet assets (M101-M110) raises ValueError."""
        filt = RetrievalFilter(machine_id="M999")
        with self.assertRaises(ValueError) as ctx:
            self.compiler.compile_filter(filter_spec=filt)
        self.assertIn("Invalid machine identifier", str(ctx.exception))

    def test_valid_category_filtering(self):
        """Valid category filters compile correctly into where clause."""
        for cat in ["SOP", "TROUBLESHOOTING", "INCIDENT", "SAFETY"]:
            filt = RetrievalFilter(category=cat, cross_machine=True)
            where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
            self.assertEqual(where_clause, {"category": cat})

    def test_invalid_category_rejection(self):
        """Unsupported category raises ValueError / ValidationError."""
        with self.assertRaises(ValueError) as ctx:
            RetrievalFilter(category="INVALID_CAT")
        self.assertIn("Invalid category", str(ctx.exception))

    def test_safety_filter_compilation(self):
        """Safety-related flag filter compiles into boolean equality condition."""
        filt = RetrievalFilter(is_safety_related=True, cross_machine=True)
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(where_clause, {"is_safety_related": True})

    def test_synthetic_status_filter_compilation(self):
        """Synthetic status flag compiles into boolean equality condition."""
        filt = RetrievalFilter(is_synthetic=False, cross_machine=True)
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(where_clause, {"is_synthetic": False})

    def test_document_and_record_id_filter(self):
        """document_id and source_record_id compile into expected fields."""
        filt = RetrievalFilter(
            document_id="DOC-SOP-M101-001",
            source_record_id="ROW-0042",
            cross_machine=True,
        )
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertIn("$and", where_clause)
        conds = where_clause["$and"]
        self.assertIn({"document_id": "DOC-SOP-M101-001"}, conds)
        self.assertIn({"source_record_id": "ROW-0042"}, conds)

    def test_multiple_conditions_wrap_in_and(self):
        """Multiple combined criteria are wrapped in ChromaDB $and operator."""
        filt = RetrievalFilter(
            machine_id="M103",
            category="SOP",
            is_safety_related=True,
            include_global=True,
        )
        where_clause, mode = self.compiler.compile_filter(filter_spec=filt)
        self.assertEqual(mode, RetrievalMode.MACHINE_SPECIFIC)
        self.assertIn("$and", where_clause)
        self.assertEqual(len(where_clause["$and"]), 3)
        self.assertIn({"machine_id": {"$in": ["M103", "NONE"]}}, where_clause["$and"])
        self.assertIn({"category": "SOP"}, where_clause["$and"])
        self.assertIn({"is_safety_related": True}, where_clause["$and"])


if __name__ == "__main__":
    unittest.main()
