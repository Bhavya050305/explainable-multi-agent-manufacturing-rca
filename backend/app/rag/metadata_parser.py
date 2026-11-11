"""
ManuMind AI — RAG Metadata Parser
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from typing import Tuple, Dict, Any
import yaml

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.exceptions import (
    MetadataParseError,
    MissingFrontMatterError,
    MalformedYAMLError,
    MissingMandatoryMetadataError,
    InvalidMetadataTypeError,
)
from backend.app.rag.schemas import DocumentMetadata


class MetadataParser:
    """Parses and validates YAML front matter from Markdown documents."""

    def __init__(self, config: RAGConfig = rag_config):
        self.config = config

    def parse(self, raw_content: str, source_path: str) -> Tuple[DocumentMetadata, str]:
        """
        Parse front matter and body from raw Markdown content.
        Returns a tuple of (DocumentMetadata, body_content).
        """
        # Strip potential UTF-8 BOM
        text = raw_content.lstrip("\ufeff")

        # 1. Delimiter check
        if not text.startswith("---"):
            raise MissingFrontMatterError(
                "Document missing opening '---' front matter delimiter",
                source_path=source_path,
                field="frontmatter",
            )

        parts = text.split("---", 2)
        if len(parts) < 3:
            raise MissingFrontMatterError(
                "Document missing closing '---' front matter delimiter",
                source_path=source_path,
                field="frontmatter",
            )

        fm_raw = parts[1]
        body = parts[2]

        # 2. YAML parsing
        try:
            data = yaml.safe_load(fm_raw)
        except yaml.YAMLError as e:
            raise MalformedYAMLError(
                f"YAML parsing error: {e}",
                source_path=source_path,
                field="frontmatter",
            )

        if not isinstance(data, dict):
            raise MalformedYAMLError(
                f"Expected YAML front matter to be a mapping, got {type(data).__name__}",
                source_path=source_path,
                field="frontmatter",
            )

        # 3. Mandatory fields check
        doc_id = data.get("document_id")
        if not doc_id or not isinstance(doc_id, str) or not doc_id.strip():
            raise MissingMandatoryMetadataError(
                "Missing or invalid 'document_id' (must be non-empty string)",
                source_path=source_path,
                field="document_id",
            )

        doc_type = data.get("document_type")
        if not doc_type or doc_type not in self.config.VALID_DOCUMENT_TYPES:
            raise InvalidMetadataTypeError(
                f"Invalid or unsupported 'document_type': {doc_type}. Must be one of {sorted(self.config.VALID_DOCUMENT_TYPES)}",
                source_path=source_path,
                field="document_type",
            )

        source_type = data.get("source_type")
        if not source_type or source_type not in {"SYNTHETIC_DEMONSTRATION", "DERIVED_SYNTHETIC"}:
            raise InvalidMetadataTypeError(
                f"Invalid 'source_type': {source_type}. Must be SYNTHETIC_DEMONSTRATION or DERIVED_SYNTHETIC",
                source_path=source_path,
                field="source_type",
            )

        is_synthetic = data.get("is_synthetic")
        if is_synthetic is not True:
            raise InvalidMetadataTypeError(
                f"'is_synthetic' must be boolean True, got {type(is_synthetic).__name__} ({is_synthetic})",
                source_path=source_path,
                field="is_synthetic",
            )

        title = data.get("title") or data.get("document_name")
        if not title or not isinstance(title, str) or not title.strip():
            raise MissingMandatoryMetadataError(
                "Document must contain a non-empty 'title' or 'document_name'",
                source_path=source_path,
                field="title",
            )

        # 4. Type-specific mandatory fields
        if doc_type == "INCIDENT":
            if not data.get("machine_id"):
                raise MissingMandatoryMetadataError(
                    "Incident documents must specify 'machine_id'",
                    source_path=source_path,
                    field="machine_id",
                )
            if data.get("original_row_index") is None or not isinstance(data.get("original_row_index"), int):
                raise MissingMandatoryMetadataError(
                    "Incident documents must specify integer 'original_row_index'",
                    source_path=source_path,
                    field="original_row_index",
                )
            if not data.get("source_record_id"):
                raise MissingMandatoryMetadataError(
                    "Incident documents must specify 'source_record_id'",
                    source_path=source_path,
                    field="source_record_id",
                )

        elif doc_type == "SOP":
            if not data.get("machine_id"):
                raise MissingMandatoryMetadataError(
                    "SOP documents must specify 'machine_id'",
                    source_path=source_path,
                    field="machine_id",
                )
            if not data.get("machine_type"):
                raise MissingMandatoryMetadataError(
                    "SOP documents must specify 'machine_type'",
                    source_path=source_path,
                    field="machine_type",
                )

        elif doc_type == "TROUBLESHOOTING":
            if not data.get("fault_category"):
                raise MissingMandatoryMetadataError(
                    "Troubleshooting documents must specify 'fault_category'",
                    source_path=source_path,
                    field="fault_category",
                )

        # 5. Type validations on optional fields
        if "criticality" in data and data["criticality"] is not None and not isinstance(data["criticality"], int):
            raise InvalidMetadataTypeError(
                f"'criticality' must be an integer, got {type(data['criticality']).__name__}",
                source_path=source_path,
                field="criticality",
            )

        if "production_impact" in data and data["production_impact"] is not None and not isinstance(data["production_impact"], int):
            raise InvalidMetadataTypeError(
                f"'production_impact' must be an integer, got {type(data['production_impact']).__name__}",
                source_path=source_path,
                field="production_impact",
            )

        # 6. Extract known fields & preserve extra
        known_keys = {
            "document_id",
            "document_name",
            "title",
            "document_type",
            "document_version",
            "version",
            "source_type",
            "is_synthetic",
            "machine_id",
            "machine_type",
            "component",
            "fault_category",
            "target_machine",
            "applicable_scope",
            "source_name",
            "source_record_id",
            "original_row_index",
            "event_date",
            "created_at",
            "generation_method",
            "review_status",
            "operational_disclaimer",
            "criticality",
            "production_impact",
        }
        extra_metadata: Dict[str, Any] = {
            k: v for k, v in data.items() if k not in known_keys
        }

        metadata = DocumentMetadata(
            document_id=doc_id,
            title=title,
            document_type=doc_type,
            document_version=str(data.get("document_version") or data.get("version") or "1.0.0"),
            source_type=source_type,
            is_synthetic=bool(is_synthetic),
            machine_id=str(data.get("machine_id")) if data.get("machine_id") is not None else None,
            machine_type=str(data.get("machine_type")) if data.get("machine_type") is not None else None,
            component=str(data.get("component")) if data.get("component") is not None else None,
            fault_category=str(data.get("fault_category")) if data.get("fault_category") is not None else None,
            target_machine=str(data.get("target_machine")) if data.get("target_machine") is not None else None,
            applicable_scope=str(data.get("applicable_scope")) if data.get("applicable_scope") is not None else None,
            source_name=str(data.get("source_name")) if data.get("source_name") is not None else None,
            source_record_id=str(data.get("source_record_id")) if data.get("source_record_id") is not None else None,
            original_row_index=data.get("original_row_index"),
            event_date=str(data.get("event_date")) if data.get("event_date") is not None else None,
            created_at=str(data.get("created_at")) if data.get("created_at") is not None else None,
            generation_method=str(data.get("generation_method")) if data.get("generation_method") is not None else None,
            review_status=str(data.get("review_status")) if data.get("review_status") is not None else None,
            operational_disclaimer=str(data.get("operational_disclaimer")) if data.get("operational_disclaimer") is not None else None,
            criticality=data.get("criticality"),
            production_impact=data.get("production_impact"),
            extra_metadata=extra_metadata,
        )

        return metadata, body
