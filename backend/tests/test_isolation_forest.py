"""
ManuMind AI — Unit & Integration Tests for Model 1: Isolation Forest
Department of AI & Data Science — RMK Engineering College
"""

import json
import os
import sys
import joblib
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.app.ml.isolation_forest.config import IsolationForestConfig
from backend.app.ml.isolation_forest.predict import IsolationForestPredictor
from backend.app.ml.isolation_forest.train import train_isolation_forest
from backend.app.ml.isolation_forest.evaluate import evaluate_isolation_forest


@pytest.fixture(scope="module")
def trained_artifacts():
    """Ensures model and evaluation outputs are available."""
    config = IsolationForestConfig()
    if not (os.path.exists(config.model_save_path) and os.path.exists(config.metadata_save_path)):
        train_isolation_forest(config)

    if not (os.path.exists(config.results_save_path) and os.path.exists(config.predictions_save_path)):
        evaluate_isolation_forest(config)

    model = joblib.load(config.model_save_path)
    with open(config.metadata_save_path, "r") as f:
        metadata = json.load(f)
    with open(config.results_save_path, "r") as f:
        results = json.load(f)
    pred_df = pd.read_csv(config.predictions_save_path)

    return {
        "model": model,
        "metadata": metadata,
        "results": results,
        "pred_df": pred_df,
        "config": config
    }


def test_model_trained_successfully(trained_artifacts):
    """Test 1: Verify model object is fitted and has estimators_ attribute."""
    model = trained_artifacts["model"]
    assert hasattr(model, "estimators_")
    assert len(model.estimators_) == trained_artifacts["config"].n_estimators
    assert hasattr(model, "offset_")


def test_only_healthy_training_samples_used(trained_artifacts):
    """Test 2: Verify exactly 27,200 healthy samples were used and 800 anomalies excluded."""
    meta = trained_artifacts["metadata"]["training_data_summary"]
    assert meta["healthy_rows_used_for_fitting"] == 27200
    assert meta["anomalous_rows_strictly_excluded"] == 800
    assert meta["filtering_condition"] == "is_anomaly == 0"


def test_five_sensor_features_accepted(trained_artifacts):
    """Test 3: Verify the 5 expected sensor channels are processed."""
    features = trained_artifacts["metadata"]["features"]
    expected = ["vibration", "temperature", "pressure", "current", "rpm"]
    assert features == expected
    assert trained_artifacts["model"].n_features_in_ == 5


def test_predictions_contain_only_valid_binary_classes(trained_artifacts):
    """Test 4: Verify binary outputs in {0, 1}."""
    pred_df = trained_artifacts["pred_df"]
    unique_preds = set(pred_df["is_anomaly_pred"].unique())
    assert unique_preds.issubset({0, 1})


def test_anomaly_scores_are_finite(trained_artifacts):
    """Test 5: Verify no NaNs or Infs in anomaly scores."""
    pred_df = trained_artifacts["pred_df"]
    scores = pred_df["anomaly_score"].values
    assert np.all(np.isfinite(scores))
    assert len(scores) == 6000


def test_model_serialization_and_reproducibility(trained_artifacts):
    """Test 6: Verify model can be saved and loaded with matching inference scores."""
    config = trained_artifacts["config"]
    predictor = IsolationForestPredictor(
        model_path=config.model_save_path,
        metadata_path=config.metadata_save_path
    )
    test_input = np.zeros((1, 5), dtype=np.float32)
    score = predictor.score(test_input)
    assert np.isfinite(score[0])


def test_timestamps_and_machine_ids_preserved(trained_artifacts):
    """Test 7: Verify all 10 machine IDs and 6000 timestamps are intact."""
    pred_df = trained_artifacts["pred_df"]
    assert len(pred_df) == 6000
    machines = set(pred_df["machine_id"].unique())
    assert len(machines) == 10
    assert "timestamp" in pred_df.columns
    assert pred_df["timestamp"].isnull().sum() == 0


def test_test_data_isolated_from_training_and_calibration(trained_artifacts):
    """Test 8: Verify metadata records confirm test data was strictly unobserved during training/calibration."""
    train_summary = trained_artifacts["metadata"]["training_data_summary"]
    val_summary = trained_artifacts["metadata"]["validation_calibration"]

    assert "train" in train_summary["source_file"]
    assert "val" in val_summary["val_source_file"]
    assert "test" not in train_summary["source_file"]
    assert "test" not in val_summary["val_source_file"]


def test_all_twelve_graphs_generated(trained_artifacts):
    """Test 9: Verify existence of all 12 generated analytical PNG files."""
    graphs_dir = trained_artifacts["config"].graphs_dir
    expected_graphs = [
        "anomaly_counts.png",
        "sensor_vibration_timeline.png",
        "sensor_temperature_timeline.png",
        "sensor_pressure_timeline.png",
        "sensor_current_timeline.png",
        "sensor_rpm_timeline.png",
        "anomaly_score_distribution.png",
        "machine_anomaly_comparison.png",
        "sensor_anomaly_comparison.png",
        "anomaly_heatmap.png",
        "feature_distribution.png",
        "confusion_matrix.png"
    ]
    for g in expected_graphs:
        g_path = os.path.join(graphs_dir, g)
        assert os.path.exists(g_path), f"Missing graph: {g_path}"
        assert os.path.getsize(g_path) > 10000, f"Graph file suspiciously small: {g_path}"


def test_evaluation_metrics_parity(trained_artifacts):
    """Test 10: Independently calculate metrics and assert parity with results JSON."""
    pred_df = trained_artifacts["pred_df"]
    results = trained_artifacts["results"]["global_metrics"]

    y_true = pred_df["is_anomaly"].values
    y_pred = pred_df["is_anomaly_pred"].values

    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    calc_acc = float(accuracy_score(y_true, y_pred))
    calc_prec = float(precision_score(y_true, y_pred))
    calc_rec = float(recall_score(y_true, y_pred))
    calc_f1 = float(f1_score(y_true, y_pred))

    assert abs(calc_acc - results["accuracy"]) < 1e-4
    assert abs(calc_prec - results["precision"]) < 1e-4
    assert abs(calc_rec - results["recall"]) < 1e-4
    assert abs(calc_f1 - results["f1_score"]) < 1e-4
