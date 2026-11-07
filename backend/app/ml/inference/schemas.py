"""
ManuMind AI — Unified Inference Pydantic Schemas
Department of AI & Data Science — RMK Engineering College

Strict Pydantic v2 contracts for requests, responses, and validation rules.
Rejects non-finite values, unknown fields, and maintains semantic distinction
between anomaly intensity, reconstruction MSE, and uncalibrated vision scores.
"""

import math
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.ml.inference.config import (
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    LSTM_AUTOENCODER_FROZEN_THRESHOLD,
    MODEL_ID_IF,
    MODEL_ID_LSTM,
    MODEL_ID_RESNET,
)
from backend.app.ml.inference.exceptions import (
    InvalidSensorValueError,
    InvalidSequenceLengthError,
    TimestampOrderingError,
)


class ExplanationStatus(str, Enum):
    """Explicit status tracking for optional explainability outputs."""
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"
    NOT_REQUESTED = "NOT_REQUESTED"


class SensorReadingInput(BaseModel):
    """
    Input schema for tabular sensor observation.
    Rejects extra fields and non-finite values (NaN, +Inf, -Inf).
    """
    model_config = ConfigDict(extra="forbid")

    vibration: float = Field(..., description="Vibration RMS velocity in mm/s")
    temperature: float = Field(..., description="Operating temperature in °C")
    pressure: float = Field(..., description="Process hydraulic/pneumatic pressure in bar")
    current: float = Field(..., description="Spindle motor current in Amperes")
    rpm: float = Field(..., description="Rotational speed in RPM")
    timestamp: Optional[datetime] = Field(None, description="ISO timestamp of observation")
    machine_id: Optional[str] = Field(None, description="Manufacturing machine identifier")

    @field_validator("vibration", "temperature", "pressure", "current", "rpm")
    @classmethod
    def validate_finite_sensor_value(cls, v: float) -> float:
        """Ensures sensor values are real finite numbers."""
        if math.isnan(v) or math.isinf(v):
            raise InvalidSensorValueError(f"Sensor value must be finite; received {v}")
        return float(v)


class SequenceWindowInput(BaseModel):
    """
    Input schema for temporal sequence anomaly detection.
    Requires exactly 30 chronological readings.
    """
    model_config = ConfigDict(extra="forbid")

    machine_id: str = Field(..., description="Manufacturing asset identifier")
    readings: List[SensorReadingInput] = Field(
        ...,
        min_length=30,
        max_length=30,
        description="Chronological window of exactly 30 sensor observations"
    )
    window_id: Optional[str] = Field(None, description="Optional sliding-window identifier")

    @model_validator(mode="after")
    def validate_sequence_structure(self) -> "SequenceWindowInput":
        """Validates sequence length and verifies chronological ordering if timestamps exist."""
        if len(self.readings) != 30:
            raise InvalidSequenceLengthError(
                f"Expected exactly 30 observations, got {len(self.readings)}"
            )

        # Validate non-decreasing timestamps if provided
        timestamps = [r.timestamp for r in self.readings if r.timestamp is not None]
        if len(timestamps) == len(self.readings):
            for i in range(1, len(timestamps)):
                if timestamps[i] < timestamps[i - 1]:
                    raise TimestampOrderingError(
                        f"Timestamps must be non-decreasing; reading at index {i} "
                        f"({timestamps[i]}) preceded by index {i - 1} ({timestamps[i - 1]})"
                    )

        return self


class DefectImageInput(BaseModel):
    """
    Input schema for optical workpiece inspection.
    Accepts filepath, raw image bytes, or pre-extracted array representation.
    """
    model_config = ConfigDict(extra="forbid")

    image_path: Optional[str] = Field(None, description="Filesystem path to workpiece image")
    image_bytes: Optional[bytes] = Field(None, description="Raw binary image payload")
    image_name: Optional[str] = Field(None, description="Identifier or filename for workpiece")


class UnifiedInferenceRequest(BaseModel):
    """
    Optional composite request allowing arbitrary combinations of modalities.
    """
    model_config = ConfigDict(extra="forbid")

    sensor_reading: Optional[SensorReadingInput] = Field(
        None, description="Single tabular sensor observation"
    )
    sequence_window: Optional[SequenceWindowInput] = Field(
        None, description="30-step temporal sensor sequence window"
    )
    defect_image: Optional[DefectImageInput] = Field(
        None, description="Optical inspection workpiece image"
    )
    include_shap: bool = Field(
        False, description="Flag to generate Kernel SHAP explanations for sensor reading"
    )
    include_attribution: bool = Field(
        False, description="Flag to generate reconstruction MSE attribution for sequence"
    )


class SensorAnomalyResponse(BaseModel):
    """
    Output contract for point-in-time sensor anomaly scoring.
    Maintains continuous anomaly score semantics (-decision_function).
    """
    machine_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    anomaly_score: float = Field(..., description="Continuous anomaly score (-decision_function)")
    threshold: float = Field(
        default=ISOLATION_FOREST_FROZEN_THRESHOLD,
        description="Frozen calibrated decision threshold"
    )
    is_anomaly: bool = Field(..., description="True if anomaly_score > threshold")
    model_id: str = Field(default=MODEL_ID_IF, description="Model identifier")
    explanation_status: ExplanationStatus = Field(
        default=ExplanationStatus.NOT_REQUESTED,
        description="Status of optional SHAP explanation"
    )
    shap_explanation: Optional[Dict[str, Any]] = Field(
        None, description="Additive game-theoretic SHAP attributions"
    )


class SequenceAnomalyResponse(BaseModel):
    """
    Output contract for temporal sequence anomaly detection.
    Maintains continuous sequence reconstruction MSE semantics.
    """
    machine_id: str
    window_id: Optional[str] = None
    reconstruction_error: float = Field(..., description="Mean squared reconstruction error")
    threshold: float = Field(
        default=LSTM_AUTOENCODER_FROZEN_THRESHOLD,
        description="Frozen empirical p99 reconstruction threshold"
    )
    is_anomaly: bool = Field(..., description="True if reconstruction_error > threshold")
    model_id: str = Field(default=MODEL_ID_LSTM, description="Model identifier")
    attribution_status: ExplanationStatus = Field(
        default=ExplanationStatus.NOT_REQUESTED,
        description="Status of optional sensor attribution"
    )
    sensor_attribution: Optional[Dict[str, Any]] = Field(
        None, description="Per-channel MSE reconstruction attribution and contributions"
    )


class DefectClassificationResponse(BaseModel):
    """
    Output contract for workpiece optical defect inspection.
    Scores are explicitly documented as uncalibrated model outputs on synthetic crops.
    """
    image_name: str
    defect_type: str = Field(..., description="Human-readable defect label")
    raw_defect_class: str = Field(..., description="Canonical class identifier")
    confidence: float = Field(..., description="Uncalibrated model Softmax score")
    class_probabilities: Dict[str, float] = Field(
        ..., description="Full 4-class Softmax score distribution"
    )
    is_defective: bool = Field(..., description="True if defect != 'normal_surface'")
    affected_machine_id: str = Field(..., description="Machine/batch provenance identifier")
    batch_number: str = Field(..., description="Production batch identifier")
    recommendation: str = Field(..., description="Actionable manufacturing maintenance guideline")
    model_id: str = Field(default=MODEL_ID_RESNET, description="Model identifier")


class UnifiedInferenceResponse(BaseModel):
    """
    Output contract for unified multi-modal inference execution.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sensor_result: Optional[SensorAnomalyResponse] = None
    sequence_result: Optional[SequenceAnomalyResponse] = None
    defect_result: Optional[DefectClassificationResponse] = None
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")
    data_quality_status: str = Field(default="OK", description="Data validation status")
    warnings: List[str] = Field(default_factory=list, description="Diagnostic warnings")
