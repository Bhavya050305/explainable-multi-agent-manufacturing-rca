"""
ManuMind AI — Unified Inference Service Package
Department of AI & Data Science — RMK Engineering College

Exposes production facades, process-local model registry, Pydantic schemas,
and typed inference exceptions.
"""

from backend.app.ml.inference.config import (
    CANONICAL_FEATURES,
    DEFECT_CLASSES,
    DEFECT_RECOMMENDATIONS,
    FEATURE_UNITS,
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    LSTM_AUTOENCODER_FROZEN_THRESHOLD,
    InferenceConfig,
)
from backend.app.ml.inference.exceptions import (
    ArtifactIntegrityError,
    ExplanationError,
    ImageDecodingError,
    InferenceServiceError,
    InferenceTimeoutError,
    InvalidSensorValueError,
    InvalidSequenceLengthError,
    MissingSensorFeatureError,
    ModelArtifactNotFoundError,
    ModelNotLoadedError,
    TimestampOrderingError,
)
from backend.app.ml.inference.registry import ModelRegistry
from backend.app.ml.inference.schemas import (
    DefectClassificationResponse,
    DefectImageInput,
    ExplanationStatus,
    SensorAnomalyResponse,
    SensorReadingInput,
    SequenceAnomalyResponse,
    SequenceWindowInput,
    UnifiedInferenceRequest,
    UnifiedInferenceResponse,
)
from backend.app.ml.inference.service import UnifiedInferenceService

__all__ = [
    # Facade & Registry
    "UnifiedInferenceService",
    "ModelRegistry",
    "InferenceConfig",
    # Constants
    "CANONICAL_FEATURES",
    "FEATURE_UNITS",
    "DEFECT_CLASSES",
    "DEFECT_RECOMMENDATIONS",
    "ISOLATION_FOREST_FROZEN_THRESHOLD",
    "LSTM_AUTOENCODER_FROZEN_THRESHOLD",
    # Schemas
    "ExplanationStatus",
    "SensorReadingInput",
    "SequenceWindowInput",
    "DefectImageInput",
    "UnifiedInferenceRequest",
    "SensorAnomalyResponse",
    "SequenceAnomalyResponse",
    "DefectClassificationResponse",
    "UnifiedInferenceResponse",
    # Exceptions
    "InferenceServiceError",
    "ModelArtifactNotFoundError",
    "ArtifactIntegrityError",
    "ModelNotLoadedError",
    "InvalidSensorValueError",
    "MissingSensorFeatureError",
    "InvalidSequenceLengthError",
    "TimestampOrderingError",
    "ImageDecodingError",
    "InferenceTimeoutError",
    "ExplanationError",
]
