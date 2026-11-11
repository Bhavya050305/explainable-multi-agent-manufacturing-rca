"""
ManuMind AI — RAG Provenance and Synthetic Data Validator
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.exceptions import (
    ProvenanceValidationError,
    MissingDisclaimerError,
    IncidentMappingError,
    ManifestReconciliationError,
)
from backend.app.rag.schemas import (
    DocumentMetadata,
    RawDocument,
    ManifestReconciliationResult,
    IncidentMappingResult,
)


class ProvenanceValidator:
    """Enforces provenance, synthetic disclosures, manifest integrity, and CSV mapping."""

    def __init__(self, config: RAGConfig = rag_config):
        self.config = config
        self._csv_rows_cache: Optional[List[List[str]]] = None
        self._manifest_cache: Optional[Dict] = None

    def _get_maintenance_csv_rows(self, csv_path: Path | None = None) -> List[List[str]]:
        """Read and cache maintenance history CSV rows."""
        if self._csv_rows_cache is not None:
            return self._csv_rows_cache

        target_path = (csv_path or self.config.MAINTENANCE_CSV_PATH).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Maintenance history CSV not found: {target_path}")

        with open(target_path, "r", encoding=self.config.ENCODING) as f:
            reader = csv.reader(f)
            _ = next(reader)  # Skip header
            self._csv_rows_cache = list(reader)

        return self._csv_rows_cache

    def _get_manifest_data(self, manifest_path: Path | None = None) -> Dict:
        """Read and cache manifest JSON data."""
        if self._manifest_cache is not None:
            return self._manifest_cache

        target_path = (manifest_path or self.config.CORPUS_MANIFEST_PATH).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Corpus manifest not found: {target_path}")

        with open(target_path, "r", encoding=self.config.ENCODING) as f:
            self._manifest_cache = json.load(f)

        return self._manifest_cache

    def validate_provenance(self, metadata: DocumentMetadata, source_path: str) -> None:
        """Verify provenance policy compliance for a document."""
        # 1. is_synthetic must always be True
        if not metadata.is_synthetic:
            raise ProvenanceValidationError(
                "Document must declare 'is_synthetic: true'",
                source_path=source_path,
                field="is_synthetic",
            )

        # 2. Category to source_type rule
        expected = self.config.PROVENANCE_POLICY.get(metadata.document_type)
        if not expected:
            raise ProvenanceValidationError(
                f"Unknown document category '{metadata.document_type}' in provenance policy",
                source_path=source_path,
                field="document_type",
            )

        expected_source_type = expected["source_type"]
        if metadata.source_type != expected_source_type:
            raise ProvenanceValidationError(
                f"Invalid source_type '{metadata.source_type}' for category '{metadata.document_type}'. Expected '{expected_source_type}'",
                source_path=source_path,
                field="source_type",
            )

    def validate_disclaimer(self, content: str, source_path: str) -> None:
        """Validate presence of visible synthetic disclaimer notice in document body."""
        upper_content = content.upper()
        # Must have clear, prominent synthetic notice
        has_notice = (
            "SYNTHETIC DEMONSTRATION" in upper_content
            or "SYNTHETIC MAINTENANCE" in upper_content
            or "SYNTHETIC HISTORICAL" in upper_content
            or "NOT AN APPROVED OPERATIONAL PROCEDURE" in upper_content
        )
        if not has_notice:
            raise MissingDisclaimerError(
                "Document body missing required visible synthetic demonstration disclaimer",
                source_path=source_path,
                field="operational_disclaimer",
            )

    def validate_incident_mapping(
        self,
        metadata: DocumentMetadata,
        source_path: str,
        csv_path: Path | None = None,
    ) -> None:
        """Validate incident document one-to-one mapping against source CSV row."""
        if metadata.document_type != "INCIDENT":
            return

        idx = metadata.original_row_index
        if idx is None or idx < 1:
            raise IncidentMappingError(
                f"Incident has invalid original_row_index: {idx}",
                source_path=source_path,
                field="original_row_index",
            )

        expected_record_id = f"ROW-{idx:04d}"
        if metadata.source_record_id != expected_record_id:
            raise IncidentMappingError(
                f"Incident source_record_id '{metadata.source_record_id}' does not match expected '{expected_record_id}'",
                source_path=source_path,
                field="source_record_id",
            )

        csv_rows = self._get_maintenance_csv_rows(csv_path)
        if idx > len(csv_rows):
            raise IncidentMappingError(
                f"original_row_index {idx} exceeds CSV row count {len(csv_rows)}",
                source_path=source_path,
                field="original_row_index",
            )

        row = csv_rows[idx - 1]
        row_machine_id = row[0]
        row_date = row[1]

        if metadata.machine_id != row_machine_id:
            raise IncidentMappingError(
                f"Machine ID mismatch: document has '{metadata.machine_id}', CSV row {idx} has '{row_machine_id}'",
                source_path=source_path,
                field="machine_id",
            )

        if metadata.event_date and metadata.event_date != row_date:
            raise IncidentMappingError(
                f"Event date mismatch: document has '{metadata.event_date}', CSV row {idx} has '{row_date}'",
                source_path=source_path,
                field="event_date",
            )

    def reconcile_with_manifest(
        self,
        raw_docs: List[RawDocument],
        manifest_path: Path | None = None,
    ) -> ManifestReconciliationResult:
        """Reconcile all loaded raw documents against corpus_manifest.json."""
        manifest = self._get_manifest_data(manifest_path)
        manifest_docs = {
            entry["relative_path"].replace("\\", "/"): entry
            for entry in manifest.get("documents", [])
        }

        # Index loaded documents by relative path (normalized to start with knowledge_base/ if needed)
        loaded_by_rel: Dict[str, RawDocument] = {}
        for d in raw_docs:
            p = d.source_path.replace("\\", "/")
            if not p.startswith("knowledge_base/"):
                p = f"knowledge_base/{p}"
            loaded_by_rel[p] = d

        total_manifest = len(manifest_docs)
        matched = 0
        missing_on_disk: List[str] = []
        hash_mismatches: List[str] = []
        size_mismatches: List[str] = []

        for rel_path, entry in manifest_docs.items():
            if rel_path not in loaded_by_rel:
                missing_on_disk.append(rel_path)
                continue

            doc = loaded_by_rel[rel_path]
            matched += 1

            if doc.size_bytes != entry.get("size_bytes"):
                size_mismatches.append(
                    f"{rel_path}: disk={doc.size_bytes} vs manifest={entry.get('size_bytes')}"
                )

            if doc.raw_file_hash != entry.get("sha256"):
                hash_mismatches.append(
                    f"{rel_path}: disk={doc.raw_file_hash[:12]}... vs manifest={entry.get('sha256', '')[:12]}..."
                )

        untracked: List[str] = [p for p in loaded_by_rel if p not in manifest_docs]

        is_reconciled = (
            matched == total_manifest
            and len(missing_on_disk) == 0
            and len(untracked) == 0
            and len(hash_mismatches) == 0
            and len(size_mismatches) == 0
        )

        return ManifestReconciliationResult(
            total_manifest_entries=total_manifest,
            matched_entries=matched,
            missing_on_disk=missing_on_disk,
            untracked_on_disk=untracked,
            hash_mismatches=hash_mismatches,
            size_mismatches=size_mismatches,
            is_reconciled=is_reconciled,
        )

    def reconcile_all_incidents(
        self,
        metadata_list: List[DocumentMetadata],
        csv_path: Path | None = None,
    ) -> IncidentMappingResult:
        """Reconcile all 400 incident metadata records against CSV rows."""
        csv_rows = self._get_maintenance_csv_rows(csv_path)
        total_csv = len(csv_rows)

        incident_metas = [m for m in metadata_list if m.document_type == "INCIDENT"]
        mismatches: List[str] = []

        seen_indices = set()
        for m in incident_metas:
            idx = m.original_row_index
            if idx is None or idx < 1 or idx > total_csv:
                mismatches.append(f"{m.document_id}: invalid row index {idx}")
                continue
            seen_indices.add(idx)

            row = csv_rows[idx - 1]
            if m.machine_id != row[0]:
                mismatches.append(f"{m.document_id}: machine_id {m.machine_id} != {row[0]}")
            if m.event_date != row[1]:
                mismatches.append(f"{m.document_id}: date {m.event_date} != {row[1]}")

        # Check for missing rows
        missing_rows = set(range(1, total_csv + 1)) - seen_indices
        if missing_rows:
            mismatches.append(f"Missing incident rows from CSV: {sorted(list(missing_rows))[:5]}")

        is_reconciled = (
            len(incident_metas) == total_csv
            and len(missing_rows) == 0
            and len(mismatches) == 0
        )

        return IncidentMappingResult(
            total_csv_rows=total_csv,
            mapped_documents=len(incident_metas),
            mismatches=mismatches,
            is_reconciled=is_reconciled,
        )
