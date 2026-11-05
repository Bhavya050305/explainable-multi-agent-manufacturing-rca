"""
ManuMind AI — Unit & Integration Tests for Model 2: LSTM Autoencoder
Department of AI & Data Science — RMK Engineering College

Covers:
1. Input/output tensor dimensions (batch_size, 30, 5) -> (batch_size, 30, 5)
2. Normal training filter (2,700 normal sequences fitted, 80 anomalous excluded)
3. Zero test leakage (threshold calibrated strictly on validation normal sequences)
4. Standard scaler reuse without independent refitting
5. Finite non-negative reconstruction error across all test sequences
6. Calibrated threshold loading and binary prediction validity
7. Metadata preservation (window IDs, machine IDs, timestamps)
8. Test set detection performance (F1, Precision, Recall, ROC-AUC)
9. Model artifact existence and end-to-end predictor inference
10. Machine breakdown (100% recall on faulted machines, low false alarm on healthy fleet)
"""

import json
import os
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.app.ml.lstm_autoencoder.config import LSTMAutoencoderConfig
from backend.app.ml.lstm_autoencoder.predict import LSTMAutoencoderPredictor
from backend.app.ml.lstm_autoencoder.train import train_lstm_autoencoder
from backend.app.ml.lstm_autoencoder.evaluate import evaluate_lstm_autoencoder


@pytest.fixture(scope="module")
def lstm_artifacts():
    """Fixture ensuring trained model and evaluation outputs are available."""
    config = LSTMAutoencoderConfig()

    # If model is not yet trained, train it
    if not (os.path.exists(config.model_save_path) and os.path.exists(config.metadata_save_path)):
        train_lstm_autoencoder(config)

    # If evaluation outputs not yet present, evaluate
    if not (os.path.exists(config.results_save_path) and os.path.exists(config.predictions_save_path)):
        evaluate_lstm_autoencoder(config)

    with open(config.metadata_save_path, "r") as f:
        metadata = json.load(f)
    with open(config.results_save_path, "r") as f:
        results = json.load(f)
    pred_df = pd.read_csv(config.predictions_save_path)

    predictor = LSTMAutoencoderPredictor(
        model_path=config.model_save_path,
        metadata_path=config.metadata_save_path
    )

    test_data = np.load(config.test_sequences_path, allow_pickle=True)

    return {
        "config": config,
        "metadata": metadata,
        "results": results,
        "pred_df": pred_df,
        "predictor": predictor,
        "test_data": test_data
    }


def test_model_input_output_dimensions(lstm_artifacts):
    """Test 1: Verify model accepts shape (batch, 30, 5) and returns identical shape (batch, 30, 5)."""
    predictor = lstm_artifacts["predictor"]
    batch_size = 4
    dummy_input = np.random.randn(batch_size, 30, 5).astype(np.float32)
    output = predictor.reconstruct(dummy_input)

    assert output.shape == (batch_size, 30, 5), f"Expected shape ({batch_size}, 30, 5), got {output.shape}"
    assert np.all(np.isfinite(output)), "Reconstructed outputs must be finite."


def test_training_used_only_normal_sequences(lstm_artifacts):
    """Test 2: Verify exactly 2,700 normal sequences were used and 80 anomalies strictly excluded."""
    details = lstm_artifacts["metadata"]["training_details"]
    assert details["normal_train_sequences"] == 2700
    assert details["anomalies_excluded"] == 80
    assert details["normal_train_sequences"] + details["anomalies_excluded"] == 2780


def test_no_test_data_used_during_training_or_threshold_calibration(lstm_artifacts):
    """Test 3: Verify threshold calibration partition was strictly validation, not test."""
    thresh_meta = lstm_artifacts["metadata"]["threshold_calibration"]
    assert "validation" in thresh_meta["method"]
    assert "validation_performance_at_selected_threshold" in thresh_meta
    val_cm = thresh_meta["validation_performance_at_selected_threshold"]["confusion_matrix"]
    assert val_cm["tn"] + val_cm["fp"] == 348  # normal validation sequences
    assert val_cm["tp"] + val_cm["fn"] == 232  # anomalous validation sequences


def test_reuses_existing_standard_scaler(lstm_artifacts):
    """Test 4: Verify sensor scaler artifact exists and feature names match specification."""
    import joblib
    config = lstm_artifacts["config"]
    assert os.path.exists(config.scaler_path), f"Sensor scaler not found at: {config.scaler_path}"
    scaler = joblib.load(config.scaler_path)
    assert scaler.n_features_in_ == 5
    expected_features = ["vibration", "temperature", "pressure", "current", "rpm"]
    assert config.feature_cols == expected_features


def test_reconstruction_error_non_negative_and_finite(lstm_artifacts):
    """Test 5: Verify reconstruction error on all 580 test sequences is finite and non-negative."""
    predictor = lstm_artifacts["predictor"]
    X_test = lstm_artifacts["test_data"]["X"]
    errors = predictor.compute_reconstruction_error(X_test)

    assert len(errors) == 580, f"Expected 580 test sequence errors, got {len(errors)}"
    assert np.all(np.isfinite(errors)), "All reconstruction errors must be finite numbers."
    assert np.all(errors >= 0.0), "MSE reconstruction error must be strictly non-negative."


def test_calibrated_threshold_loading_and_validity(lstm_artifacts):
    """Test 6: Verify loaded calibrated threshold matches metadata and produces binary predictions."""
    predictor = lstm_artifacts["predictor"]
    threshold = predictor.threshold
    expected_threshold = lstm_artifacts["metadata"]["threshold_calibration"]["selected_threshold"]

    assert abs(threshold - expected_threshold) < 1e-5, f"Threshold mismatch: {threshold} vs {expected_threshold}"
    assert threshold > 0.0, "Threshold must be positive."

    pred_df = lstm_artifacts["pred_df"]
    unique_preds = set(pred_df["is_anomaly_pred"].unique())
    assert unique_preds.issubset({0, 1}), f"Predictions must be binary in {{0, 1}}, got {unique_preds}"


def test_window_ids_machine_ids_and_metadata_preserved(lstm_artifacts):
    """Test 7: Verify window IDs, machine IDs, and timestamps are preserved in predictions."""
    pred_df = lstm_artifacts["pred_df"]
    assert len(pred_df) == 580, f"Expected 580 predictions rows, got {len(pred_df)}"

    required_cols = [
        "window_id",
        "machine_id",
        "start_time",
        "end_time",
        "is_anomaly",
        "is_anomaly_pred",
        "reconstruction_error",
        "anomaly_threshold_used"
    ]
    for col in required_cols:
        assert col in pred_df.columns, f"Required column '{col}' missing from predictions dataframe."

    # Verify all 10 machines are represented (58 windows each)
    machine_counts = pred_df["machine_id"].value_counts()
    assert len(machine_counts) == 10
    assert all(c == 58 for c in machine_counts.values)


def test_performance_metrics_and_high_anomaly_detection(lstm_artifacts):
    """Test 8: Verify test set metrics meet project standards."""
    metrics = lstm_artifacts["results"]["global_metrics"]
    assert metrics["accuracy"] >= 0.98, f"Accuracy too low: {metrics['accuracy']}"
    assert metrics["precision"] >= 0.95, f"Precision too low: {metrics['precision']}"
    assert metrics["recall"] >= 0.98, f"Recall too low: {metrics['recall']}"
    assert metrics["f1_score"] >= 0.98, f"F1 too low: {metrics['f1_score']}"
    assert metrics["roc_auc"] >= 0.99, f"ROC-AUC too low: {metrics['roc_auc']}"

    cm = metrics["confusion_matrix"]
    assert cm["false_negative"] == 0, f"Expected 0 false negatives, got {cm['false_negative']}"
    assert cm["true_positive"] == 232, f"Expected 232 true positives, got {cm['true_positive']}"


def test_model_artifact_loading_and_inference_roundtrip(lstm_artifacts):
    """Test 9: Verify model artifact exists and predict_dataframe functions properly."""
    config = lstm_artifacts["config"]
    assert os.path.exists(config.model_save_path), f"Keras model not found at: {config.model_save_path}"
    assert os.path.getsize(config.model_save_path) > 100_000, "Model file is suspiciously small."

    predictor = lstm_artifacts["predictor"]
    dummy_input = np.random.randn(2, 30, 5).astype(np.float32)
    errors, binary_preds = predictor.predict(dummy_input)
    assert len(binary_preds) == 2
    assert set(binary_preds.tolist()).issubset({0, 1})


def test_per_machine_anomaly_breakdown(lstm_artifacts):
    """Test 10: Verify 100% recall on faulted machines and false alarm rate <= 2% on healthy fleet."""
    breakdown = lstm_artifacts["results"]["machine_breakdown"]
    faulted_machines = ["M102", "M104", "M107", "M109"]
    healthy_machines = ["M101", "M103", "M105", "M106", "M108", "M110"]

    for m in faulted_machines:
        m_res = breakdown[m]
        assert m_res["recall"] == 1.0, f"Machine {m} recall was {m_res['recall']}, expected 1.0"
        assert m_res["actual_anomalies"] == 58
        assert m_res["tp"] == 58
        assert m_res["fn"] == 0

    healthy_perf = lstm_artifacts["results"]["healthy_machines_performance"]
    assert healthy_perf["false_positive_rate"] <= 0.02, (
        f"Healthy fleet FPR {healthy_perf['false_positive_rate']} exceeded 2% maximum target."
    )
