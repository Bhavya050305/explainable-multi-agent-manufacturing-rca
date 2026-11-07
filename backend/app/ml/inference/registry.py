"""
ManuMind AI — Unified Model Registry
Department of AI & Data Science — RMK Engineering College

Process-local singleton managing model lifecycle, thread-safe lazy loading,
cryptographic SHA-256 integrity verification, and pre-warming routines.
"""

import copy
import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

from backend.app.ml.inference.config import (
    InferenceConfig,
    EXPECTED_ARTIFACT_HASHES,
    MODEL_ID_IF,
    MODEL_ID_LSTM,
    MODEL_ID_RESNET,
    MODEL_ID_SHAP,
    MODEL_ID_ATTRIBUTION,
)
from backend.app.ml.inference.exceptions import (
    ArtifactIntegrityError,
    ModelArtifactNotFoundError,
    ModelNotLoadedError,
)
from backend.app.ml.isolation_forest.predict import IsolationForestPredictor
from backend.app.ml.lstm_autoencoder.predict import LSTMAutoencoderPredictor
from backend.app.ml.sensor_attribution.lstm_attribution import LSTMAttributionExplainer
from backend.app.ml.shap_explainability.config import ShapExplainerConfig
from backend.app.ml.shap_explainability.explainer import IsolationForestShapExplainer
from backend.app.ml.defect_classifier.predict import DefectClassifierInferenceService

logger = logging.getLogger("ModelRegistry")


class ModelRegistry:
    """
    Process-local thread-safe singleton model registry.

    Note on Singleton Scope:
    In multi-worker web servers (e.g., Uvicorn or Gunicorn with N worker processes),
    each OS process maintains its own ModelRegistry singleton in its isolated heap memory.
    Locks and caches are process-local and do NOT cross OS process boundaries.
    """

    _instance: Optional["ModelRegistry"] = None
    _init_lock = threading.RLock()

    def __init__(self, config: Optional[InferenceConfig] = None) -> None:
        self.config = config or InferenceConfig()
        self._lock = threading.RLock()

        # Cached model instances
        self._scaler: Optional[Any] = None
        self._isolation_forest: Optional[IsolationForestPredictor] = None
        self._lstm_autoencoder: Optional[LSTMAutoencoderPredictor] = None
        self._lstm_attribution: Optional[LSTMAttributionExplainer] = None
        self._shap_explainer: Optional[IsolationForestShapExplainer] = None
        self._defect_classifier: Optional[DefectClassifierInferenceService] = None

        # Loaded metadata cache
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls, config: Optional[InferenceConfig] = None) -> "ModelRegistry":
        """Returns the process-local singleton ModelRegistry instance."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets the process-local singleton instance (primarily for isolated test fixtures)."""
        with cls._init_lock:
            cls._instance = None

    def verify_artifact(self, filename: str) -> Path:
        """
        Cryptographically verifies an artifact's existence and SHA-256 hash.

        Raises:
            ModelArtifactNotFoundError: If file does not exist on disk.
            ArtifactIntegrityError: If computed hash differs from verified baseline.
        """
        artifact_path = self.config.resolve_artifact_path(filename)
        if not artifact_path.exists():
            raise ModelArtifactNotFoundError(
                f"Required model artifact not found on disk: {artifact_path}"
            )

        expected_hash = self.config.expected_hashes.get(filename)
        if expected_hash:
            with open(artifact_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            if actual_hash != expected_hash:
                raise ArtifactIntegrityError(
                    f"Cryptographic checksum mismatch for artifact '{filename}': "
                    f"expected SHA-256 '{expected_hash}', but got '{actual_hash}'."
                )

        return artifact_path

    def get_scaler(self) -> Any:
        """Lazily loads and caches the production StandardScaler."""
        if self._scaler is None:
            with self._lock:
                if self._scaler is None:
                    scaler_path = self.verify_artifact("sensor_scaler.joblib")
                    logger.info("Loading sensor scaler from: %s", scaler_path)
                    self._scaler = joblib.load(scaler_path)
        return self._scaler

    def get_isolation_forest(self) -> IsolationForestPredictor:
        """Lazily loads and caches the Isolation Forest predictor."""
        if self._isolation_forest is None:
            with self._lock:
                if self._isolation_forest is None:
                    model_path = self.verify_artifact("isolation_forest.joblib")
                    meta_path = self.verify_artifact("isolation_forest_metadata.json")

                    logger.info("Initializing IsolationForestPredictor from: %s", model_path)
                    predictor = IsolationForestPredictor(
                        model_path=str(model_path),
                        metadata_path=str(meta_path)
                    )
                    self._isolation_forest = predictor
                    self._metadata_cache[MODEL_ID_IF] = predictor.metadata
        return self._isolation_forest

    def get_lstm_autoencoder(self) -> LSTMAutoencoderPredictor:
        """Lazily loads and caches the LSTM Autoencoder predictor."""
        if self._lstm_autoencoder is None:
            with self._lock:
                if self._lstm_autoencoder is None:
                    model_path = self.verify_artifact("lstm_autoencoder.keras")
                    meta_path = self.verify_artifact("lstm_autoencoder_metadata.json")

                    logger.info("Initializing LSTMAutoencoderPredictor from: %s", model_path)
                    predictor = LSTMAutoencoderPredictor(
                        model_path=str(model_path),
                        metadata_path=str(meta_path)
                    )
                    self._lstm_autoencoder = predictor
                    self._metadata_cache[MODEL_ID_LSTM] = predictor.metadata
        return self._lstm_autoencoder

    def get_lstm_attribution_explainer(self) -> LSTMAttributionExplainer:
        """Lazily initializes and caches the Step 4 LSTM MSE attribution explainer."""
        if self._lstm_attribution is None:
            with self._lock:
                if self._lstm_attribution is None:
                    lstm_pred = self.get_lstm_autoencoder()
                    scaler = self.get_scaler()
                    logger.info("Initializing LSTMAttributionExplainer with loaded models")
                    self._lstm_attribution = LSTMAttributionExplainer(
                        predictor=lstm_pred,
                        scaler=scaler
                    )
        return self._lstm_attribution

    def get_shap_explainer(self) -> IsolationForestShapExplainer:
        """Lazily initializes and caches the Step 6 Isolation Forest Kernel SHAP explainer."""
        if self._shap_explainer is None:
            with self._lock:
                if self._shap_explainer is None:
                    if_pred = self.get_isolation_forest()
                    scaler = self.get_scaler()

                    # Configure SHAP explainer with resolved dataset path
                    shap_cfg = ShapExplainerConfig()
                    shap_cfg.train_sensor_csv = str(
                        self.config.base_dir / "data" / "processed" / "scaled_sensor_train.csv"
                    )
                    shap_cfg.model_path = str(self.verify_artifact("isolation_forest.joblib"))
                    shap_cfg.scaler_path = str(self.verify_artifact("sensor_scaler.joblib"))
                    shap_cfg.metadata_path = str(self.verify_artifact("isolation_forest_metadata.json"))

                    logger.info("Initializing IsolationForestShapExplainer with verified background")
                    self._shap_explainer = IsolationForestShapExplainer(
                        config=shap_cfg,
                        model=if_pred.model,
                        scaler=scaler
                    )
        return self._shap_explainer

    def get_defect_classifier(self) -> DefectClassifierInferenceService:
        """Lazily loads and caches the Step 7 Compact ResNet-18 defect classifier."""
        if self._defect_classifier is None:
            with self._lock:
                if self._defect_classifier is None:
                    model_path = self.verify_artifact("resnet_defect_classifier.keras")
                    meta_path = self.verify_artifact("resnet_defect_classifier_metadata.json")

                    logger.info("Initializing DefectClassifierInferenceService from: %s", model_path)
                    service = DefectClassifierInferenceService(model_path=str(model_path))
                    self._defect_classifier = service

                    with open(meta_path, "r") as f:
                        self._metadata_cache[MODEL_ID_RESNET] = json.load(f)
        return self._defect_classifier

    def warmup(self) -> Dict[str, str]:
        """
        Eagerly loads all models and executes dummy inference to compile graphs
        and eliminate first-request cold-start latency.
        """
        status: Dict[str, str] = {}
        with self._lock:
            # 1. Scaler
            self.get_scaler()
            status["scaler"] = "LOADED"

            # 2. Isolation Forest
            if_pred = self.get_isolation_forest()
            _ = if_pred.score(np.zeros((1, 5), dtype=np.float32))
            status["isolation_forest"] = "WARMED"

            # 3. LSTM Autoencoder
            lstm_pred = self.get_lstm_autoencoder()
            _ = lstm_pred.compute_reconstruction_error(np.zeros((1, 30, 5), dtype=np.float32))
            status["lstm_autoencoder"] = "WARMED"

            # 4. Sensor Attribution
            attr_explainer = self.get_lstm_attribution_explainer()
            _ = attr_explainer.explain_sequences(np.zeros((1, 30, 5), dtype=np.float32))
            status["sensor_attribution"] = "WARMED"

            # 5. SHAP Explainer
            _ = self.get_shap_explainer()
            status["shap_explainer"] = "WARMED"

            # 6. Defect Classifier
            defect_service = self.get_defect_classifier()
            dummy_img = np.zeros((128, 128, 3), dtype=np.float32)
            _ = defect_service.predict_image(dummy_img, image_name="warmup.bmp")
            status["defect_classifier"] = "WARMED"

        logger.info("All model registry components successfully pre-warmed: %s", status)
        return status

    def get_metadata(self, model_id: str) -> Dict[str, Any]:
        """Returns deep copy of cached metadata for a model."""
        meta = self._metadata_cache.get(model_id, {})
        return copy.deepcopy(meta)

    def list_loaded_models(self) -> List[str]:
        """Lists IDs of currently instantiated models in memory."""
        loaded = []
        if self._scaler is not None:
            loaded.append("sensor_scaler")
        if self._isolation_forest is not None:
            loaded.append(MODEL_ID_IF)
        if self._lstm_autoencoder is not None:
            loaded.append(MODEL_ID_LSTM)
        if self._lstm_attribution is not None:
            loaded.append(MODEL_ID_ATTRIBUTION)
        if self._shap_explainer is not None:
            loaded.append(MODEL_ID_SHAP)
        if self._defect_classifier is not None:
            loaded.append(MODEL_ID_RESNET)
        return loaded
