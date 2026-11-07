"""
ManuMind AI — Isolation Forest Kernel SHAP Explainer
Department of AI & Data Science — RMK Engineering College

Production explainer for multivariate anomaly scoring using SHAP KernelExplainer.
Decomposes the continuous anomaly intensity function f(X) = -decision_function(X)
into game-theoretic additive feature attributions with strict mathematical additivity.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import shap

from backend.app.ml.shap_explainability.config import (
    ShapExplainerConfig,
    FEATURE_COLUMNS,
    STRATIFIED_MACHINE_IDS,
    SAMPLES_PER_MACHINE,
    TOTAL_BACKGROUND_SAMPLES,
    RANDOM_SEED,
    SHAP_NSAMPLES,
    ADDITIVITY_TOLERANCE,
    ATTRIBUTION_UNITS
)

logger = logging.getLogger("IsolationForestShapExplainer")


class IsolationForestShapExplainer:
    """
    Production Kernel SHAP Explainer for the Isolation Forest anomaly detector.

    Wraps the continuous anomaly-intensity function:
        f(X) = -model.decision_function(X)

    Guarantees:
    1. Zero Data Leakage: Background exemplars strictly selected from normal training data.
    2. Strict Additivity: Internal verification that |f(x) - (E[f] + sum(phi))| < 1e-6.
    3. Production Alignment: Exact 5-feature column order and units preserved.
    4. Safe Serialization: Returns JSON-compliant native Python types matching Alert.shap_json.
    """

    def __init__(
        self,
        config: Optional[ShapExplainerConfig] = None,
        model: Optional[Any] = None,
        scaler: Optional[Any] = None,
        background_data: Optional[np.ndarray] = None
    ):
        self.config = config or ShapExplainerConfig()
        self.feature_cols = list(self.config.feature_cols)
        self.n_features = len(self.feature_cols)

        # 1. Load or bind Isolation Forest model
        if model is not None:
            self.model = model
        else:
            self.model = self._load_model()

        # 2. Load or bind sensor scaler
        if scaler is not None:
            self.scaler = scaler
        else:
            self.scaler = self._load_scaler()

        # 3. Establish verified background exemplars
        self.background_metadata: Dict[str, Any] = {}
        if background_data is not None:
            self._validate_background(background_data)
            self.background_data = np.asarray(background_data, dtype=np.float64)
            self.background_metadata = {
                "source": "provided_in_memory",
                "sample_count": len(self.background_data),
                "feature_count": self.background_data.shape[1]
            }
        else:
            self.background_data, self.background_metadata = self._build_background()

        # 4. Initialize KernelExplainer with production anomaly wrapper
        self.explainer: Optional[shap.KernelExplainer] = None
        self.expected_value: float = 0.0
        self._init_kernel_explainer()

        logger.info(
            "IsolationForestShapExplainer initialized successfully with %d background exemplars. "
            "Baseline expectation E[f(X)] = %.6f",
            len(self.background_data),
            self.expected_value
        )

    def _load_model(self) -> Any:
        """Loads serialized Isolation Forest from model store."""
        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"Isolation Forest model artifact not found at: {self.config.model_path}")
        model = joblib.load(self.config.model_path)
        return model

    def _load_scaler(self) -> Optional[Any]:
        """Loads serialized StandardScaler from model store."""
        if os.path.exists(self.config.scaler_path):
            try:
                return joblib.load(self.config.scaler_path)
            except Exception as e:
                logger.warning("Could not load scaler from %s (%s).", self.config.scaler_path, e)
        return None

    def _validate_background(self, data: np.ndarray) -> None:
        """Validates background sample shape, finite values, and dimension."""
        if data.ndim != 2 or data.shape[1] != self.n_features:
            raise ValueError(f"Background data must have shape (N, {self.n_features}), got {data.shape}")
        if not np.all(np.isfinite(data)):
            raise ValueError("Background data contains non-finite values (NaNs or Infs).")
        if len(data) < 1:
            raise ValueError("Background data must contain at least one observation.")

    def _build_background(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Extracts 50 real normal observations strictly from the normal training partition.

        Selection Protocol:
        - Partition: Scaled training telemetry (data/processed/scaled_sensor_train.csv).
        - Filter: Strictly is_anomaly == 0 (normal operation only).
        - Stratification: 5 observations per machine across all 10 machines (M101–M110).
        - Determinism: Pseudo-random selection with fixed random seed (42).
        - Zero Leakage: Validation and test partitions are never observed.
        """
        train_path = self.config.train_sensor_csv
        if not os.path.exists(train_path):
            raise FileNotFoundError(f"Training dataset not found at: {train_path}")

        df_train = pd.read_csv(train_path)

        # Safety assertions
        for col in self.feature_cols:
            if col not in df_train.columns:
                raise ValueError(f"Missing required feature '{col}' in training telemetry.")
        if "machine_id" not in df_train.columns or "is_anomaly" not in df_train.columns:
            raise ValueError("Training dataset missing 'machine_id' or 'is_anomaly' columns.")

        # Filter normal operation
        normal_mask = (df_train["is_anomaly"] == 0)
        df_normal = df_train[normal_mask].copy()

        selected_rows: List[pd.DataFrame] = []
        machine_selection_records: Dict[str, Dict[str, Any]] = {}

        for machine_id in self.config.stratified_machines:
            m_df = df_normal[df_normal["machine_id"] == machine_id].copy()
            if len(m_df) < self.config.samples_per_machine:
                raise ValueError(
                    f"Machine {machine_id} has only {len(m_df)} normal training rows; "
                    f"requires {self.config.samples_per_machine}."
                )

            # Deterministic selection using fixed seed and machine-specific offset
            m_seed = self.config.random_seed + int(machine_id.replace("M", ""))
            rng = np.random.RandomState(m_seed)
            sample_indices = rng.choice(
                len(m_df),
                size=self.config.samples_per_machine,
                replace=False
            )
            sample_indices.sort()

            m_samples = m_df.iloc[sample_indices]
            selected_rows.append(m_samples)

            machine_selection_records[machine_id] = {
                "available_normal_rows": int(len(m_df)),
                "selected_count": int(self.config.samples_per_machine),
                "selected_row_indices": [int(idx) for idx in sample_indices],
                "sample_timestamps": m_samples["timestamp"].tolist() if "timestamp" in m_samples.columns else []
            }

        df_bg = pd.concat(selected_rows, axis=0, ignore_index=True)

        if len(df_bg) != self.config.total_background_samples:
            raise ValueError(
                f"Expected exactly {self.config.total_background_samples} background rows, got {len(df_bg)}"
            )

        background_arr = df_bg[self.feature_cols].values.astype(np.float64)
        self._validate_background(background_arr)

        metadata = {
            "source_file": train_path,
            "total_samples": int(len(background_arr)),
            "features": list(self.feature_cols),
            "random_seed": int(self.config.random_seed),
            "samples_per_machine": int(self.config.samples_per_machine),
            "machines_sampled": list(self.config.stratified_machines),
            "machine_details": machine_selection_records,
            "feature_means": {
                feat: float(np.mean(background_arr[:, i]))
                for i, feat in enumerate(self.feature_cols)
            },
            "feature_stds": {
                feat: float(np.std(background_arr[:, i]))
                for i, feat in enumerate(self.feature_cols)
            }
        }

        return background_arr, metadata

    def anomaly_intensity_wrapper(self, X: np.ndarray) -> np.ndarray:
        """
        Continuous Anomaly Intensity Wrapper.

        Mathematical definition:
            f(X) = -decision_function(X)

        Orientation:
            Higher output = greater anomaly intensity.
            Lower output = more normal operation.
            f(X) ≈ 0.0 represents the nominal decision boundary.
        """
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape[1] != self.n_features:
            raise ValueError(f"Expected {self.n_features} features, got shape {arr.shape}")

        # In scikit-learn IsolationForest:
        # decision_function(X) > 0 for inliers (normal)
        # decision_function(X) < 0 for outliers (anomalies)
        # Therefore: -decision_function(X) is positive for anomalies and negative for inliers.
        scores = -self.model.decision_function(arr)
        return scores.astype(np.float64)

    def _init_kernel_explainer(self) -> None:
        """Initializes shap.KernelExplainer on the anomaly intensity wrapper."""
        # Silence SHAP informational warnings for batch evaluation
        self.explainer = shap.KernelExplainer(
            self.anomaly_intensity_wrapper,
            self.background_data,
            link="identity"
        )
        self.expected_value = float(self.explainer.expected_value)

    def explain_observation(
        self,
        x: Union[np.ndarray, List[float], pd.Series, pd.DataFrame],
        machine_id: Optional[str] = None,
        step: Optional[int] = None,
        timestamp: Optional[str] = None,
        nsamples: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes game-theoretic SHAP attribution for a single 5-feature sensor observation.

        Args:
            x: Input vector of shape (5,) or (1, 5).
            machine_id: Optional machine identifier (e.g. 'M104').
            step: Optional synthetic time-step.
            timestamp: Optional ISO timestamp string.
            nsamples: Optional number of coalition evaluations (default: 32 for full 2^5 lattice).

        Returns:
            Structured dictionary matching the Alert.shap_json schema.
        """
        t_start = time.perf_counter()

        # Input array normalization and validation
        try:
            if isinstance(x, pd.DataFrame):
                x_arr = x[self.feature_cols].values.astype(np.float64)
            elif isinstance(x, pd.Series):
                x_arr = x[self.feature_cols].values.astype(np.float64)
            else:
                x_arr = np.asarray(x, dtype=np.float64)

            if x_arr.ndim == 1:
                x_arr = x_arr.reshape(1, -1)

            if x_arr.shape != (1, self.n_features):
                raise ValueError(f"Expected input shape (1, {self.n_features}) or ({self.n_features},), got {x_arr.shape}")

            if not np.all(np.isfinite(x_arr)):
                raise ValueError("Input observation contains non-finite values (NaNs or Infs).")

            # 1. Target continuous anomaly score
            anomaly_score = float(self.anomaly_intensity_wrapper(x_arr)[0])

            # 2. Compute SHAP values
            n_eval = nsamples or self.config.shap_nsamples
            phi = self.explainer.shap_values(x_arr, nsamples=n_eval, silent=True)

            # Flatten SHAP array to (5,)
            if isinstance(phi, list):
                phi_arr = np.squeeze(np.asarray(phi[0], dtype=np.float64))
            else:
                phi_arr = np.squeeze(np.asarray(phi, dtype=np.float64))

            # 3. Mathematical additivity verification (full internal numerical precision)
            base_val = self.expected_value
            sum_phi = float(np.sum(phi_arr))
            reconstructed_output = base_val + sum_phi
            additivity_error = abs(anomaly_score - reconstructed_output)
            is_additive = bool(additivity_error <= self.config.additivity_tolerance)

            if not is_additive:
                logger.warning(
                    "SHAP additivity verification exceeded tolerance: |%.6f - %.6f| = %.2e > %.2e",
                    anomaly_score,
                    reconstructed_output,
                    additivity_error,
                    self.config.additivity_tolerance
                )

            # 4. Feature attributions dictionary
            feature_attributions: Dict[str, float] = {
                feat: float(phi_arr[i])
                for i, feat in enumerate(self.feature_cols)
            }

            # 5. Top positive contributor (pushes toward anomaly)
            positive_features = {
                feat: val for feat, val in feature_attributions.items() if val > 0.0
            }
            if positive_features:
                top_positive_contributor = max(positive_features, key=positive_features.get)
            else:
                top_positive_contributor = None

            # 6. Top absolute contributor (largest magnitude impact)
            top_absolute_contributor = max(
                feature_attributions,
                key=lambda f: abs(feature_attributions[f])
            )

            # 7. Share of positive attribution percentage
            # Defined as: max(0, phi_top) / sum_i(max(0, phi_i)) * 100
            # Returns null when there are no positive attributions.
            sum_positive_attribution = sum(positive_features.values())
            if sum_positive_attribution > 0.0 and top_positive_contributor is not None:
                top_pos_val = positive_features[top_positive_contributor]
                share_of_positive_attribution_pct = float(
                    (top_pos_val / sum_positive_attribution) * 100.0
                )
            else:
                share_of_positive_attribution_pct = None

            elapsed_ms = float((time.perf_counter() - t_start) * 1000.0)

            payload: Dict[str, Any] = {
                "status": "success",
                "machine_id": machine_id,
                "step": step,
                "timestamp": timestamp,
                "explained_model": self.config.explained_model_name,
                "explained_output": self.config.explained_output_name,
                "explainer_method": self.config.explainer_method_name,
                "model_artifact": os.path.basename(self.config.model_path),
                "anomaly_score": anomaly_score,
                "base_value": base_val,
                "attribution_units": self.config.attribution_units,
                "feature_attributions": feature_attributions,
                "feature_order": list(self.feature_cols),
                "top_positive_contributor": top_positive_contributor,
                "top_absolute_contributor": top_absolute_contributor,
                "share_of_positive_attribution_pct": share_of_positive_attribution_pct,
                "additivity_verified": is_additive,
                "additivity_error": float(additivity_error),
                "background_samples": len(self.background_data),
                "background_seed": int(self.config.random_seed),
                "computation_time_ms": elapsed_ms,
                "error_message": None
            }

            return payload

        except Exception as e:
            elapsed_ms = float((time.perf_counter() - t_start) * 1000.0)
            logger.error("Failed to explain observation: %s", e, exc_info=True)
            return {
                "status": "failed",
                "machine_id": machine_id,
                "step": step,
                "timestamp": timestamp,
                "explained_model": self.config.explained_model_name,
                "explained_output": self.config.explained_output_name,
                "explainer_method": self.config.explainer_method_name,
                "model_artifact": os.path.basename(self.config.model_path),
                "anomaly_score": None,
                "base_value": self.expected_value,
                "attribution_units": self.config.attribution_units,
                "feature_attributions": {feat: 0.0 for feat in self.feature_cols},
                "feature_order": list(self.feature_cols),
                "top_positive_contributor": None,
                "top_absolute_contributor": None,
                "share_of_positive_attribution_pct": None,
                "additivity_verified": False,
                "additivity_error": None,
                "background_samples": len(self.background_data) if hasattr(self, "background_data") else 0,
                "background_seed": int(self.config.random_seed),
                "computation_time_ms": elapsed_ms,
                "error_message": str(e)
            }

    def explain_batch(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        metadata_df: Optional[pd.DataFrame] = None,
        nsamples: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Explains a batch of observations sequentially.

        Args:
            X: Telemetry observations array of shape (N, 5) or DataFrame.
            metadata_df: Optional matching DataFrame containing 'machine_id', 'step', 'timestamp'.
            nsamples: Optional coalition evaluation budget per sample.

        Returns:
            List of structured explanation payloads.
        """
        if isinstance(X, pd.DataFrame):
            X_arr = X[self.feature_cols].values.astype(np.float64)
            meta = X
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            meta = metadata_df

        N = len(X_arr)
        explanations: List[Dict[str, Any]] = []

        for i in range(N):
            row_x = X_arr[i]
            m_id = str(meta.iloc[i]["machine_id"]) if (meta is not None and "machine_id" in meta.columns) else None
            st = int(meta.iloc[i]["step"]) if (meta is not None and "step" in meta.columns) else None
            ts = str(meta.iloc[i]["timestamp"]) if (meta is not None and "timestamp" in meta.columns) else None

            exp = self.explain_observation(
                row_x,
                machine_id=m_id,
                step=st,
                timestamp=ts,
                nsamples=nsamples
            )
            explanations.append(exp)

        return explanations
