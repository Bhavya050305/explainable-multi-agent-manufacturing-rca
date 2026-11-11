"""
ManuMind AI — Phase 3 Step 5: Source Provenance Resolver Tests
Tests for source path resolution, file existence checks, SHA-256 hash formatting,
and maintenance CSV row index integrity.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.config import rag_config
from backend.app.rag.source_resolver import SourceResolver, source_resolver


class TestSourceResolver(unittest.TestCase):
    """Test suite for SourceResolver."""

    def setUp(self):
        self.resolver = SourceResolver()
        self.valid_hash = "a" * 64

    def test_missing_source_path(self):
        """Missing or 'NONE' source path returns False."""
        is_valid, msg = self.resolver.resolve_provenance({"source_path": None})
        self.assertFalse(is_valid)
        self.assertIn("Missing source_path", msg)

        is_valid, msg = self.resolver.resolve_provenance({"source_path": "NONE"})
        self.assertFalse(is_valid)
        self.assertIn("Missing source_path", msg)

    def test_nonexistent_source_path(self):
        """Path pointing to nonexistent file returns False."""
        meta = {
            "source_path": "knowledge_base/non_existent_folder/fake_file.md",
            "raw_file_hash": self.valid_hash,
            "content_hash": self.valid_hash,
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Source file does not exist on disk", msg)

    def test_invalid_raw_file_hash_format(self):
        """Invalid length or non-hex characters in raw_file_hash fails validation."""
        # Short hash
        meta = {
            "source_path": "knowledge_base/corpus_manifest.json",
            "raw_file_hash": "short_hash",
            "content_hash": self.valid_hash,
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid raw_file_hash format", msg)

        # Non-hex characters
        meta["raw_file_hash"] = "z" * 64
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid raw_file_hash format", msg)

    def test_invalid_content_hash_format(self):
        """Invalid length or non-hex characters in content_hash fails validation."""
        meta = {
            "source_path": "knowledge_base/corpus_manifest.json",
            "raw_file_hash": self.valid_hash,
            "content_hash": "not_64_hex_chars",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid content_hash format", msg)

    def test_incident_record_missing_or_invalid_record_id(self):
        """Incident record with missing or invalid source_record_id fails validation."""
        meta = {
            "source_path": "incidents/INC-0001.md",
            "raw_file_hash": self.valid_hash,
            "content_hash": self.valid_hash,
            "category": "INCIDENT",
            "source_record_id": "INVALID-ID",
            "original_row_index": 1,
            "machine_id": "M101",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid incident source_record_id", msg)

    def test_incident_record_row_index_out_of_bounds(self):
        """Incident record with row index outside 1-400 fails validation."""
        meta = {
            "source_path": "incidents/INC-0001.md",
            "raw_file_hash": self.valid_hash,
            "content_hash": self.valid_hash,
            "category": "INCIDENT",
            "source_record_id": "ROW-0001",
            "original_row_index": 0,  # Below minimum 1
            "machine_id": "M101",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid incident row_index", msg)

        meta["original_row_index"] = 401  # Above maximum 400
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Invalid incident row_index", msg)

    def test_incident_record_missing_machine_id(self):
        """Incident record with missing or 'NONE' machine_id fails validation."""
        meta = {
            "source_path": "incidents/INC-0001.md",
            "raw_file_hash": self.valid_hash,
            "content_hash": self.valid_hash,
            "category": "INCIDENT",
            "source_record_id": "ROW-0001",
            "original_row_index": 1,
            "machine_id": "NONE",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertFalse(is_valid)
        self.assertIn("Missing machine_id for incident record", msg)

    def test_valid_real_incident_provenance(self):
        """Valid incident record with actual markdown file passes provenance check."""
        meta = {
            "source_path": "incidents/INC-0001.md",
            "raw_file_hash": "b" * 64,
            "content_hash": "c" * 64,
            "category": "INCIDENT",
            "source_record_id": "ROW-0001",
            "original_row_index": 1,
            "machine_id": "M101",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "Provenance verified successfully")

    def test_valid_real_sop_provenance(self):
        """Valid SOP document with actual file on disk passes provenance check."""
        meta = {
            "source_path": "sops/SOP-M101.md",
            "raw_file_hash": "d" * 64,
            "content_hash": "e" * 64,
            "category": "SOP",
            "machine_id": "M101",
        }
        is_valid, msg = self.resolver.resolve_provenance(meta)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "Provenance verified successfully")


if __name__ == "__main__":
    unittest.main()
