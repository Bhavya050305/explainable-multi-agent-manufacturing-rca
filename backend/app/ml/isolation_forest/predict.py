"""
ManuMind AI — Isolation Forest Inference Interface
Department of AI & Data Science — RMK Engineering College

Provides scoring, threshold application, and tabular prediction functions.
"""

import json
import logging
import os
from typing import Optional, Union, Dict, Any, List

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("IsolationForestPredict")


class IsolationForestPredictor:
    """Production inference service for Isolation Forest anomaly detection."""

    FEATURE_COLS: List[str] = ["vibration", "temperature", "pressure", "current", "rpm"]

    def __init__(
        self,
        model_path: str = "ml/models_store/isolation_forest.joblib",
        metadata_path: Optional[str] = "ml/models_store/isolation_forest_metadata.json"
    ):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.model = None
        self.threshold: float = 0.0
        self.metadata: Dict[str, Any] = {}
        self.load()

    def load(self) -> "IsolationForestPredictor":
        """Loads trained Isolation Forest and associated calibration metadata."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model artifact not found at: {self.model_path}")

        self.model = joblib.load(self.model_path)

        if self.metadata_path and os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                self.metadata = json.load(f)
            self.threshold = float(
                self.metadata.get("validation_calibration", {}).get("calibrated_threshold", 0.0)
            )
            logger.info("Loaded Isolation Forest with calibrated threshold=%.4f", self.threshold)
        else:
            self.threshold = 0.0
            logger.warning("No metadata found; defaulting threshold to 0.0.")

        return self

    def score(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Computes continuous anomaly score for each observation.
        Definition: anomaly_score = -decision_function(X).
        Interpretation: Higher score = greater deviation from healthy training baseline.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load() before scoring.")

        if isinstance(X, pd.DataFrame):
            X_arr = X[self.FEATURE_COLS].values
        else:
            X_arr = np.asarray(X)

        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)

        # Negative decision function: higher is more anomalous
        scores = -self.model.decision_function(X_arr)
        return scores.astype(np.float32)

    def predict(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        threshold: Optional[float] = None
    ) -> np.ndarray:
        """
        Binary anomaly classification:
        Returns 1 for anomaly, 0 for normal.
        """
        thresh = threshold if threshold is not None else self.threshold
        scores = self.score(X)
        preds = (scores > thresh).astype(int)
        return preds

    def predict_dataframe(
        self,
        df: pd.DataFrame,
        threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Scores an entire DataFrame, preserving all metadata, machine IDs, and timestamps.
        Appends 'anomaly_score' and 'is_anomaly_pred' columns.
        """
        result_df = df.copy()
        scores = self.score(df)
        thresh = threshold if threshold is not None else self.threshold
        preds = (scores > thresh).astype(int)

        result_df["anomaly_score"] = scores
        result_df["is_anomaly_pred"] = preds
        result_df["anomaly_threshold_used"] = thresh
        return result_df
