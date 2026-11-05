"""
ManuMind AI — LSTM Autoencoder Sensor-Level Attribution Explainer
Department of AI & Data Science — RMK Engineering College

Computes per-sensor reconstruction-error attribution, normalized contribution percentages,
and signed residuals for multivariate time-series sequences.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd
import joblib

from backend.app.ml.sensor_attribution.config import (
    SensorAttributionConfig,
    FEATURE_COLUMNS,
    FEATURE_UNITS
)
from backend.app.ml.lstm_autoencoder.predict import LSTMAutoencoderPredictor

logger = logging.getLogger("LSTMAttributionExplainer")


@dataclass
class LSTMAttributionResult:
    """Structured container for sequence-level LSTM reconstruction attribution."""
    feature_mse: np.ndarray               # (N, 5) per-feature mean squared error
    feature_rmse: np.ndarray              # (N, 5) per-feature root mean squared error
    total_sequence_error: np.ndarray      # (N,) sum of feature MSEs
    sequence_mean_mse: np.ndarray         # (N,) mean of feature MSEs (matches model MSE)
    feature_contribution_pct: np.ndarray  # (N, 5) normalized percentage contribution (sums to 100)
    signed_residuals: np.ndarray          # (N, 5) scaled signed residuals (X - X_recon)
    unscaled_residuals: np.ndarray        # (N, 5) physical engineering unit residuals
    dominant_feature_indices: np.ndarray  # (N,) index of highest contributing feature
    dominant_features: List[str]          # (N,) name of dominant feature
    top2_features: List[List[str]]        # (N, 2) top-2 contributing feature names
    dataframe: pd.DataFrame               # Full tabular view


class LSTMAttributionExplainer:
    """Production explainer for multivariate sequence reconstruction error attribution."""

    def __init__(
        self,
        config: Optional[SensorAttributionConfig] = None,
        predictor: Optional[LSTMAutoencoderPredictor] = None,
        scaler: Optional[Any] = None
    ):
        self.config = config or SensorAttributionConfig()
        self.feature_cols = list(self.config.feature_cols)
        self.n_features = len(self.feature_cols)

        # Initialize or reuse predictor
        if predictor is not None:
            self.predictor = predictor
        else:
            self.predictor = LSTMAutoencoderPredictor(
                model_path=self.config.lstm_model_path,
                metadata_path=self.config.lstm_metadata_path
            )

        # Initialize or load scaler for unscaled physical residuals
        if scaler is not None:
            self.scaler = scaler
        else:
            try:
                self.scaler = joblib.load(self.config.scaler_path)
            except Exception as e:
                logger.warning("Could not load scaler from %s (%s); physical residuals will use unit scale.", self.config.scaler_path, e)
                self.scaler = None

    def explain_sequences(
        self,
        X: np.ndarray,
        window_ids: Optional[Union[List[str], np.ndarray]] = None,
        machine_ids: Optional[Union[List[str], np.ndarray]] = None,
        timestamps: Optional[Union[List[str], np.ndarray]] = None,
        labels: Optional[Union[List[int], np.ndarray]] = None,
        batch_size: Optional[int] = None
    ) -> LSTMAttributionResult:
        """
        Computes reconstruction-error attribution for a batch of sequences.

        Args:
            X: Input array of shape (N, 30, 5) or (30, 5).
            window_ids: Optional sequence identifiers.
            machine_ids: Optional machine identifiers.
            timestamps: Optional timestamp list.
            labels: Optional ground-truth anomaly labels (0 or 1).
            batch_size: Batch size for model reconstruction.

        Returns:
            LSTMAttributionResult containing all computed attribution metrics and DataFrame.
        """
        if X.ndim == 2:
            X = np.expand_dims(X, axis=0)

        N, T, C = X.shape
        if C != self.n_features:
            raise ValueError(f"Expected {self.n_features} features, got shape {X.shape}")

        b_size = batch_size or self.config.batch_size
        X_recon = self.predictor.reconstruct(X, batch_size=b_size)

        # 1. Per-feature MSE: E_c = mean((X[:,:,c] - X_recon[:,:,c])^2) over timesteps T=30
        residuals = X - X_recon  # (N, 30, 5)
        feature_mse = np.mean(np.square(residuals), axis=1).astype(np.float64)  # (N, 5)

        # 2. Per-feature RMSE: sqrt(E_c)
        feature_rmse = np.sqrt(np.maximum(feature_mse, 0.0))  # (N, 5)

        # 3. Total Sequence Reconstruction Error
        total_sequence_error = np.sum(feature_mse, axis=1)  # (N,) sum of 5 features
        sequence_mean_mse = np.mean(feature_mse, axis=1)    # (N,) matches model predict error

        # 4. Normalized Feature Contribution Percentage: (E_c / sum(E_all)) * 100
        # Safe zero-division handling
        total_sum_safe = np.sum(feature_mse, axis=1, keepdims=True)  # (N, 1)
        near_zero_mask = (total_sum_safe.squeeze(axis=-1) < self.config.epsilon)

        with np.errstate(divide='ignore', invalid='ignore'):
            feature_contrib_pct = (feature_mse / np.maximum(total_sum_safe, self.config.epsilon)) * 100.0

        # When total error is negligible, distribute contribution equally (20% each)
        if np.any(near_zero_mask):
            feature_contrib_pct[near_zero_mask, :] = 100.0 / self.n_features

        # 5. Signed Residuals: mean(X[:,:,c] - X_recon[:,:,c]) over timesteps T=30
        signed_residuals = np.mean(residuals, axis=1).astype(np.float64)  # (N, 5)

        # 6. Physical (Unscaled) Residuals: signed_residuals * scale
        if self.scaler is not None and hasattr(self.scaler, "scale_"):
            scales = np.asarray(self.scaler.scale_, dtype=np.float64)
            unscaled_residuals = signed_residuals * scales
        else:
            unscaled_residuals = signed_residuals.copy()

        # 7. Identify Dominant and Top-2 Features
        dominant_indices = np.argmax(feature_contrib_pct, axis=1)  # (N,)
        dominant_features = [self.feature_cols[idx] for idx in dominant_indices]

        # Sorted indices descending for top-k
        sorted_indices = np.argsort(-feature_contrib_pct, axis=1)
        top2_features = [
            [self.feature_cols[row[0]], self.feature_cols[row[1]]]
            for row in sorted_indices
        ]

        # 8. Build structured DataFrame
        df_dict: Dict[str, Any] = {}
        if window_ids is not None:
            df_dict["window_id"] = list(window_ids)
        else:
            df_dict["window_id"] = [f"win_{i:04d}" for i in range(N)]

        if machine_ids is not None:
            df_dict["machine_id"] = list(machine_ids)
        if timestamps is not None:
            df_dict["timestamp"] = list(timestamps)
        if labels is not None:
            df_dict["is_anomaly"] = list(labels)

        df_dict["total_reconstruction_error"] = np.round(total_sequence_error, 6)
        df_dict["sequence_mse"] = np.round(sequence_mean_mse, 6)
        df_dict["dominant_feature"] = dominant_features
        df_dict["dominant_contribution_pct"] = np.round(
            [feature_contrib_pct[i, dominant_indices[i]] for i in range(N)], 2
        )
        df_dict["dominant_signed_residual"] = np.round(
            [signed_residuals[i, dominant_indices[i]] for i in range(N)], 4
        )
        df_dict["dominant_direction"] = [
            "positive" if signed_residuals[i, dominant_indices[i]] >= 0 else "negative"
            for i in range(N)
        ]
        df_dict["secondary_feature"] = [t2[1] for t2 in top2_features]
        df_dict["secondary_contribution_pct"] = np.round(
            [feature_contrib_pct[i, sorted_indices[i, 1]] for i in range(N)], 2
        )

        # Per-feature columns
        for idx, feat in enumerate(self.feature_cols):
            unit = FEATURE_UNITS.get(feat, "")
            df_dict[f"{feat}_mse"] = np.round(feature_mse[:, idx], 6)
            df_dict[f"{feat}_rmse"] = np.round(feature_rmse[:, idx], 6)
            df_dict[f"{feat}_pct"] = np.round(feature_contrib_pct[:, idx], 2)
            df_dict[f"{feat}_signed_residual"] = np.round(signed_residuals[:, idx], 4)
            df_dict[f"{feat}_unscaled_residual_{unit}"] = np.round(unscaled_residuals[:, idx], 3)

        df = pd.DataFrame(df_dict)

        return LSTMAttributionResult(
            feature_mse=feature_mse,
            feature_rmse=feature_rmse,
            total_sequence_error=total_sequence_error,
            sequence_mean_mse=sequence_mean_mse,
            feature_contribution_pct=feature_contrib_pct,
            signed_residuals=signed_residuals,
            unscaled_residuals=unscaled_residuals,
            dominant_feature_indices=dominant_indices,
            dominant_features=dominant_features,
            top2_features=top2_features,
            dataframe=df
        )
