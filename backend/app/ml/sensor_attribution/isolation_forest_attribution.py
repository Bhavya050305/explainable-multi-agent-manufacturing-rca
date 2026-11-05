"""
ManuMind AI — Isolation Forest Model-Agnostic Feature-Ablation Explainer
Department of AI & Data Science — RMK Engineering College

Computes feature-level anomaly contribution via healthy-reference feature ablation
for tabular and sequential sensor readings.
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
from backend.app.ml.isolation_forest.predict import IsolationForestPredictor

logger = logging.getLogger("IsolationForestAttributionExplainer")


@dataclass
class IsolationForestAttributionResult:
    """Structured container for sequence-level Isolation Forest ablation attribution."""
    raw_ablation_delta: np.ndarray       # (N, 5) OriginalScore - AblatedScore_c
    normalized_contrib_pct: np.ndarray   # (N, 5) percentage of positive ablation reduction
    sequence_original_score: np.ndarray  # (N,) sequence mean original anomaly score
    dominant_feature_indices: np.ndarray # (N,) index of feature with highest positive reduction
    dominant_features: List[str]         # (N,) name of dominant feature
    top2_features: List[List[str]]       # (N, 2) top-2 contributing feature names
    healthy_references: np.ndarray       # (5,) reference values used for ablation in scaled space
    dataframe: pd.DataFrame              # Tabular view


class IsolationForestAttributionExplainer:
    """
    Model-agnostic feature-ablation diagnostic for Isolation Forest.

    Methodology:
    1. Establish healthy reference values strictly from training data (Train split, is_anomaly == 0).
    2. Replace feature c with its healthy training reference value: X_ablated[:, c] = ref_c.
    3. Re-score with existing Isolation Forest: AblatedScore_c = -decision_function(X_ablated).
    4. Compute ablation contribution: Contribution_c = OriginalScore - AblatedScore_c.
    5. Aggregate over sequence timesteps (mean over 30 readings).

    Important Engineering Notes:
    - This is a model-agnostic perturbation diagnostic, not native tree feature importance.
    - Feature interactions in tree splits can affect results.
    - Individual contributions are not guaranteed to be strictly additive.
    - Negative values are possible (when replacing a feature increases isolation) and are preserved.
    """

    def __init__(
        self,
        config: Optional[SensorAttributionConfig] = None,
        predictor: Optional[IsolationForestPredictor] = None,
        healthy_references: Optional[np.ndarray] = None
    ):
        self.config = config or SensorAttributionConfig()
        self.feature_cols = list(self.config.feature_cols)
        self.n_features = len(self.feature_cols)

        # Initialize or reuse predictor
        if predictor is not None:
            self.predictor = predictor
        else:
            self.predictor = IsolationForestPredictor(
                model_path=self.config.if_model_path,
                metadata_path=self.config.if_metadata_path
            )

        # Establish healthy reference values strictly from training data
        if healthy_references is not None:
            self.healthy_references = np.asarray(healthy_references, dtype=np.float64)
        else:
            self.healthy_references = self._compute_healthy_reference_values()

        logger.info(
            "Isolation Forest Explainer initialized with healthy reference vector (scaled space): %s",
            np.round(self.healthy_references, 4).tolist()
        )

    def _compute_healthy_reference_values(self) -> np.ndarray:
        """
        Calculates healthy reference values strictly from the training dataset.
        Never uses validation or test data to compute references.
        """
        train_csv = self.config.train_sensor_csv
        scaler_path = self.config.scaler_path

        df_train = pd.read_csv(train_csv)
        healthy_mask = (df_train["is_anomaly"] == 0)
        healthy_raw = df_train.loc[healthy_mask, self.feature_cols].values

        scaler = joblib.load(scaler_path)
        scaled_healthy = scaler.transform(healthy_raw)

        # Use median for robustness against benign operational spikes
        ref_values = np.median(scaled_healthy, axis=0).astype(np.float64)
        return ref_values

    def explain_points(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Point-level feature ablation attribution on 2D array of shape (M, 5).

        Returns:
            orig_scores: (M,)
            ablation_deltas: (M, 5)
            normalized_pct: (M, 5)
        """
        if X.ndim != 2 or X.shape[1] != self.n_features:
            raise ValueError(f"Expected 2D array of shape (M, {self.n_features}), got {X.shape}")

        M = X.shape[0]
        orig_scores = self.predictor.score(X)  # (M,)

        ablation_deltas = np.zeros((M, self.n_features), dtype=np.float64)

        for c in range(self.n_features):
            X_abl = X.copy()
            X_abl[:, c] = self.healthy_references[c]
            abl_scores = self.predictor.score(X_abl)
            ablation_deltas[:, c] = orig_scores - abl_scores

        # Normalized positive percentage
        positive_deltas = np.maximum(0.0, ablation_deltas)
        pos_sum = np.sum(positive_deltas, axis=1, keepdims=True)
        near_zero_mask = (pos_sum.squeeze(axis=-1) < self.config.epsilon)

        with np.errstate(divide='ignore', invalid='ignore'):
            normalized_pct = (positive_deltas / np.maximum(pos_sum, self.config.epsilon)) * 100.0

        # When all five raw signed deltas are zero or negative, no feature contributed
        # to reducing anomaly isolation. In that case, all normalized contributions are set to 0.0%,
        # and the percentages do not sum to 100% (they sum to 0.0%).
        if np.any(near_zero_mask):
            normalized_pct[near_zero_mask, :] = 0.0

        return orig_scores, ablation_deltas, normalized_pct

    def explain_sequences(
        self,
        X: np.ndarray,
        window_ids: Optional[Union[List[str], np.ndarray]] = None,
        machine_ids: Optional[Union[List[str], np.ndarray]] = None,
        timestamps: Optional[Union[List[str], np.ndarray]] = None,
        labels: Optional[Union[List[int], np.ndarray]] = None
    ) -> IsolationForestAttributionResult:
        """
        Computes feature-ablation attribution for 3D sequence array of shape (N, 30, 5).
        Aggregates point-level ablation deltas across the 30 readings in each sequence.
        """
        if X.ndim == 2:
            X = np.expand_dims(X, axis=0)

        N, T, C = X.shape
        if C != self.n_features:
            raise ValueError(f"Expected {self.n_features} features, got shape {X.shape}")

        # Vectorized point-level scoring across all N * T points
        X_flat = X.reshape(-1, C)  # (N * 30, 5)
        orig_scores_flat, deltas_flat, _ = self.explain_points(X_flat)

        # Aggregate back to sequence level (mean across the 30 steps)
        orig_scores_seq = orig_scores_flat.reshape(N, T)
        sequence_original_score = np.mean(orig_scores_seq, axis=1)  # (N,)

        deltas_seq = deltas_flat.reshape(N, T, C)
        raw_ablation_delta = np.mean(deltas_seq, axis=1)  # (N, 5)

        # Normalized percentage among positive shifts
        positive_deltas = np.maximum(0.0, raw_ablation_delta)
        pos_sum = np.sum(positive_deltas, axis=1, keepdims=True)
        near_zero_mask = (pos_sum.squeeze(axis=-1) < self.config.epsilon)

        with np.errstate(divide='ignore', invalid='ignore'):
            normalized_pct = (positive_deltas / np.maximum(pos_sum, self.config.epsilon)) * 100.0

        # When all five raw signed deltas are zero or negative, no feature contributed
        # to reducing anomaly isolation. In that case, all normalized contributions are set to 0.0%,
        # and the percentages do not sum to 100% (they sum to 0.0%).
        if np.any(near_zero_mask):
            normalized_pct[near_zero_mask, :] = 0.0

        # Identify dominant and top-2 features based on positive reduction delta
        dominant_indices = np.argmax(raw_ablation_delta, axis=1)
        dominant_features = [self.feature_cols[idx] for idx in dominant_indices]

        sorted_indices = np.argsort(-raw_ablation_delta, axis=1)
        top2_features = [
            [self.feature_cols[row[0]], self.feature_cols[row[1]]]
            for row in sorted_indices
        ]

        # Build tabular DataFrame
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

        df_dict["sequence_original_score"] = np.round(sequence_original_score, 6)
        df_dict["dominant_feature"] = dominant_features
        df_dict["dominant_delta"] = np.round(
            [raw_ablation_delta[i, dominant_indices[i]] for i in range(N)], 6
        )
        df_dict["dominant_contribution_pct"] = np.round(
            [normalized_pct[i, dominant_indices[i]] for i in range(N)], 2
        )
        df_dict["secondary_feature"] = [t2[1] for t2 in top2_features]
        df_dict["secondary_delta"] = np.round(
            [raw_ablation_delta[i, sorted_indices[i, 1]] for i in range(N)], 6
        )
        df_dict["secondary_contribution_pct"] = np.round(
            [normalized_pct[i, sorted_indices[i, 1]] for i in range(N)], 2
        )

        for idx, feat in enumerate(self.feature_cols):
            df_dict[f"{feat}_delta"] = np.round(raw_ablation_delta[:, idx], 6)
            df_dict[f"{feat}_contrib_pct"] = np.round(normalized_pct[:, idx], 2)

        df = pd.DataFrame(df_dict)

        return IsolationForestAttributionResult(
            raw_ablation_delta=raw_ablation_delta,
            normalized_contrib_pct=normalized_pct,
            sequence_original_score=sequence_original_score,
            dominant_feature_indices=dominant_indices,
            dominant_features=dominant_features,
            top2_features=top2_features,
            healthy_references=self.healthy_references,
            dataframe=df
        )
