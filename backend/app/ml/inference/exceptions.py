"""
ManuMind AI — Unified Inference Service Exceptions
Department of AI & Data Science — RMK Engineering College

Typed exceptions for model loading, artifact verification, input validation,
concurrency, and execution lifecycle.
"""


class InferenceServiceError(Exception):
    """Base exception for all Unified Inference Service errors."""
    pass


class ModelArtifactNotFoundError(InferenceServiceError):
    """Raised when a required model binary or metadata sidecar is missing on disk."""
    pass


class ArtifactIntegrityError(InferenceServiceError):
    """Raised when an artifact's SHA-256 checksum fails to match the expected digest."""
    pass


class ModelNotLoadedError(InferenceServiceError):
    """Raised when an inference operation is invoked on an unloaded model."""
    pass


class InvalidSensorValueError(InferenceServiceError):
    """Raised when sensor readings contain NaN, Infinity, or out-of-boundary values."""
    pass


class MissingSensorFeatureError(InferenceServiceError):
    """Raised when input sensor readings lack one or more canonical features."""
    pass


class InvalidSequenceLengthError(InferenceServiceError):
    """Raised when a sequence window contains fewer or more than 30 observations."""
    pass


class TimestampOrderingError(InferenceServiceError):
    """Raised when sequence observations violate strict chronological monotonicity."""
    pass


class ImageDecodingError(InferenceServiceError):
    """Raised when an input image cannot be decoded into a valid workpiece tensor."""
    pass


class InferenceTimeoutError(InferenceServiceError):
    """Raised when an inference request exceeds its allocated deadline budget."""
    pass


class ExplanationError(InferenceServiceError):
    """Raised when SHAP or sensor attribution computation fails."""
    pass
