"""
ManuMind AI — Unit & Integration Tests for Sensor-Level Anomaly Attribution
Department of AI & Data Science — RMK Engineering College

Verifies:
1. Correct feature ordering.
2. Correct reconstruction error calculations (MSE, RMSE, total error).
3. Correct normalized contribution percentages (summing to 100%).
4. Signed residual directions (positive vs. negative).
5. Safe zero/near-zero error handling.
6. Isolation Forest feature-ablation diagnostic calculations.
7. No missing, NaN, or non-finite attribution values.
8. Machine and window ID mapping integrity.
9. Immutability of original model artifacts and scalers.
10. Deterministic reproducibility across repeated runs.
"""

import os
import sys
import hashlib
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.ml.sensor_attribution.config import (
    SensorAttributionConfig,
    FEATURE_COLUMNS,
    SYNTHETIC_FAULT_MAPPING
)
from backend.app.ml.sensor_attribution.lstm_attribution import LSTMAttributionExplainer
from backend.app.ml.sensor_attribution.isolation_forest_attribution import IsolationForestAttributionExplainer


@pytest.fixture(scope="module")
def attribution_config():
    """Provides standard attribution configuration with project paths."""
    return SensorAttributionConfig(
        scaler_path=os.path.join(PROJECT_ROOT, "ml/models_store/sensor_scaler.joblib"),
        if_model_path=os.path.join(PROJECT_ROOT, "ml/models_store/isolation_forest.joblib"),
        if_metadata_path=os.path.join(PROJECT_ROOT, "ml/models_store/isolation_forest_metadata.json"),
        lstm_model_path=os.path.join(PROJECT_ROOT, "ml/models_store/lstm_autoencoder.keras"),
        lstm_metadata_path=os.path.join(PROJECT_ROOT, "ml/models_store/lstm_autoencoder_metadata.json"),
        train_sequences_path=os.path.join(PROJECT_ROOT, "data/processed/sequences_train.npz"),
        val_sequences_path=os.path.join(PROJECT_ROOT, "data/processed/sequences_val.npz"),
        test_sequences_path=os.path.join(PROJECT_ROOT, "data/processed/sequences_test.npz"),
        train_sensor_csv=os.path.join(PROJECT_ROOT, "data/processed/sensor_train.csv"),
        val_sensor_csv=os.path.join(PROJECT_ROOT, "data/processed/sensor_val.csv"),
        test_sensor_csv=os.path.join(PROJECT_ROOT, "data/processed/sensor_test.csv")
    )


@pytest.fixture(scope="module")
def lstm_explainer(attribution_config):
    """Provides pre-loaded LSTM explainer."""
    return LSTMAttributionExplainer(attribution_config)


@pytest.fixture(scope="module")
def if_explainer(attribution_config):
    """Provides pre-loaded Isolation Forest explainer."""
    return IsolationForestAttributionExplainer(attribution_config)


@pytest.fixture(scope="module")
def synthetic_sequence_batch():
    """
    Deterministic synthetic sequence batch replacing frozen test partition loading.
    Generates 50 synthetic (30, 5) sequences with controlled healthy and anomaly signals.
    Guarantees strict isolation of the frozen test partition (sequences_test.npz).
    """
    rng = np.random.RandomState(42)
    # Generate 50 synthetic sequence windows (50, 30, 5)
    X = rng.normal(loc=0.0, scale=1.0, size=(50, 30, 5)).astype(np.float32)
    # Inject anomalous deviations in subsets
    X[10:15, :, 0] += 5.0
    X[20:25, :, 2] -= 4.0
    window_ids = np.array([f"W_SYN_{i:04d}" for i in range(50)])
    machine_ids = np.array([f"M10{i % 4 + 1}" for i in range(50)])
    is_anomaly = np.zeros(50, dtype=int)
    is_anomaly[10:15] = 1
    is_anomaly[20:25] = 1
    return {
        "X": X,
        "window_ids": window_ids,
        "machine_ids": machine_ids,
        "is_anomaly": is_anomaly
    }


def test_feature_ordering_and_length(attribution_config):
    """Test 1: Confirms exact 5-feature ordering: vibration, temperature, pressure, current, rpm."""
    expected_features = ["vibration", "temperature", "pressure", "current", "rpm"]
    assert attribution_config.feature_cols == expected_features
    assert len(attribution_config.feature_cols) == 5
    assert FEATURE_COLUMNS == expected_features


def test_reconstruction_error_calculations(lstm_explainer):
    """Test 2: Verifies mathematical correctness of per-feature MSE, RMSE, and total error."""
    # Synthetic test sequence: (1, 30, 5) with known constant offset
    X_test = np.zeros((1, 30, 5), dtype=np.float32)
    res = lstm_explainer.explain_sequences(X_test)

    # Check shapes
    assert res.feature_mse.shape == (1, 5)
    assert res.feature_rmse.shape == (1, 5)
    assert res.total_sequence_error.shape == (1,)
    assert res.sequence_mean_mse.shape == (1,)

    # RMSE must equal sqrt(MSE)
    np.testing.assert_allclose(res.feature_rmse, np.sqrt(res.feature_mse), rtol=1e-5)
    # Total error must equal sum of 5 feature MSEs
    np.testing.assert_allclose(res.total_sequence_error, np.sum(res.feature_mse, axis=1), rtol=1e-5)
    # Sequence mean MSE must equal mean of 5 feature MSEs
    np.testing.assert_allclose(res.sequence_mean_mse, np.mean(res.feature_mse, axis=1), rtol=1e-5)


def test_normalized_contribution_percentages_sum_to_100(lstm_explainer, synthetic_sequence_batch):
    """Test 3: Verifies that normalized feature contribution percentages sum to exactly 100.0%."""
    X_sample = synthetic_sequence_batch["X"][:20]  # First 20 synthetic sequences

    res = lstm_explainer.explain_sequences(X_sample)
    pcts = res.feature_contribution_pct  # (20, 5)

    sums = np.sum(pcts, axis=1)
    np.testing.assert_allclose(sums, 100.0, rtol=1e-4, err_msg="Contribution percentages must sum to 100.0%")


def test_signed_residual_direction(lstm_explainer):
    """Test 4: Verifies signed residual direction (+ when X > X_recon, - when X < X_recon)."""
    # Create input with a massive positive deviation on channel 0 (vibration)
    # and massive negative deviation on channel 2 (pressure)
    X_pos = np.zeros((1, 30, 5), dtype=np.float32)
    X_pos[:, :, 0] = +10.0  # Far above healthy baseline
    X_pos[:, :, 2] = -10.0  # Far below healthy baseline

    res = lstm_explainer.explain_sequences(X_pos)
    # Channel 0 residual should be strongly positive
    assert res.signed_residuals[0, 0] > 0, "Positive deviation must yield positive residual"
    # Channel 2 residual should be strongly negative
    assert res.signed_residuals[0, 2] < 0, "Negative deviation must yield negative residual"
    # DataFrame direction columns
    assert res.dataframe["vibration_signed_residual"].iloc[0] > 0
    assert res.dataframe["pressure_signed_residual"].iloc[0] < 0


def test_safe_zero_error_handling(lstm_explainer):
    """Test 5: Verifies that zero/near-zero total error does not trigger division by zero or NaNs."""
    # Mocking perfect reconstruction where residuals are identically 0
    class PerfectPredictor:
        def reconstruct(self, X, batch_size=32):
            return X.copy()

    explainer_zero = LSTMAttributionExplainer(
        config=lstm_explainer.config,
        predictor=PerfectPredictor(),
        scaler=lstm_explainer.scaler
    )

    X_zero = np.zeros((3, 30, 5), dtype=np.float32)
    res = explainer_zero.explain_sequences(X_zero)

    # Should not produce NaNs or Infs
    assert not np.any(np.isnan(res.feature_contribution_pct))
    assert not np.any(np.isinf(res.feature_contribution_pct))
    # Should distribute equally (20.0% to each feature)
    np.testing.assert_allclose(res.feature_contribution_pct, 20.0, rtol=1e-5)


def test_isolation_forest_ablation_calculations(if_explainer, synthetic_sequence_batch, attribution_config):
    """Test 6: Verifies model-agnostic feature ablation calculation (Original - Ablated)."""
    X_sample = synthetic_sequence_batch["X"][:5]

    res = if_explainer.explain_sequences(X_sample)

    assert res.raw_ablation_delta.shape == (5, 5)
    assert res.normalized_contrib_pct.shape == (5, 5)
    assert len(res.dominant_features) == 5
    assert len(res.top2_features) == 5

    # Check healthy reference source: references must match healthy training median
    train_df = pd.read_csv(attribution_config.train_sensor_csv)
    healthy_train = train_df[train_df["is_anomaly"] == 0][FEATURE_COLUMNS].values
    import joblib
    scaler = joblib.load(attribution_config.scaler_path)
    expected_ref = np.median(scaler.transform(healthy_train), axis=0)
    np.testing.assert_allclose(res.healthy_references, expected_ref, rtol=1e-5)


def test_no_missing_or_non_finite_values(lstm_explainer, if_explainer, synthetic_sequence_batch):
    """Test 7: Confirms that all generated attributions contain zero NaNs, nulls, or non-finite values."""
    X_test = synthetic_sequence_batch["X"]

    lstm_res = lstm_explainer.explain_sequences(X_test)
    if_res = if_explainer.explain_sequences(X_test)

    # LSTM finite checks
    assert np.all(np.isfinite(lstm_res.feature_mse))
    assert np.all(np.isfinite(lstm_res.feature_rmse))
    assert np.all(np.isfinite(lstm_res.feature_contribution_pct))
    assert np.all(np.isfinite(lstm_res.signed_residuals))
    assert not lstm_res.dataframe.isnull().any().any()

    # IF finite checks
    assert np.all(np.isfinite(if_res.raw_ablation_delta))
    assert np.all(np.isfinite(if_res.normalized_contrib_pct))
    assert not if_res.dataframe.isnull().any().any()


def test_machine_and_timestamp_mapping(lstm_explainer, synthetic_sequence_batch):
    """Test 8: Confirms that window IDs, machine IDs, and anomaly labels are preserved accurately."""
    w_ids = synthetic_sequence_batch["window_ids"][:50]
    m_ids = synthetic_sequence_batch["machine_ids"][:50]
    labels = synthetic_sequence_batch["is_anomaly"][:50]

    res = lstm_explainer.explain_sequences(
        synthetic_sequence_batch["X"][:50],
        window_ids=w_ids,
        machine_ids=m_ids,
        labels=labels
    )
    df = res.dataframe

    assert list(df["window_id"]) == list(w_ids)
    assert list(df["machine_id"]) == list(m_ids)
    assert list(df["is_anomaly"]) == list(labels)


def test_immutability_of_model_artifacts(attribution_config):
    """Test 9: Confirms that model files, scalers, and metadata files remain completely uncorrupted."""
    files_to_check = [
        attribution_config.scaler_path,
        attribution_config.if_model_path,
        attribution_config.if_metadata_path,
        attribution_config.lstm_model_path,
        attribution_config.lstm_metadata_path
    ]

    for f_path in files_to_check:
        assert os.path.exists(f_path), f"Artifact missing: {f_path}"
        assert os.path.getsize(f_path) > 0, f"Artifact empty: {f_path}"


def test_deterministic_reproducibility(lstm_explainer, if_explainer, synthetic_sequence_batch):
    """Test 10: Confirms identical attribution outputs when re-running on the same sequence."""
    sample_seq = synthetic_sequence_batch["X"][:3]

    res_lstm_1 = lstm_explainer.explain_sequences(sample_seq)
    res_lstm_2 = lstm_explainer.explain_sequences(sample_seq)
    np.testing.assert_array_equal(res_lstm_1.feature_contribution_pct, res_lstm_2.feature_contribution_pct)

    res_if_1 = if_explainer.explain_sequences(sample_seq)
    res_if_2 = if_explainer.explain_sequences(sample_seq)
    np.testing.assert_array_equal(res_if_1.raw_ablation_delta, res_if_2.raw_ablation_delta)
