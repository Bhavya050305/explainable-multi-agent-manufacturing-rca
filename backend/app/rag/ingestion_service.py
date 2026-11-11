"""
ManuMind AI — RAG Ingestion Service
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from collections import Counter
import hashlib
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.document_loader import DocumentLoader
from backend.app.rag.exceptions import (
    DuplicateDocumentIDError,
    MetadataParseError,
    ProvenanceValidationError,
)
from backend.app.rag.metadata_parser import MetadataParser
from backend.app.rag.provenance_validator import ProvenanceValidator
from backend.app.rag.schemas import (
    ExecutionMode,
    IngestionRecord,
    IngestionSummary,
    RawDocument,
    RejectedDocument,
)


class IngestionService:
    """Orchestrates document discovery, validation, normalization, and in-memory registration."""

    def __init__(self, config: RAGConfig = rag_config):
        self.config = config
        self.loader = DocumentLoader(config)
        self.parser = MetadataParser(config)
        self.validator = ProvenanceValidator(config)

        # In-memory document registry: document_id -> IngestionRecord
        self._registry: Dict[str, IngestionRecord] = {}

    @property
    def registry(self) -> Dict[str, IngestionRecord]:
        """Read-only view of the in-memory document registry."""
        return dict(self._registry)

    def clear_registry(self) -> None:
        """Reset the in-memory document registry."""
        self._registry.clear()

    @staticmethod
    def normalize_content(body: str) -> str:
        """
        Deterministic content normalization rules:
        1. Replace CRLF and CR with LF.
        2. Strip trailing whitespace from every individual line.
        3. Strip leading and trailing newlines/whitespace from the whole text.
        """
        # Standardize line endings
        normalized = body.replace("\r\n", "\n").replace("\r", "\n")
        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in normalized.split("\n")]
        # Strip leading and trailing whitespace from the document
        return "\n".join(lines).strip()

    @classmethod
    def compute_content_hash(cls, body: str) -> str:
        """Calculate SHA-256 hash of normalized content body."""
        normalized = cls.normalize_content(body)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def process_document(
        self, raw_doc: RawDocument, seen_ids: Dict[str, Tuple[str, str]]
    ) -> IngestionRecord:
        """
        Parse, validate, normalize, and construct an IngestionRecord.
        seen_ids tracks {document_id: (source_path, content_hash)} to detect duplicates within a batch.
        """
        source_path = raw_doc.source_path

        # 1. Parse YAML front matter
        metadata, body = self.parser.parse(raw_doc.raw_content, source_path)

        # 2. Check within-batch duplicate IDs
        doc_id = metadata.document_id
        content_hash = self.compute_content_hash(body)

        if doc_id in seen_ids:
            prev_path, prev_hash = seen_ids[doc_id]
            if prev_path != source_path or prev_hash != content_hash:
                raise DuplicateDocumentIDError(
                    f"Duplicate conflicting document_id '{doc_id}' found in '{source_path}', originally seen in '{prev_path}'",
                    source_path=source_path,
                    field="document_id",
                )

        seen_ids[doc_id] = (source_path, content_hash)

        # 3. Validate provenance
        self.validator.validate_provenance(metadata, source_path)

        # 4. Validate synthetic disclaimer in body
        self.validator.validate_disclaimer(body, source_path)

        # 5. Validate incident mapping if applicable
        if metadata.document_type == "INCIDENT":
            self.validator.validate_incident_mapping(metadata, source_path)

        # 6. Construct structured record (content preserves original body text)
        return IngestionRecord(
            document_id=doc_id,
            title=metadata.title,
            document_type=metadata.document_type,
            source_type=metadata.source_type,
            is_synthetic=metadata.is_synthetic,
            machine_id=metadata.machine_id,
            machine_type=metadata.machine_type,
            component=metadata.component,
            fault_category=metadata.fault_category,
            version=metadata.document_version,
            source_path=source_path,
            content=body,
            content_hash=content_hash,
            raw_file_hash=raw_doc.raw_file_hash,
            metadata=metadata,
        )

    def ingest(
        self,
        execution_mode: ExecutionMode = ExecutionMode.IN_MEMORY_INGESTION,
        corpus_dir: Path | None = None,
    ) -> IngestionSummary:
        """
        Execute document discovery, validation, and ingestion pipeline.
        ExecutionMode.VALIDATION_ONLY: No registry mutation.
        ExecutionMode.IN_MEMORY_INGESTION: In-memory registry mutation with idempotency.
        """
        start_time = time.perf_counter()
        warnings: List[str] = []
        errors: List[str] = []

        # 1. Document discovery and raw file loading
        loaded_raw_docs, rejected_docs = self.loader.load_all(corpus_dir)
        total_discovered = len(loaded_raw_docs) + len(rejected_docs)

        # 2. Reconcile loaded files against corpus_manifest.json
        manifest_result = self.validator.reconcile_with_manifest(loaded_raw_docs)
        if not manifest_result.is_reconciled:
            warnings.append(
                f"Manifest reconciliation discrepancy: missing={len(manifest_result.missing_on_disk)}, "
                f"untracked={len(manifest_result.untracked_on_disk)}, hash_mismatches={len(manifest_result.hash_mismatches)}"
            )

        # 3. Parse, validate, and build records
        seen_batch_ids: Dict[str, Tuple[str, str]] = {}
        valid_records: List[IngestionRecord] = []
        duplicate_ids_count = 0
        provenance_passed = 0
        disclaimer_passed = 0

        doc_type_counts: Counter = Counter()
        machine_counts: Counter = Counter()
        fault_counts: Counter = Counter()

        for raw_doc in loaded_raw_docs:
            try:
                record = self.process_document(raw_doc, seen_batch_ids)
                valid_records.append(record)

                provenance_passed += 1
                disclaimer_passed += 1
                doc_type_counts[record.document_type] += 1
                if record.machine_id:
                    machine_counts[record.machine_id] += 1
                if record.fault_category:
                    fault_counts[record.fault_category] += 1

            except DuplicateDocumentIDError as e:
                duplicate_ids_count += 1
                errors.append(str(e))
                rejected_docs.append(
                    RejectedDocument(
                        source_path=raw_doc.source_path,
                        document_id=e.field,
                        rejection_reason="DuplicateDocumentIDError",
                        error_details=str(e),
                        phase="duplicate_detection",
                    )
                )
            except (MetadataParseError, ProvenanceValidationError) as e:
                errors.append(str(e))
                rejected_docs.append(
                    RejectedDocument(
                        source_path=raw_doc.source_path,
                        document_id=getattr(e, "field", None),
                        rejection_reason=e.__class__.__name__,
                        error_details=str(e),
                        phase="validation",
                    )
                )

        # 4. Global incident reconciliation against CSV
        valid_metadata = [r.metadata for r in valid_records]
        incident_result = self.validator.reconcile_all_incidents(valid_metadata)
        if not incident_result.is_reconciled:
            errors.append(
                f"Incident mapping reconciliation failed: {len(incident_result.mismatches)} mismatches"
            )

        # 5. In-Memory Ingestion Mode handling (idempotent registration)
        if execution_mode == ExecutionMode.IN_MEMORY_INGESTION:
            # Deterministic ordering by document_id
            for record in sorted(valid_records, key=lambda r: r.document_id):
                doc_id = record.document_id
                if doc_id in self._registry:
                    existing = self._registry[doc_id]
                    if existing.content_hash == record.content_hash and existing.source_path == record.source_path:
                        # Idempotent re-ingestion, unchanged document
                        continue
                    else:
                        raise DuplicateDocumentIDError(
                            f"Conflicting document identity in registry: {doc_id} has different hash or path",
                            source_path=record.source_path,
                            field="document_id",
                        )
                else:
                    self._registry[doc_id] = record

        duration = time.perf_counter() - start_time

        return IngestionSummary(
            execution_mode=execution_mode,
            total_discovered=total_discovered,
            total_parsed=len(loaded_raw_docs),
            total_valid=len(valid_records),
            total_rejected=len(rejected_docs),
            duplicate_ids_count=duplicate_ids_count,
            provenance_passed=provenance_passed,
            disclaimer_passed=disclaimer_passed,
            incident_mappings_reconciled=incident_result.mapped_documents,
            manifest_reconciliation=manifest_result,
            incident_mapping_result=incident_result,
            document_type_distribution=dict(doc_type_counts),
            machine_distribution=dict(machine_counts),
            fault_category_distribution=dict(fault_counts),
            duration_seconds=round(duration, 4),
            rejected_documents=rejected_docs,
            warnings=warnings,
            errors=errors,
        )
