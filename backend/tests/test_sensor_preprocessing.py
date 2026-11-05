"""
Unit & Integration Tests for Sensor Preprocessing & Sequence Generation Pipeline
Department of AI & Data Science — RMK Engineering College
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import joblib
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.preprocessing.sensor_preprocessing import SensorPreprocessor, run_preprocessing_pipeline

DATA_DIR = "data/processed"
MODELS_DIR = "ml/models_store"


@pytest.fixture(scope="module")
def preprocessed_data():
    """Runs or verifies preprocessing pipeline artifacts."""
    train_npz = os.path.join(DATA_DIR, "sequences_train.npz")
    val_npz = os.path.join(DATA_DIR, "sequences_val.npz")
    test_npz = os.path.join(DATA_DIR, "sequences_test.npz")
    meta_csv = os.path.join(DATA_DIR, "clean_sensor_windows.csv")
    scaler_joblib = os.path.join(MODELS_DIR, "sensor_scaler.joblib")

    if not (os.path.exists(train_npz) and os.path.exists(val_npz) and os.path.exists(test_npz) and os.path.exists(meta_csv)):
        run_preprocessing_pipeline()

    train_data = np.load(train_npz)
    val_data = np.load(val_npz)
    test_data = np.load(test_npz)
    meta_df = pd.read_csv(meta_csv)
    scaler = joblib.load(scaler_joblib)

    return {
        "train": train_data,
        "val": val_data,
        "test": test_data,
        "meta": meta_df,
        "scaler": scaler
    }


def test_scaler_fitted_strictly_on_train(preprocessed_data):
    """Test 1: Verify StandardScaler is fitted on exactly 28,000 samples and mean/std match train set."""
    scaler = preprocessed_data["scaler"]
    raw_train = pd.read_csv(os.path.join(DATA_DIR, "sensor_train.csv"))

    # Check number of samples
    assert scaler.n_samples_seen_ == 28000

    # Check means match raw_train features
    for idx, col in enumerate(SensorPreprocessor.FEATURE_COLS):
        expected_mean = float(raw_train[col].mean())
        assert abs(scaler.mean_[idx] - expected_mean) < 1e-4

    # Check scaled train has mean ~ 0 and std ~ 1
    scaled_train = pd.read_csv(os.path.join(DATA_DIR, "scaled_sensor_train.csv"))
    for col in SensorPreprocessor.FEATURE_COLS:
        assert abs(scaled_train[col].mean()) < 1e-4
        assert abs(scaled_train[col].std(ddof=0) - 1.0) < 1e-3


def test_zero_missing_values_and_duplicates():
    """Test 2: Verify zero missing values and zero duplicate machine-timestamp records."""
    for split in ["train", "val", "test"]:
        scaled_df = pd.read_csv(os.path.join(DATA_DIR, f"scaled_sensor_{split}.csv"))
        # Zero nulls
        assert scaled_df.isnull().sum().sum() == 0
        # Zero duplicates
        assert scaled_df.duplicated(subset=["machine_id", "timestamp"]).sum() == 0


def test_sequence_dimensions_and_dtype(preprocessed_data):
    """Test 3: Verify (30, 5) shape and float32 dtype across all partitions."""
    X_train = preprocessed_data["train"]["X"]
    X_val = preprocessed_data["val"]["X"]
    X_test = preprocessed_data["test"]["X"]

    assert X_train.shape == (2780, 30, 5)
    assert X_val.shape == (580, 30, 5)
    assert X_test.shape == (580, 30, 5)

    assert X_train.dtype == np.float32
    assert X_val.dtype == np.float32
    assert X_test.dtype == np.float32

    assert not np.isnan(X_train).any()
    assert not np.isnan(X_val).any()
    assert not np.isnan(X_test).any()


def test_zero_boundary_crossing_windows(preprocessed_data):
    """Test 4: Verify that no sequence window crosses partition temporal boundaries."""
    meta_df = preprocessed_data["meta"]
    raw_train = pd.read_csv(os.path.join(DATA_DIR, "sensor_train.csv"))
    raw_val = pd.read_csv(os.path.join(DATA_DIR, "sensor_val.csv"))
    raw_test = pd.read_csv(os.path.join(DATA_DIR, "sensor_test.csv"))

    for machine_id in meta_df["machine_id"].unique():
        tr_max = raw_train[raw_train["machine_id"] == machine_id]["timestamp"].max()
        va_min = raw_val[raw_val["machine_id"] == machine_id]["timestamp"].min()
        va_max = raw_val[raw_val["machine_id"] == machine_id]["timestamp"].max()
        te_min = raw_test[raw_test["machine_id"] == machine_id]["timestamp"].min()

        mach_meta = meta_df[meta_df["machine_id"] == machine_id]

        # Train windows must not reach or exceed val_min
        tr_wins = mach_meta[mach_meta["partition"] == "train"]
        assert (tr_wins["end_time"] <= tr_max).all()
        assert (tr_wins["end_time"] < va_min).all()

        # Val windows must be strictly inside [va_min, va_max]
        va_wins = mach_meta[mach_meta["partition"] == "val"]
        assert (va_wins["start_time"] >= va_min).all()
        assert (va_wins["end_time"] <= va_max).all()
        assert (va_wins["end_time"] < te_min).all()

        # Test windows must be >= te_min
        te_wins = mach_meta[mach_meta["partition"] == "test"]
        assert (te_wins["start_time"] >= te_min).all()


def test_straddling_windows_elimination(preprocessed_data):
    """Test 5: Verify that exactly 40 straddling windows were eliminated (3980 -> 3940)."""
    meta_df = preprocessed_data["meta"]
    assert len(meta_df) == 3940

    train_count = len(meta_df[meta_df["partition"] == "train"])
    val_count = len(meta_df[meta_df["partition"] == "val"])
    test_count = len(meta_df[meta_df["partition"] == "test"])

    assert train_count == 2780
    assert val_count == 580
    assert test_count == 580


def test_zero_cross_machine_windows(preprocessed_data):
    """Test 6: Verify that each window metadata and tensor correspond to a single machine."""
    meta_df = preprocessed_data["meta"]
    for win_id in meta_df["window_id"]:
        parts = win_id.split("_")
        # Format: WIN_{PARTITION}_{MACHINE_ID}_{IDX}
        assert len(parts) == 4
        assert parts[2] in [f"M1{i:02d}" for i in range(1, 11)]


def test_metadata_and_label_preservation(preprocessed_data):
    """Test 7: Verify preservation of anomaly labels, failure risk, and fault types."""
    meta_df = preprocessed_data["meta"]

    # Anomaly labels are binary
    assert set(meta_df["is_anomaly"].unique()).issubset({0, 1})

    # Failure risk is in [0, 1]
    assert (meta_df["end_failure_risk"] >= 0.0).all()
    assert (meta_df["end_failure_risk"] <= 1.0).all()

    # Fault types are non-empty strings
    expected_faults = {"normal", "bearing_wear", "overheating", "pressure_drop", "lubrication_failure"}
    assert set(meta_df["fault_type"].unique()).issubset(expected_faults)


def test_reproducibility_and_inversion(preprocessed_data):
    """Test 8: Verify inverse transformation recovers original sensor telemetry."""
    preprocessor = SensorPreprocessor()
    preprocessor.load_scaler(os.path.join(MODELS_DIR, "sensor_scaler.joblib"))

    raw_train = pd.read_csv(os.path.join(DATA_DIR, "sensor_train.csv"))
    scaled_train = pd.read_csv(os.path.join(DATA_DIR, "scaled_sensor_train.csv"))

    recovered_values = preprocessor.inverse_transform(scaled_train[SensorPreprocessor.FEATURE_COLS].values)
    original_values = raw_train[SensorPreprocessor.FEATURE_COLS].values

    np.testing.assert_allclose(recovered_values, original_values, rtol=1e-5, atol=1e-5)
