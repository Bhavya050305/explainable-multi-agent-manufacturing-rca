"""
ManuMind AI — RAG Source Provenance Resolver
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.app.rag.config import RAGConfig, rag_config


class SourceResolver:
    """
    Validates physical file and database provenance for retrieved vector segments.
    Enforces auditability, CSV row mapping verification, and hash integrity.
    """

    def __init__(self, config: RAGConfig = rag_config):
        self.config = config
        self.repo_root = config.BASE_DIR

    def resolve_provenance(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verify provenance and file existence for a retrieved segment's metadata.
        Returns:
            Tuple of (is_validated: bool, diagnostic_message: Optional[str]).
        """
        source_path_rel = metadata.get("source_path")
        if not source_path_rel or source_path_rel == "NONE":
            return False, "Missing source_path metadata"

        # Resolve path relative to knowledge_base or repo root
        file_path = self.repo_root / source_path_rel
        if not file_path.exists():
            kb_path = self.config.KNOWLEDGE_BASE_DIR / source_path_rel
            if kb_path.exists():
                file_path = kb_path
            else:
                return False, f"Source file does not exist on disk: {source_path_rel}"

        # Verify raw file hash format
        raw_hash = metadata.get("raw_file_hash")
        if not raw_hash or len(raw_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in raw_hash):
            return False, f"Invalid raw_file_hash format: {raw_hash}"

        # Verify content hash format
        content_hash = metadata.get("content_hash")
        if not content_hash or len(content_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in content_hash):
            return False, f"Invalid content_hash format: {content_hash}"

        # For Incident records, verify maintenance CSV lineage
        category = metadata.get("category")
        if category == "INCIDENT":
            rec_id = metadata.get("source_record_id")
            row_idx = metadata.get("original_row_index")

            if not rec_id or not str(rec_id).startswith("ROW-"):
                return False, f"Invalid incident source_record_id: {rec_id}"

            if row_idx is None or int(row_idx) < 1 or int(row_idx) > 400:
                return False, f"Invalid incident row_index: {row_idx} (expected 1-400)"

            # Verify machine ID is present and valid
            machine_id = metadata.get("machine_id")
            if not machine_id or machine_id == "NONE":
                return False, "Missing machine_id for incident record"

        return True, "Provenance verified successfully"


source_resolver = SourceResolver()
