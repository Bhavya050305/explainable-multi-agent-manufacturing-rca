"""
ManuMind AI — RAG Module
Phase 3 Step 2 & Step 3: Ingestion and Chunking Pipelines

Department of AI & Data Science — RMK Engineering College
"""

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.document_loader import DocumentLoader
from backend.app.rag.metadata_parser import MetadataParser
from backend.app.rag.provenance_validator import ProvenanceValidator
from backend.app.rag.ingestion_service import IngestionService
from backend.app.rag.ingestion_report import IngestionReportGenerator

from backend.app.rag.chunking_config import ChunkingConfig, chunking_config
from backend.app.rag.chunk_schemas import (
    ChunkMetadata,
    ChunkRecord,
    ChunkingQualityMetrics,
    ChunkingSummary,
)
from backend.app.rag.text_splitter import TextSplitter, RawSection, SplitChunkResult
from backend.app.rag.metadata_enricher import MetadataEnricher
from backend.app.rag.chunking_service import ChunkingService
from backend.app.rag.chunking_report import ChunkingReportGenerator

from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service
from backend.app.rag.embedding_segment_schemas import (
    EmbeddingSegmentMetadata,
    EmbeddingSegment,
    SegmentationSummary,
)
from backend.app.rag.embedding_segmenter import EmbeddingSegmenter, embedding_segmenter
from backend.app.rag.embedding_model import BGEEmbeddingModel, bge_embedding_model
from backend.app.rag.vector_store import ChromaVectorStore, chroma_vector_store
from backend.app.rag.embedding_service import EmbeddingService, embedding_service

from backend.app.rag.retrieval_config import RetrievalConfig, retrieval_config
from backend.app.rag.retrieval_schemas import (
    RetrievalMode,
    RetrievalFilter,
    RetrievalQuery,
    RetrievalResultItem,
    RetrievalResponse,
)
from backend.app.rag.query_processor import QueryProcessor, query_processor, ProcessedQuery
from backend.app.rag.metadata_filter import MetadataFilterCompiler, metadata_filter_compiler
from backend.app.rag.source_resolver import SourceResolver, source_resolver
from backend.app.rag.retrieval_service import RetrievalService, retrieval_service

from backend.app.rag.schemas import (
    ExecutionMode,
    DocumentType,
    SourceType,
    RawDocument,
    DocumentMetadata,
    IngestionRecord,
    RejectedDocument,
    ManifestReconciliationResult,
    IncidentMappingResult,
    IngestionSummary,
)

from backend.app.rag.exceptions import (
    RAGException,
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileError,
    MetadataParseError,
    MissingFrontMatterError,
    MalformedYAMLError,
    MissingMandatoryMetadataError,
    InvalidMetadataTypeError,
    DuplicateDocumentIDError,
    ProvenanceValidationError,
    MissingDisclaimerError,
    IncidentMappingError,
    ManifestReconciliationError,
)

__all__ = [
    # Ingestion Components
    "RAGConfig",
    "rag_config",
    "DocumentLoader",
    "MetadataParser",
    "ProvenanceValidator",
    "IngestionService",
    "IngestionReportGenerator",
    # Chunking Components
    "ChunkingConfig",
    "chunking_config",
    "ChunkMetadata",
    "ChunkRecord",
    "ChunkingQualityMetrics",
    "ChunkingSummary",
    "TextSplitter",
    "RawSection",
    "SplitChunkResult",
    "MetadataEnricher",
    "ChunkingService",
    "ChunkingReportGenerator",
    # Embedding & Indexing Components
    "TokenizerService",
    "tokenizer_service",
    "EmbeddingSegmentMetadata",
    "EmbeddingSegment",
    "SegmentationSummary",
    "EmbeddingSegmenter",
    "embedding_segmenter",
    "BGEEmbeddingModel",
    "bge_embedding_model",
    "ChromaVectorStore",
    "chroma_vector_store",
    "EmbeddingService",
    "embedding_service",
    # Retrieval Components
    "RetrievalConfig",
    "retrieval_config",
    "RetrievalMode",
    "RetrievalFilter",
    "RetrievalQuery",
    "RetrievalResultItem",
    "RetrievalResponse",
    "QueryProcessor",
    "query_processor",
    "ProcessedQuery",
    "MetadataFilterCompiler",
    "metadata_filter_compiler",
    "SourceResolver",
    "source_resolver",
    "RetrievalService",
    "retrieval_service",
    # Schemas
    "ExecutionMode",
    "DocumentType",
    "SourceType",
    "RawDocument",
    "DocumentMetadata",
    "IngestionRecord",
    "RejectedDocument",
    "ManifestReconciliationResult",
    "IncidentMappingResult",
    "IngestionSummary",
    # Exceptions
    "RAGException",
    "DocumentLoadError",
    "EmptyDocumentError",
    "UnsupportedFileError",
    "MetadataParseError",
    "MissingFrontMatterError",
    "MalformedYAMLError",
    "MissingMandatoryMetadataError",
    "InvalidMetadataTypeError",
    "DuplicateDocumentIDError",
    "ProvenanceValidationError",
    "MissingDisclaimerError",
    "IncidentMappingError",
    "ManifestReconciliationError",
]
