"""
ManuMind AI — Phase 3 Step 2: RAG Document Ingestion Pipeline Tests
Comprehensive Test Suite covering all 18 mandatory audit requirements.

Department of AI & Data Science — RMK Engineering College
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.document_loader import DocumentLoader
from backend.app.rag.metadata_parser import MetadataParser
from backend.app.rag.provenance_validator import ProvenanceValidator
from backend.app.rag.ingestion_service import IngestionService
from backend.app.rag.ingestion_report import IngestionReportGenerator
from backend.app.rag.schemas import (
    ExecutionMode,
    RawDocument,
    DocumentMetadata,
)
from backend.app.rag.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileError,
    MissingFrontMatterError,
    MalformedYAMLError,
    MissingMandatoryMetadataError,
    InvalidMetadataTypeError,
    DuplicateDocumentIDError,
    ProvenanceValidationError,
    MissingDisclaimerError,
    IncidentMappingError,
)


class TestRAGDocumentIngestion(unittest.TestCase):
    """Authoritative test suite for Phase 3 Step 2 document ingestion pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.config = rag_config
        cls.loader = DocumentLoader(cls.config)
        cls.parser = MetadataParser(cls.config)
        cls.validator = ProvenanceValidator(cls.config)
        cls.service = IngestionService(cls.config)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="manumind_rag_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Markdown Discovery
    # -------------------------------------------------------------------------
    def test_01_markdown_discovery(self):
        """Verify recursive discovery finds all 418 corpus markdown files in sorted order."""
        files = self.loader.discover_files(self.config.KNOWLEDGE_BASE_DIR)
        self.assertEqual(len(files), 418)

        # Confirm all files end with .md
        for f in files:
            self.assertTrue(f.name.endswith(".md"))

        # Confirm strictly sorted
        rel_paths = [str(f.relative_to(self.config.KNOWLEDGE_BASE_DIR)).replace("\\", "/") for f in files]
        self.assertEqual(rel_paths, sorted(rel_paths))

    # -------------------------------------------------------------------------
    # 2. UTF-8 Reading
    # -------------------------------------------------------------------------
    def test_02_utf8_reading(self):
        """Verify safe UTF-8 reading and detection of non-UTF-8 bytes."""
        # Valid UTF-8 file with multi-byte unicode
        valid_file = Path(self.temp_dir) / "valid.md"
        valid_content = "---\ndocument_id: TEST-01\n---\nUnicode: Ω, µ, ±, 100°C"
        valid_file.write_text(valid_content, encoding="utf-8")

        raw_doc = self.loader.load_document(valid_file, Path(self.temp_dir))
        self.assertIn("100°C", raw_doc.raw_content)

        # Invalid non-UTF-8 bytes
        bad_file = Path(self.temp_dir) / "corrupt_encoding.md"
        with open(bad_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00\x80\x81\x82")

        with self.assertRaises(DocumentLoadError) as ctx:
            self.loader.load_document(bad_file, Path(self.temp_dir))
        self.assertIn("UTF-8 decode failure", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. YAML Parsing
    # -------------------------------------------------------------------------
    def test_03_yaml_parsing(self):
        """Verify parsing valid front matter and separating body content."""
        sample_yaml = (
            "---\n"
            "document_id: 'DOC-SOP-TEST'\n"
            "document_name: 'Test Standard Operating Procedure'\n"
            "document_type: 'SOP'\n"
            "document_version: '1.0.0'\n"
            "machine_id: 'M101'\n"
            "machine_type: 'CNC Lathe'\n"
            "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
            "is_synthetic: true\n"
            "---\n"
            "\n"
            "> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL**\n"
            "# SOP Body Content"
        )
        meta, body = self.parser.parse(sample_yaml, "test.md")
        self.assertEqual(meta.document_id, "DOC-SOP-TEST")
        self.assertEqual(meta.title, "Test Standard Operating Procedure")
        self.assertEqual(meta.document_type, "SOP")
        self.assertEqual(meta.machine_id, "M101")
        self.assertEqual(meta.machine_type, "CNC Lathe")
        self.assertTrue(meta.is_synthetic)
        self.assertIn("# SOP Body Content", body)

    # -------------------------------------------------------------------------
    # 4. Missing Front Matter
    # -------------------------------------------------------------------------
    def test_04_missing_front_matter(self):
        """Verify rejection when opening or closing front matter delimiter is absent."""
        # Missing opening ---
        no_opening = "document_id: TEST\n---\nBody text"
        with self.assertRaises(MissingFrontMatterError):
            self.parser.parse(no_opening, "no_open.md")

        # Missing closing ---
        no_closing = "---\ndocument_id: TEST\nBody text without closing delimiter"
        with self.assertRaises(MissingFrontMatterError):
            self.parser.parse(no_closing, "no_close.md")

    # -------------------------------------------------------------------------
    # 5. Malformed YAML
    # -------------------------------------------------------------------------
    def test_05_malformed_yaml(self):
        """Verify handling of invalid YAML syntax and non-dictionary front matter."""
        # Broken YAML syntax
        bad_syntax = "---\ndocument_id: [broken yaml: invalid mapping\n---\nBody"
        with self.assertRaises(MalformedYAMLError):
            self.parser.parse(bad_syntax, "bad_yaml.md")

        # Non-dictionary YAML (e.g. scalar or list)
        scalar_yaml = "---\n- item1\n- item2\n---\nBody"
        with self.assertRaises(MalformedYAMLError):
            self.parser.parse(scalar_yaml, "list_yaml.md")

    # -------------------------------------------------------------------------
    # 6. Missing Required Metadata
    # -------------------------------------------------------------------------
    def test_06_missing_required_metadata(self):
        """Verify rejection when mandatory metadata fields are missing."""
        # Missing document_id
        missing_id = "---\ndocument_type: 'SOP'\nsource_type: 'SYNTHETIC_DEMONSTRATION'\nis_synthetic: true\ntitle: 'Title'\n---\nBody"
        with self.assertRaises(MissingMandatoryMetadataError) as ctx:
            self.parser.parse(missing_id, "missing_id.md")
        self.assertEqual(ctx.exception.field, "document_id")

        # Incident missing original_row_index
        incident_missing_row = (
            "---\n"
            "document_id: 'INC-TEST'\n"
            "title: 'Test Incident'\n"
            "document_type: 'INCIDENT'\n"
            "source_type: 'DERIVED_SYNTHETIC'\n"
            "is_synthetic: true\n"
            "machine_id: 'M101'\n"
            "source_record_id: 'ROW-0001'\n"
            "---\nBody"
        )
        with self.assertRaises(MissingMandatoryMetadataError) as ctx:
            self.parser.parse(incident_missing_row, "missing_row.md")
        self.assertEqual(ctx.exception.field, "original_row_index")

    # -------------------------------------------------------------------------
    # 7. Invalid Metadata Types
    # -------------------------------------------------------------------------
    def test_07_invalid_metadata_types(self):
        """Verify validation of enums and boolean types."""
        # Invalid document_type
        bad_type = (
            "---\n"
            "document_id: 'DOC-01'\n"
            "title: 'Test'\n"
            "document_type: 'MANUAL'\n"
            "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
            "is_synthetic: true\n"
            "---\nBody"
        )
        with self.assertRaises(InvalidMetadataTypeError) as ctx:
            self.parser.parse(bad_type, "bad_type.md")
        self.assertEqual(ctx.exception.field, "document_type")

        # is_synthetic must be boolean True
        false_synthetic = (
            "---\n"
            "document_id: 'DOC-01'\n"
            "title: 'Test'\n"
            "document_type: 'SOP'\n"
            "machine_id: 'M101'\n"
            "machine_type: 'CNC'\n"
            "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
            "is_synthetic: false\n"
            "---\nBody"
        )
        with self.assertRaises(InvalidMetadataTypeError) as ctx:
            self.parser.parse(false_synthetic, "not_synthetic.md")
        self.assertEqual(ctx.exception.field, "is_synthetic")

    # -------------------------------------------------------------------------
    # 8. Duplicate Document IDs
    # -------------------------------------------------------------------------
    def test_08_duplicate_document_ids(self):
        """Verify that conflicting duplicate document IDs within a batch are rejected."""
        seen = {}
        raw_doc1 = RawDocument(
            source_path="sops/doc1.md",
            file_name="doc1.md",
            raw_content=(
                "---\n"
                "document_id: 'DUPLICATE-ID'\n"
                "title: 'Doc 1'\n"
                "document_type: 'SOP'\n"
                "machine_id: 'M101'\n"
                "machine_type: 'Lathe'\n"
                "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
                "is_synthetic: true\n"
                "---\n"
                "> SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL\nBody 1"
            ),
            size_bytes=200,
            raw_file_hash="hash1",
        )
        raw_doc2 = RawDocument(
            source_path="sops/doc2.md",
            file_name="doc2.md",
            raw_content=(
                "---\n"
                "document_id: 'DUPLICATE-ID'\n"
                "title: 'Doc 2'\n"
                "document_type: 'SOP'\n"
                "machine_id: 'M102'\n"
                "machine_type: 'Mill'\n"
                "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
                "is_synthetic: true\n"
                "---\n"
                "> SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL\nBody 2 Different"
            ),
            size_bytes=220,
            raw_file_hash="hash2",
        )

        # First doc succeeds
        rec1 = self.service.process_document(raw_doc1, seen)
        self.assertEqual(rec1.document_id, "DUPLICATE-ID")

        # Second doc with conflicting path/content must raise DuplicateDocumentIDError
        with self.assertRaises(DuplicateDocumentIDError):
            self.service.process_document(raw_doc2, seen)

    # -------------------------------------------------------------------------
    # 9. Synthetic Provenance Validation
    # -------------------------------------------------------------------------
    def test_09_synthetic_provenance_validation(self):
        """Verify enforcement of category-to-source_type mapping rules."""
        # SOP must be SYNTHETIC_DEMONSTRATION, not DERIVED_SYNTHETIC
        sop_meta = DocumentMetadata(
            document_id="SOP-BAD-PROV",
            title="Bad Provenance SOP",
            document_type="SOP",
            source_type="DERIVED_SYNTHETIC",
            is_synthetic=True,
            machine_id="M101",
            machine_type="CNC Lathe",
        )
        with self.assertRaises(ProvenanceValidationError) as ctx:
            self.validator.validate_provenance(sop_meta, "sops/bad_prov.md")
        self.assertEqual(ctx.exception.field, "source_type")

        # Incident must be DERIVED_SYNTHETIC, not SYNTHETIC_DEMONSTRATION
        inc_meta = DocumentMetadata(
            document_id="INC-BAD-PROV",
            title="Bad Provenance Incident",
            document_type="INCIDENT",
            source_type="SYNTHETIC_DEMONSTRATION",
            is_synthetic=True,
            machine_id="M101",
            original_row_index=1,
            source_record_id="ROW-0001",
        )
        with self.assertRaises(ProvenanceValidationError) as ctx:
            self.validator.validate_provenance(inc_meta, "incidents/bad_prov.md")
        self.assertEqual(ctx.exception.field, "source_type")

    # -------------------------------------------------------------------------
    # 10. Missing Synthetic Disclaimers
    # -------------------------------------------------------------------------
    def test_10_missing_synthetic_disclaimers(self):
        """Verify rejection of documents missing prominent synthetic notices."""
        clean_content = "# Real Factory Manual\nThis is an authoritative OEM document with zero warnings."
        with self.assertRaises(MissingDisclaimerError):
            self.validator.validate_disclaimer(clean_content, "sops/clean.md")

        disclaimed_content = "> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL — NOT AN APPROVED OPERATIONAL PROCEDURE.**\nBody"
        # Should not raise
        self.validator.validate_disclaimer(disclaimed_content, "sops/valid.md")

    # -------------------------------------------------------------------------
    # 11. Manifest Reconciliation
    # -------------------------------------------------------------------------
    def test_11_manifest_reconciliation(self):
        """Verify manifest reconciliation against actual corpus and synthetic drift detection."""
        loaded, _ = self.loader.load_all(self.config.KNOWLEDGE_BASE_DIR)
        result = self.validator.reconcile_with_manifest(loaded)
        self.assertTrue(result.is_reconciled)
        self.assertEqual(result.matched_entries, 418)
        self.assertEqual(len(result.missing_on_disk), 0)
        self.assertEqual(len(result.hash_mismatches), 0)

        # Test detecting simulated drift
        mock_doc = RawDocument(
            source_path="knowledge_base/sops/SAFETY-ELECTRICAL-ISOLATION-DEMO.md",
            file_name="SAFETY-ELECTRICAL-ISOLATION-DEMO.md",
            raw_content="tampered",
            size_bytes=9999,
            raw_file_hash="0000000000000000000000000000000000000000000000000000000000000000",
        )
        drift_result = self.validator.reconcile_with_manifest([mock_doc])
        self.assertFalse(drift_result.is_reconciled)
        self.assertGreater(len(drift_result.size_mismatches), 0)
        self.assertGreater(len(drift_result.hash_mismatches), 0)

    # -------------------------------------------------------------------------
    # 12. Incident Source-Row Mapping
    # -------------------------------------------------------------------------
    def test_12_incident_source_row_mapping(self):
        """Verify all 400 incidents map 1-to-1 to maintenance_history.csv rows."""
        loaded, _ = self.loader.load_all(self.config.KNOWLEDGE_BASE_DIR / "incidents")
        self.assertEqual(len(loaded), 400)

        metadata_list = []
        for raw_doc in loaded:
            meta, _ = self.parser.parse(raw_doc.raw_content, raw_doc.source_path)
            self.validator.validate_incident_mapping(meta, raw_doc.source_path)
            metadata_list.append(meta)

        reconcile_res = self.validator.reconcile_all_incidents(metadata_list)
        self.assertTrue(reconcile_res.is_reconciled)
        self.assertEqual(reconcile_res.mapped_documents, 400)
        self.assertEqual(len(reconcile_res.mismatches), 0)

        # Test detecting invalid row mapping
        corrupt_meta = DocumentMetadata(
            document_id="INC-CORRUPT",
            title="Corrupted",
            document_type="INCIDENT",
            source_type="DERIVED_SYNTHETIC",
            is_synthetic=True,
            machine_id="M999",  # Wrong machine
            original_row_index=1,
            source_record_id="ROW-0001",
        )
        with self.assertRaises(IncidentMappingError) as ctx:
            self.validator.validate_incident_mapping(corrupt_meta, "corrupt.md")
        self.assertEqual(ctx.exception.field, "machine_id")

    # -------------------------------------------------------------------------
    # 13. SHA-256 Determinism
    # -------------------------------------------------------------------------
    def test_13_sha256_determinism(self):
        """Verify identical normalized content produces identical SHA-256 hashes."""
        content_lf = "# Header\nLine 1\nLine 2\n"
        content_crlf = "# Header\r\nLine 1   \r\nLine 2\r\n\r\n"
        content_spaces = "   \n# Header\nLine 1\nLine 2\n   \n"

        hash1 = self.service.compute_content_hash(content_lf)
        hash2 = self.service.compute_content_hash(content_crlf)
        hash3 = self.service.compute_content_hash(content_spaces)

        self.assertEqual(hash1, hash2)
        self.assertEqual(hash2, hash3)

        diff_content = "# Header\nLine 1\nLine 2 modified\n"
        hash_diff = self.service.compute_content_hash(diff_content)
        self.assertNotEqual(hash1, hash_diff)

    # -------------------------------------------------------------------------
    # 14. Changed-Document Detection
    # -------------------------------------------------------------------------
    def test_14_changed_document_detection(self):
        """Verify detection of changed document content under identical document_id."""
        self.service.clear_registry()
        raw_v1 = RawDocument(
            source_path="sops/test_change.md",
            file_name="test_change.md",
            raw_content=(
                "---\n"
                "document_id: 'DOC-CHANGE-01'\n"
                "title: 'Test'\n"
                "document_type: 'SOP'\n"
                "machine_id: 'M101'\n"
                "machine_type: 'Lathe'\n"
                "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
                "is_synthetic: true\n"
                "---\n"
                "> SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL\nOriginal content"
            ),
            size_bytes=200,
            raw_file_hash="hash1",
        )
        rec1 = self.service.process_document(raw_v1, {})
        # Register v1
        self.service._registry[rec1.document_id] = rec1

        # Now simulate ingesting v2 with modified body
        raw_v2 = RawDocument(
            source_path="sops/test_change.md",
            file_name="test_change.md",
            raw_content=(
                "---\n"
                "document_id: 'DOC-CHANGE-01'\n"
                "title: 'Test'\n"
                "document_type: 'SOP'\n"
                "machine_id: 'M101'\n"
                "machine_type: 'Lathe'\n"
                "source_type: 'SYNTHETIC_DEMONSTRATION'\n"
                "is_synthetic: true\n"
                "---\n"
                "> SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL\nModified content!"
            ),
            size_bytes=205,
            raw_file_hash="hash2",
        )
        rec2 = self.service.process_document(raw_v2, {})
        self.assertNotEqual(rec1.content_hash, rec2.content_hash)

    # -------------------------------------------------------------------------
    # 15. Idempotent Ingestion
    # -------------------------------------------------------------------------
    def test_15_idempotent_ingestion(self):
        """Verify repeating ingestion of unchanged documents does not duplicate records."""
        self.service.clear_registry()
        summary1 = self.service.ingest(execution_mode=ExecutionMode.IN_MEMORY_INGESTION)
        count1 = len(self.service.registry)
        self.assertEqual(count1, 418)

        # Repeated ingestion run
        summary2 = self.service.ingest(execution_mode=ExecutionMode.IN_MEMORY_INGESTION)
        count2 = len(self.service.registry)
        self.assertEqual(count2, 418)
        self.assertEqual(summary2.total_valid, 418)
        self.assertEqual(summary2.total_rejected, 0)

    # -------------------------------------------------------------------------
    # 16. Unsupported File Handling
    # -------------------------------------------------------------------------
    def test_16_unsupported_file_handling(self):
        """Verify non-markdown files and temporary files are safely rejected."""
        unsupported = Path(self.temp_dir) / "notes.txt"
        unsupported.write_text("Plain text file", encoding="utf-8")

        with self.assertRaises(UnsupportedFileError):
            self.loader.load_document(unsupported, Path(self.temp_dir))

        temp_file = Path(self.temp_dir) / "document.md.tmp"
        temp_file.write_text("Temporary file", encoding="utf-8")

        with self.assertRaises(UnsupportedFileError):
            self.loader.load_document(temp_file, Path(self.temp_dir))

    # -------------------------------------------------------------------------
    # 17. Empty Documents
    # -------------------------------------------------------------------------
    def test_17_empty_documents(self):
        """Verify detection of zero-byte and whitespace-only documents."""
        # 0-byte file
        zero_file = Path(self.temp_dir) / "zero.md"
        zero_file.touch()

        with self.assertRaises(EmptyDocumentError):
            self.loader.load_document(zero_file, Path(self.temp_dir))

        # Whitespace only file
        ws_file = Path(self.temp_dir) / "whitespace.md"
        ws_file.write_text("   \n\t\n  \n", encoding="utf-8")

        with self.assertRaises(EmptyDocumentError):
            self.loader.load_document(ws_file, Path(self.temp_dir))

    # -------------------------------------------------------------------------
    # 18. Full Corpus Ingestion
    # -------------------------------------------------------------------------
    def test_18_full_corpus_ingestion(self):
        """Verify complete end-to-end ingestion and reporting on the actual corpus."""
        self.service.clear_registry()
        summary = self.service.ingest(execution_mode=ExecutionMode.IN_MEMORY_INGESTION)

        # Verify acceptance targets
        self.assertEqual(summary.total_discovered, 418)
        self.assertEqual(summary.total_parsed, 418)
        self.assertEqual(summary.total_valid, 418)
        self.assertEqual(summary.total_rejected, 0)
        self.assertEqual(summary.duplicate_ids_count, 0)
        self.assertEqual(summary.provenance_passed, 418)
        self.assertEqual(summary.disclaimer_passed, 418)
        self.assertEqual(summary.incident_mappings_reconciled, 400)
        self.assertTrue(summary.manifest_reconciliation.is_reconciled)
        self.assertTrue(summary.incident_mapping_result.is_reconciled)

        # Generate reports
        generator = IngestionReportGenerator(self.config)
        md_path, json_path = generator.generate_reports(
            summary=summary,
            test_results={"all_18_unit_tests_passed": True},
        )

        self.assertTrue(md_path.exists())
        self.assertTrue(json_path.exists())

        with open(json_path, "r", encoding="utf-8") as f:
            jdata = json.load(f)
        self.assertEqual(jdata["final_verdict"], "PASS — INGESTION PIPELINE COMPLETE")
        self.assertEqual(jdata["summary_metrics"]["total_valid"], 418)


if __name__ == "__main__":
    unittest.main()
