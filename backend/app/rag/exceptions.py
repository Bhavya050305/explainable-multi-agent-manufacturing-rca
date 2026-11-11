"""
ManuMind AI — RAG Ingestion Pipeline Exceptions
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""


class RAGException(Exception):
    """Base exception for all RAG ingestion errors."""

    def __init__(self, message: str, source_path: str | None = None, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.source_path = source_path
        self.field = field

    def __str__(self) -> str:
        ctx = []
        if self.source_path:
            ctx.append(f"path={self.source_path}")
        if self.field:
            ctx.append(f"field={self.field}")
        if ctx:
            return f"[{', '.join(ctx)}] {self.message}"
        return self.message


# Document Loading Exceptions
class DocumentLoadError(RAGException):
    """Raised when discovering or reading a document file fails."""
    pass


class EmptyDocumentError(DocumentLoadError):
    """Raised when a discovered document contains no content."""
    pass


class UnsupportedFileError(DocumentLoadError):
    """Raised when an unsupported file type is encountered."""
    pass


# Metadata Parsing Exceptions
class MetadataParseError(RAGException):
    """Raised when parsing document front matter fails."""
    pass


class MissingFrontMatterError(MetadataParseError):
    """Raised when document lacks standard YAML front matter delimiters."""
    pass


class MalformedYAMLError(MetadataParseError):
    """Raised when YAML front matter has syntax or parsing errors."""
    pass


class MissingMandatoryMetadataError(MetadataParseError):
    """Raised when a required front matter field is absent."""
    pass


class InvalidMetadataTypeError(MetadataParseError):
    """Raised when a front matter field has an invalid data type or enum value."""
    pass


# Identity & Ingestion State Exceptions
class DuplicateDocumentIDError(RAGException):
    """Raised when duplicate document identifiers conflict."""
    pass


# Provenance & Validation Exceptions
class ProvenanceValidationError(RAGException):
    """Raised when document provenance does not comply with established policy."""
    pass


class MissingDisclaimerError(ProvenanceValidationError):
    """Raised when required visible synthetic data disclaimer is absent."""
    pass


class IncidentMappingError(ProvenanceValidationError):
    """Raised when incident document does not map accurately to source maintenance CSV."""
    pass


class ManifestReconciliationError(RAGException):
    """Raised when discovered corpus drifts from corpus_manifest.json."""
    pass
