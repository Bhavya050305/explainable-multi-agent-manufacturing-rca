"""
ManuMind AI — LSTM Autoencoder Inference Service
Department of AI & Data Science — RMK Engineering College

Provides sequence reconstruction, error computation, and thresholded prediction.
"""

import json
import logging
import os
from typing import Optional, Union, Dict, Any, Tuple

import numpy as np
import pandas as pd
import tensorflow as tf

logger = logging.getLogger("LSTMAutoencoderPredict")


class LSTMAutoencoderPredictor:
    """Production inference interface for temporal sequence anomaly detection via LSTM Autoencoder."""

    def __init__(
        self,
        model_path: str = "ml/models_store/lstm_autoencoder.keras",
        metadata_path: Optional[str] = "ml/models_store/lstm_autoencoder_metadata.json"
    ):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.model: Optional[tf.keras.Model] = None
        self.threshold: float = 0.05
        self.metadata: Dict[str, Any] = {}
        self.load()

    def load(self) -> "LSTMAutoencoderPredictor":
        """Loads trained Keras LSTM Autoencoder and calibration metadata."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"LSTM Autoencoder model not found at: {self.model_path}")

        self.model = tf.keras.models.load_model(self.model_path)
        logger.info("Loaded LSTM Autoencoder model from: %s", self.model_path)

        if self.metadata_path and os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                self.metadata = json.load(f)
            self.threshold = float(
                self.metadata.get("threshold_calibration", {}).get("selected_threshold", 0.05)
            )
            logger.info("Loaded calibrated reconstruction threshold: %.6f", self.threshold)
        else:
            self.threshold = 0.05
            logger.warning("Metadata not found; default threshold set to %.6f", self.threshold)

        return self

    def reconstruct(self, X: np.ndarray, batch_size: int = 32) -> np.ndarray:
        """
        Reconstructs input temporal sequences of shape (N, 30, 5).
        Returns reconstructed sequences of identical shape (N, 30, 5).
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load() before predicting.")

        if X.ndim == 2:
            # Single sequence (30, 5) -> (1, 30, 5)
            X = np.expand_dims(X, axis=0)

        X_recon = self.model.predict(X, batch_size=batch_size, verbose=0)
        return X_recon.astype(np.float32)

    def compute_reconstruction_error(
        self,
        X: np.ndarray,
        X_recon: Optional[np.ndarray] = None,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Computes Mean Squared Error (MSE) reconstruction loss per sequence:
        MSE = mean((X - X_recon)^2) across timesteps (30) and features (5).
        Returns 1D array of shape (N,).
        """
        if X.ndim == 2:
            X = np.expand_dims(X, axis=0)

        if X_recon is None:
            X_recon = self.reconstruct(X, batch_size=batch_size)

        # Sequence-level Mean Squared Error
        errors = np.mean(np.square(X - X_recon), axis=(1, 2))
        return errors.astype(np.float32)

    def predict(
        self,
        X: np.ndarray,
        threshold: Optional[float] = None,
        batch_size: int = 32
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Binary sequence anomaly classification:
        Returns:
            errors: np.ndarray of shape (N,)
            preds: np.ndarray of shape (N,) where 1=anomaly, 0=normal
        """
        thresh = threshold if threshold is not None else self.threshold
        errors = self.compute_reconstruction_error(X, batch_size=batch_size)
        preds = (errors > thresh).astype(int)
        return errors, preds

    def predict_sequences(
        self,
        X: np.ndarray,
        meta_df: Optional[pd.DataFrame] = None,
        threshold: Optional[float] = None,
        batch_size: int = 32
    ) -> pd.DataFrame:
        """
        Scores an array of sequence windows and attaches metadata.
        """
        thresh = threshold if threshold is not None else self.threshold
        errors, preds = self.predict(X, threshold=thresh, batch_size=batch_size)

        if meta_df is not None:
            res_df = meta_df.copy().reset_index(drop=True)
        else:
            res_df = pd.DataFrame({"sequence_idx": np.arange(len(X))})

        res_df["reconstruction_error"] = errors
        res_df["is_anomaly_pred"] = preds
        res_df["anomaly_threshold_used"] = thresh
        return res_df
