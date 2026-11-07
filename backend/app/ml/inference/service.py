"""
ManuMind AI — Unified Inference Service Facade
Department of AI & Data Science — RMK Engineering College

Production orchestration layer integrating:
1. Isolation Forest tabular sensor anomaly scoring
2. LSTM Autoencoder sequence reconstruction anomaly detection
3. Step 4 sensor-level MSE reconstruction attribution
4. Step 6 Kernel SHAP game-theoretic anomaly intensity explainability
5. Step 7 Compact ResNet-18 optical workpiece defect classification

Thread-safe, modality-decoupled, with strict input validation and graceful degradation.
"""

import io
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from PIL import Image

from backend.app.ml.inference.config import (
    CANONICAL_FEATURES,
    DEFECT_RECOMMENDATIONS,
    InferenceConfig,
    MODEL_ID_IF,
    MODEL_ID_LSTM,
    MODEL_ID_RESNET,
    MODEL_ID_SHAP,
    MODEL_ID_ATTRIBUTION,
)
from backend.app.ml.inference.exceptions import (
    ImageDecodingError,
    InvalidSensorValueError,
    InvalidSequenceLengthError,
    MissingSensorFeatureError,
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

logger = logging.getLogger("UnifiedInferenceService")


class UnifiedInferenceService:
    """
    Unified multi-modal inference facade orchestrating tabular, temporal,
    explainability, and vision machine learning models.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        config: Optional[InferenceConfig] = None
    ) -> None:
        self.config = config or InferenceConfig()
        self.registry = registry or ModelRegistry.get_instance(self.config)

        # Thread synchronization locks
        # SHAP KernelExplainer mutates internal state during coalition evaluation; serialized per-worker
        self._shap_lock = threading.Lock()
        # TensorFlow execution synchronization lock for safe multithreaded forward passes
        self._tf_lock = threading.Lock()

    def _extract_canonical_features(self, reading: Union[SensorReadingInput, Dict[str, Any]]) -> np.ndarray:
        """
        Extracts 5 sensor values strictly adhering to canonical feature ordering:
        [vibration, temperature, pressure, current, rpm].
        Resistant to dictionary/JSON key permutation.
        """
        if isinstance(reading, SensorReadingInput):
            values = [
                reading.vibration,
                reading.temperature,
                reading.pressure,
                reading.current,
                reading.rpm
            ]
        elif isinstance(reading, dict):
            missing = [f for f in self.config.canonical_features if f not in reading]
            if missing:
                raise MissingSensorFeatureError(f"Missing required sensor feature(s): {missing}")
            values = [float(reading[f]) for f in self.config.canonical_features]
        else:
            raise TypeError(f"Expected SensorReadingInput or dict, got {type(reading)}")

        arr = np.asarray(values, dtype=np.float64)
        if not np.all(np.isfinite(arr)):
            raise InvalidSensorValueError("Sensor observation contains non-finite values (NaN or Inf).")

        return arr.reshape(1, -1)

    def predict_sensor_anomaly(
        self,
        input_data: Union[SensorReadingInput, Dict[str, Any]],
        explain: bool = False
    ) -> SensorAnomalyResponse:
        """
        Point-in-time tabular sensor anomaly inference using Isolation Forest.

        Processing:
        1. Validate input and extract canonical features.
        2. Apply StandardScaler strictly via .transform().
        3. Evaluate anomaly intensity: f(X) = -decision_function(X).
        4. Compare against frozen calibrated threshold (0.0269).
        5. Optionally compute Kernel SHAP attributions with graceful failure handling.
        """
        # Validate into typed schema if dict
        if isinstance(input_data, dict):
            input_obj = SensorReadingInput(**input_data)
        else:
            input_obj = input_data

        raw_vec = self._extract_canonical_features(input_obj)

        # Scale observation using frozen scaler
        scaler = self.registry.get_scaler()
        scaled_vec = scaler.transform(raw_vec)

        # Compute continuous score: -decision_function(X)
        if_predictor = self.registry.get_isolation_forest()
        score = float(if_predictor.score(scaled_vec)[0])
        threshold = self.config.if_threshold
        is_anomaly = bool(score > threshold)

        # Handle optional SHAP explainability
        explanation_status = ExplanationStatus.NOT_REQUESTED
        shap_explanation = None

        if explain:
            try:
                shap_explanation = self.explain_sensor_shap(scaled_vec, is_scaled=True)
                explanation_status = ExplanationStatus.AVAILABLE
            except Exception as e:
                logger.error("Optional SHAP explanation failed: %s", e, exc_info=True)
                explanation_status = ExplanationStatus.FAILED
                shap_explanation = {
                    "error": str(e),
                    "explanation_status": ExplanationStatus.FAILED.value
                }

        return SensorAnomalyResponse(
            machine_id=input_obj.machine_id,
            timestamp=input_obj.timestamp,
            anomaly_score=round(score, 6),
            threshold=threshold,
            is_anomaly=is_anomaly,
            model_id=MODEL_ID_IF,
            explanation_status=explanation_status,
            shap_explanation=shap_explanation
        )

    def predict_sequence_anomaly(
        self,
        input_data: Union[SequenceWindowInput, Dict[str, Any]],
        explain: bool = False
    ) -> SequenceAnomalyResponse:
        """
        Temporal sequence anomaly inference over 30-step window using LSTM Autoencoder.

        Processing:
        1. Validate window contains exactly 30 observations.
        2. Verify timestamp monotonicity.
        3. Scale (30, 5) observations using frozen scaler.
        4. Reconstruct sequence with LSTM Autoencoder.
        5. Compute sequence reconstruction MSE: mean((X - X_recon)^2).
        6. Compare against frozen threshold (0.901464).
        7. Optionally compute Step 4 sensor attribution with graceful degradation.
        """
        if isinstance(input_data, dict):
            window_obj = SequenceWindowInput(**input_data)
        else:
            window_obj = input_data

        if len(window_obj.readings) != self.config.sequence_length:
            raise InvalidSequenceLengthError(
                f"Sequence must contain exactly {self.config.sequence_length} readings, "
                f"got {len(window_obj.readings)}"
            )

        # Construct raw (30, 5) matrix
        raw_rows = [self._extract_canonical_features(r)[0] for r in window_obj.readings]
        raw_mat = np.array(raw_rows, dtype=np.float64)  # (30, 5)

        # Scale features
        scaler = self.registry.get_scaler()
        scaled_mat = scaler.transform(raw_mat).astype(np.float32)  # (30, 5)
        seq_tensor = np.expand_dims(scaled_mat, axis=0)  # (1, 30, 5)

        # Compute sequence reconstruction error
        lstm_predictor = self.registry.get_lstm_autoencoder()
        with self._tf_lock:
            recon_error = float(lstm_predictor.compute_reconstruction_error(seq_tensor)[0])

        threshold = self.config.lstm_threshold
        is_anomaly = bool(recon_error > threshold)

        # Handle optional sensor-level attribution
        attribution_status = ExplanationStatus.NOT_REQUESTED
        sensor_attribution = None

        if explain:
            try:
                sensor_attribution = self.explain_sequence_attribution(
                    seq_tensor,
                    window_id=window_obj.window_id,
                    machine_id=window_obj.machine_id
                )
                attribution_status = ExplanationStatus.AVAILABLE
            except Exception as e:
                logger.error("Optional sensor attribution failed: %s", e, exc_info=True)
                attribution_status = ExplanationStatus.FAILED
                sensor_attribution = {
                    "error": str(e),
                    "attribution_status": ExplanationStatus.FAILED.value
                }

        return SequenceAnomalyResponse(
            machine_id=window_obj.machine_id,
            window_id=window_obj.window_id,
            reconstruction_error=round(recon_error, 6),
            threshold=threshold,
            is_anomaly=is_anomaly,
            model_id=MODEL_ID_LSTM,
            attribution_status=attribution_status,
            sensor_attribution=sensor_attribution
        )

    def explain_sequence_attribution(
        self,
        sequence_tensor: np.ndarray,
        window_id: Optional[str] = None,
        machine_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 4 Analytical MSE Reconstruction Attribution.
        Computes per-sensor reconstruction errors, normalized contribution percentages,
        and unscaled physical engineering residuals.
        """
        arr = np.asarray(sequence_tensor, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)
        if arr.shape[1:] != (self.config.sequence_length, self.config.n_features):
            raise ValueError(
                f"Expected sequence tensor shape (N, {self.config.sequence_length}, "
                f"{self.config.n_features}), got {arr.shape}"
            )

        attr_explainer = self.registry.get_lstm_attribution_explainer()
        with self._tf_lock:
            result = attr_explainer.explain_sequences(arr)

        feature_names = self.config.canonical_features
        feature_mse = {
            feat: round(float(result.feature_mse[0, i]), 6)
            for i, feat in enumerate(feature_names)
        }
        feature_pct = {
            feat: round(float(result.feature_contribution_pct[0, i]), 4)
            for i, feat in enumerate(feature_names)
        }
        unscaled_res = {
            feat: round(float(result.unscaled_residuals[0, i]), 4)
            for i, feat in enumerate(feature_names)
        }

        return {
            "window_id": window_id,
            "machine_id": machine_id,
            "feature_mse": feature_mse,
            "feature_contribution_pct": feature_pct,
            "dominant_feature": result.dominant_features[0],
            "top2_features": result.top2_features[0],
            "unscaled_residuals": unscaled_res,
            "total_sequence_error": round(float(result.total_sequence_error[0]), 6),
            "sequence_mean_mse": round(float(result.sequence_mean_mse[0]), 6),
            "method": "reconstruction_mean_squared_error",
            "attribution_status": ExplanationStatus.AVAILABLE.value,
            "limitations": "Mathematical attribution reflects reconstruction discrepancy, not verified physical failure root cause."
        }

    def explain_sensor_shap(
        self,
        sensor_values: Union[List[float], Dict[str, float], np.ndarray, SensorReadingInput],
        is_scaled: bool = False
    ) -> Dict[str, Any]:
        """
        Step 6 Kernel SHAP Game-Theoretic Additive Feature Attribution.
        Guarantees strict additivity: |f(x) - (E[f] + sum(phi))| < 1e-6.
        Protected by dedicated per-worker serialization lock.
        """
        if isinstance(sensor_values, SensorReadingInput):
            raw_vec = self._extract_canonical_features(sensor_values)
            scaler = self.registry.get_scaler()
            scaled_vec = scaler.transform(raw_vec)
        elif isinstance(sensor_values, dict):
            raw_vec = self._extract_canonical_features(sensor_values)
            scaler = self.registry.get_scaler()
            scaled_vec = scaler.transform(raw_vec)
        elif isinstance(sensor_values, (list, np.ndarray)):
            arr = np.asarray(sensor_values, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            if not is_scaled:
                scaler = self.registry.get_scaler()
                scaled_vec = scaler.transform(arr)
            else:
                scaled_vec = arr
        else:
            raise TypeError(f"Unsupported sensor values input type: {type(sensor_values)}")

        shap_explainer = self.registry.get_shap_explainer()
        with self._shap_lock:
            explanation = shap_explainer.explain_observation(scaled_vec)

        # Ensure explanation status is marked
        explanation["explanation_status"] = ExplanationStatus.AVAILABLE.value
        return explanation

    def predict_defect_image(
        self,
        image_input: Union[str, Path, Image.Image, np.ndarray, bytes],
        image_name: Optional[str] = None
    ) -> DefectClassificationResponse:
        """
        Step 7 Optical Workpiece Defect Classification using Compact ResNet-18.
        Supports filepaths, PIL Images, numpy arrays, and raw image byte buffers.
        """
        processed_input = image_input
        name_override = image_name

        if isinstance(image_input, bytes):
            try:
                processed_input = Image.open(io.BytesIO(image_input))
                if name_override is None:
                    name_override = "workpiece_buffer.bmp"
            except Exception as e:
                raise ImageDecodingError(f"Failed to decode image bytes into valid workpiece image: {e}")

        defect_service = self.registry.get_defect_classifier()
        with self._tf_lock:
            result = defect_service.predict_image(processed_input, image_name=name_override)

        return DefectClassificationResponse(
            image_name=result["image_name"],
            defect_type=result["defect_type"],
            raw_defect_class=result["raw_defect_class"],
            confidence=result["confidence"],
            class_probabilities=result["class_probabilities"],
            is_defective=result["is_defective"],
            affected_machine_id=result["affected_machine_id"],
            batch_number=result["batch_number"],
            recommendation=result["recommendation"],
            model_id=MODEL_ID_RESNET
        )

    def predict_unified(self, request: UnifiedInferenceRequest) -> UnifiedInferenceResponse:
        """
        Unified multi-modal orchestration endpoint.
        Executes requested modalities without executing unrequested models.
        """
        t0 = time.perf_counter()
        warnings: List[str] = []

        sensor_res: Optional[SensorAnomalyResponse] = None
        seq_res: Optional[SequenceAnomalyResponse] = None
        defect_res: Optional[DefectClassificationResponse] = None

        # 1. Tabular sensor anomaly
        if request.sensor_reading is not None:
            try:
                sensor_res = self.predict_sensor_anomaly(
                    request.sensor_reading,
                    explain=request.include_shap
                )
            except Exception as e:
                logger.error("Unified sensor anomaly evaluation failed: %s", e)
                warnings.append(f"Sensor inference failed: {str(e)}")

        # 2. Sequence anomaly
        if request.sequence_window is not None:
            try:
                seq_res = self.predict_sequence_anomaly(
                    request.sequence_window,
                    explain=request.include_attribution
                )
            except Exception as e:
                logger.error("Unified sequence anomaly evaluation failed: %s", e)
                warnings.append(f"Sequence inference failed: {str(e)}")

        # 3. Defect classification
        if request.defect_image is not None:
            try:
                img_inp = None
                if request.defect_image.image_path is not None:
                    img_inp = request.defect_image.image_path
                elif request.defect_image.image_bytes is not None:
                    img_inp = request.defect_image.image_bytes

                if img_inp is not None:
                    defect_res = self.predict_defect_image(
                        img_inp,
                        image_name=request.defect_image.image_name
                    )
                else:
                    warnings.append("Defect image input provided without image_path or image_bytes.")
            except Exception as e:
                logger.error("Unified defect classification failed: %s", e)
                warnings.append(f"Defect vision inference failed: {str(e)}")

        execution_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        data_quality_status = "OK" if not warnings else "PARTIAL_EXECUTION_WARNING"

        return UnifiedInferenceResponse(
            sensor_result=sensor_res,
            sequence_result=seq_res,
            defect_result=defect_res,
            execution_time_ms=execution_time_ms,
            data_quality_status=data_quality_status,
            warnings=warnings
        )
