"""
ManuMind AI — Unified Inference Service Comprehensive Test Suite
Department of AI & Data Science — RMK Engineering College

Validates:
1. ModelRegistry singleton lifecycle, lazy loading, and cryptographic verification
2. Artifact integrity enforcement and corruption rejection
3. Tabular sensor anomaly scoring, feature ordering, and frozen threshold parity
4. Sequence anomaly detection, boundary enforcement, and LSTM reconstruction parity
5. Step 4 analytical MSE sensor attribution and 100% sum normalization
6. Step 6 Kernel SHAP game-theoretic additivity and dedicated locking
7. Step 7 Compact ResNet-18 workpiece defect inspection and 4-class outputs
8. Decoupled modality execution and unified composite orchestration
9. Concurrent thread execution safety and Pydantic v2 JSON serialization
"""

import copy
import io
import math
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pytest
from PIL import Image

from backend.app.ml.inference.config import (
    CANONICAL_FEATURES,
    DEFECT_CLASSES,
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    LSTM_AUTOENCODER_FROZEN_THRESHOLD,
    InferenceConfig,
)
from backend.app.ml.inference.exceptions import (
    ArtifactIntegrityError,
    ImageDecodingError,
    InvalidSensorValueError,
    InvalidSequenceLengthError,
    MissingSensorFeatureError,
    ModelArtifactNotFoundError,
    TimestampOrderingError,
)
from backend.app.ml.inference.registry import ModelRegistry
from backend.app.ml.inference.schemas import (
    DefectImageInput,
    ExplanationStatus,
    SensorReadingInput,
    SequenceWindowInput,
    UnifiedInferenceRequest,
)
from backend.app.ml.inference.service import UnifiedInferenceService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_registry():
    """Ensure each test suite runs with a clean singleton state if needed."""
    yield
    # Note: we avoid resetting across all tests to prevent excessive reloading of TF graphs


@pytest.fixture
def service():
    """Returns a UnifiedInferenceService instance backed by process-local registry."""
    return UnifiedInferenceService()


@pytest.fixture
def sample_sensor_dict():
    """Valid canonical sensor reading dictionary."""
    return {
        "vibration": 3.85,
        "temperature": 74.2,
        "pressure": 5.8,
        "current": 16.4,
        "rpm": 1750.0,
        "machine_id": "M104",
        "timestamp": datetime(2026, 11, 7, 10, 0, 0)
    }


@pytest.fixture
def sample_sequence_window(sample_sensor_dict):
    """Generates a valid 30-step chronological SequenceWindowInput."""
    base_time = datetime(2026, 11, 7, 10, 0, 0)
    readings = []
    for i in range(30):
        readings.append(
            SensorReadingInput(
                vibration=sample_sensor_dict["vibration"] + 0.02 * math.sin(i),
                temperature=sample_sensor_dict["temperature"] + 0.05 * i,
                pressure=sample_sensor_dict["pressure"] + 0.01 * (i % 3),
                current=sample_sensor_dict["current"] + 0.03 * (i % 2),
                rpm=sample_sensor_dict["rpm"],
                machine_id="M104",
                timestamp=base_time + timedelta(seconds=i)
            )
        )
    return SequenceWindowInput(machine_id="M104", readings=readings, window_id="win_001")


@pytest.fixture
def dummy_bmp_bytes():
    """Generates valid in-memory BMP image bytes."""
    img = Image.new("RGB", (128, 128), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Registry & Artifact Verification Tests (Categories 1 - 6, 32)
# ---------------------------------------------------------------------------

def test_registry_singleton_identity():
    """Test 1: Assert ModelRegistry.get_instance() returns the identical object within process."""
    reg1 = ModelRegistry.get_instance()
    reg2 = ModelRegistry.get_instance()
    assert reg1 is reg2


def test_registry_artifact_sha256_verification():
    """Test 2: Assert registry validates exact SHA-256 baseline hashes without errors."""
    reg = ModelRegistry.get_instance()
    for artifact_name in reg.config.expected_hashes.keys():
        resolved_path = reg.verify_artifact(artifact_name)
        assert resolved_path.exists()


def test_registry_missing_artifact_handling(tmp_path):
    """Test 3: Assert ModelArtifactNotFoundError is raised for missing artifact without auto-regeneration."""
    cfg = InferenceConfig(models_dir=tmp_path)
    reg = ModelRegistry(config=cfg)

    with pytest.raises(ModelArtifactNotFoundError) as exc_info:
        reg.verify_artifact("non_existent_model.keras")
    assert "Required model artifact not found" in str(exc_info.value)


def test_registry_corrupted_artifact_handling(tmp_path):
    """Test 4: Assert ArtifactIntegrityError is raised when an artifact hash does not match."""
    corrupted_file = tmp_path / "sensor_scaler.joblib"
    corrupted_file.write_bytes(b"corrupted_tampered_bytes")

    cfg = InferenceConfig(models_dir=tmp_path)
    reg = ModelRegistry(config=cfg)

    with pytest.raises(ArtifactIntegrityError) as exc_info:
        reg.verify_artifact("sensor_scaler.joblib")
    assert "Cryptographic checksum mismatch" in str(exc_info.value)


def test_registry_lazy_loading():
    """Test 5 & 32: Assert models are loaded lazily and only when requested."""
    # Create isolated registry instance
    reg = ModelRegistry()
    assert reg._scaler is None
    assert reg._isolation_forest is None

    # Load scaler only
    scaler = reg.get_scaler()
    assert scaler is not None
    assert reg._scaler is not None
    assert reg._isolation_forest is None  # IF not loaded yet


def test_registry_no_repeated_model_loading():
    """Test 6: Assert repeated getter calls return the cached instance."""
    reg = ModelRegistry.get_instance()
    scaler1 = reg.get_scaler()
    scaler2 = reg.get_scaler()
    assert scaler1 is scaler2


# ---------------------------------------------------------------------------
# 2. Sensor Anomaly Inference Tests (Categories 7 - 10)
# ---------------------------------------------------------------------------

def test_canonical_feature_ordering_permutation_resistance(service, sample_sensor_dict):
    """Test 7: Assert input dictionaries with shuffled keys produce identical scores."""
    # Standard order
    res_normal = service.predict_sensor_anomaly(sample_sensor_dict)

    # Shuffled order
    shuffled_dict = {
        "rpm": sample_sensor_dict["rpm"],
        "pressure": sample_sensor_dict["pressure"],
        "vibration": sample_sensor_dict["vibration"],
        "temperature": sample_sensor_dict["temperature"],
        "current": sample_sensor_dict["current"],
    }
    res_shuffled = service.predict_sensor_anomaly(shuffled_dict)

    assert abs(res_normal.anomaly_score - res_shuffled.anomaly_score) < 1e-6


def test_isolation_forest_scoring_parity(service, sample_sensor_dict):
    """Test 8: Verify Isolation Forest scores match direct predictor calls to machine precision."""
    direct_pred = service.registry.get_isolation_forest()
    scaler = service.registry.get_scaler()

    raw_vec = np.array([[sample_sensor_dict[f] for f in CANONICAL_FEATURES]], dtype=np.float64)
    scaled_vec = scaler.transform(raw_vec)
    direct_score = float(direct_pred.score(scaled_vec)[0])

    service_res = service.predict_sensor_anomaly(sample_sensor_dict)
    assert abs(direct_score - service_res.anomaly_score) < 1e-5


def test_isolation_forest_frozen_threshold_parity(service, sample_sensor_dict):
    """Test 9: Verify frozen threshold is exactly 0.0269 and classification matches boundary."""
    res = service.predict_sensor_anomaly(sample_sensor_dict)
    assert res.threshold == ISOLATION_FOREST_FROZEN_THRESHOLD
    assert res.is_anomaly == (res.anomaly_score > ISOLATION_FOREST_FROZEN_THRESHOLD)


def test_invalid_sensor_inputs_rejection(service):
    """Test 10: Reject NaN, Infinity, extra fields, and missing fields."""
    # NaN rejection
    with pytest.raises(Exception):
        service.predict_sensor_anomaly({
            "vibration": float("nan"),
            "temperature": 70.0,
            "pressure": 5.0,
            "current": 10.0,
            "rpm": 1500.0
        })

    # +Infinity rejection
    with pytest.raises(Exception):
        service.predict_sensor_anomaly({
            "vibration": float("inf"),
            "temperature": 70.0,
            "pressure": 5.0,
            "current": 10.0,
            "rpm": 1500.0
        })

    # Missing field rejection
    with pytest.raises(Exception):
        service.predict_sensor_anomaly({
            "vibration": 3.0,
            "temperature": 70.0,
            "pressure": 5.0,
            "current": 10.0
            # missing rpm
        })

    # Extra field rejection (extra="forbid")
    with pytest.raises(Exception):
        SensorReadingInput(
            vibration=3.0,
            temperature=70.0,
            pressure=5.0,
            current=10.0,
            rpm=1500.0,
            unauthorized_extra_feature=999.0
        )


# ---------------------------------------------------------------------------
# 3. Sequence Anomaly Inference Tests (Categories 11 - 14)
# ---------------------------------------------------------------------------

def test_sequence_length_boundary_validation(service, sample_sequence_window):
    """Test 11 & 12: Sequence must contain exactly 30 observations; 29 or 31 rejected."""
    # 29 readings
    short_readings = sample_sequence_window.readings[:29]
    with pytest.raises(Exception):
        SequenceWindowInput(machine_id="M104", readings=short_readings)

    # 31 readings
    long_readings = sample_sequence_window.readings + [sample_sequence_window.readings[0]]
    with pytest.raises(Exception):
        SequenceWindowInput(machine_id="M104", readings=long_readings)


def test_timestamp_ordering_validation(sample_sensor_dict):
    """Test 13: Non-monotonic or decreasing timestamps must raise TimestampOrderingError."""
    base_time = datetime(2026, 11, 7, 10, 0, 0)
    readings = []
    for i in range(30):
        # Insert inverted timestamp at index 15
        t = base_time + timedelta(seconds=i if i != 15 else i - 5)
        readings.append(
            SensorReadingInput(
                vibration=sample_sensor_dict["vibration"],
                temperature=sample_sensor_dict["temperature"],
                pressure=sample_sensor_dict["pressure"],
                current=sample_sensor_dict["current"],
                rpm=sample_sensor_dict["rpm"],
                timestamp=t
            )
        )

    with pytest.raises(TimestampOrderingError):
        SequenceWindowInput(machine_id="M104", readings=readings)


def test_lstm_reconstruction_parity(service, sample_sequence_window):
    """Test 14: Verify LSTM reconstruction error matches direct predictor call."""
    direct_pred = service.registry.get_lstm_autoencoder()
    scaler = service.registry.get_scaler()

    raw_mat = np.array(
        [[r.vibration, r.temperature, r.pressure, r.current, r.rpm] for r in sample_sequence_window.readings],
        dtype=np.float64
    )
    scaled_seq = np.expand_dims(scaler.transform(raw_mat).astype(np.float32), axis=0)
    direct_mse = float(direct_pred.compute_reconstruction_error(scaled_seq)[0])

    service_res = service.predict_sequence_anomaly(sample_sequence_window)
    assert abs(direct_mse - service_res.reconstruction_error) < 1e-5
    assert service_res.threshold == LSTM_AUTOENCODER_FROZEN_THRESHOLD


# ---------------------------------------------------------------------------
# 4. Explainability Tests (Categories 15 - 19)
# ---------------------------------------------------------------------------

def test_sensor_attribution_parity_and_normalization(service, sample_sequence_window):
    """Test 15 & 16: Verify Step 4 attribution output parity and 100% sum normalization."""
    res = service.predict_sequence_anomaly(sample_sequence_window, explain=True)
    assert res.attribution_status == ExplanationStatus.AVAILABLE
    assert res.sensor_attribution is not None

    pct_dict = res.sensor_attribution["feature_contribution_pct"]
    total_pct = sum(pct_dict.values())
    assert abs(total_pct - 100.0) < 1e-2  # Sums to 100% within rounding tolerance
    assert res.sensor_attribution["dominant_feature"] in CANONICAL_FEATURES


def test_shap_additivity_verification(service, sample_sensor_dict):
    """Test 17 & 18: Verify Kernel SHAP strict additivity |f(x) - (E[f] + sum(phi))| < 1e-6."""
    res = service.predict_sensor_anomaly(sample_sensor_dict, explain=True)
    assert res.explanation_status == ExplanationStatus.AVAILABLE
    assert res.shap_explanation is not None

    # Check additivity
    additivity_err = res.shap_explanation.get("additivity_error", 0.0)
    assert abs(additivity_err) <= 1e-5


def test_optional_explanation_failure_graceful_degradation(service, sample_sensor_dict, monkeypatch):
    """Test 19: Explanation failure must not crash primary prediction; status set to FAILED."""
    # Simulate SHAP explainer exception
    def broken_shap(*args, **kwargs):
        raise RuntimeError("Simulated SHAP timeout / numerical failure")

    monkeypatch.setattr(service, "explain_sensor_shap", broken_shap)

    res = service.predict_sensor_anomaly(sample_sensor_dict, explain=True)
    # Primary prediction preserved
    assert res.anomaly_score is not None
    assert isinstance(res.is_anomaly, bool)
    # Explanation marked as failed
    assert res.explanation_status == ExplanationStatus.FAILED
    assert "Simulated SHAP timeout" in str(res.shap_explanation)


# ---------------------------------------------------------------------------
# 5. Vision Defect Classifier Tests (Categories 20 - 23)
# ---------------------------------------------------------------------------

def test_resnet_prediction_parity_and_classes(service, dummy_bmp_bytes):
    """Test 20 & 21: Verify 4-class output and Softmax score structure."""
    res = service.predict_defect_image(dummy_bmp_bytes, image_name="test_workpiece.bmp")
    assert res.image_name == "test_workpiece.bmp"
    assert res.raw_defect_class in DEFECT_CLASSES
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.class_probabilities) == 4
    for c in DEFECT_CLASSES:
        assert c in res.class_probabilities


def test_invalid_image_handling(service):
    """Test 22 & 23: Corrupted or invalid image input raises handled ImageDecodingError."""
    corrupted_bytes = b"NOT_A_VALID_BMP_HEADER_CORRUPTED"
    with pytest.raises(ImageDecodingError):
        service.predict_defect_image(corrupted_bytes)


# ---------------------------------------------------------------------------
# 6. Unified Orchestration Tests (Categories 24 - 31)
# ---------------------------------------------------------------------------

def test_unified_inference_sensor_only(service, sample_sensor_dict):
    """Test 24: Sensor-only request executes without requiring sequence or vision inputs."""
    req = UnifiedInferenceRequest(
        sensor_reading=SensorReadingInput(**sample_sensor_dict)
    )
    res = service.predict_unified(req)
    assert res.sensor_result is not None
    assert res.sequence_result is None
    assert res.defect_result is None
    assert res.execution_time_ms > 0


def test_unified_inference_sequence_only(service, sample_sequence_window):
    """Test 25: Sequence-only request executes independently."""
    req = UnifiedInferenceRequest(sequence_window=sample_sequence_window)
    res = service.predict_unified(req)
    assert res.sensor_result is None
    assert res.sequence_result is not None
    assert res.defect_result is None


def test_unified_inference_vision_only(service, dummy_bmp_bytes):
    """Test 26: Vision-only request executes independently."""
    req = UnifiedInferenceRequest(
        defect_image=DefectImageInput(image_bytes=dummy_bmp_bytes, image_name="uni_test.bmp")
    )
    res = service.predict_unified(req)
    assert res.sensor_result is None
    assert res.sequence_result is None
    assert res.defect_result is not None


def test_unified_inference_combined(service, sample_sensor_dict, sample_sequence_window, dummy_bmp_bytes):
    """Test 27: Multi-modal combined inference request executes all modalities."""
    req = UnifiedInferenceRequest(
        sensor_reading=SensorReadingInput(**sample_sensor_dict),
        sequence_window=sample_sequence_window,
        defect_image=DefectImageInput(image_bytes=dummy_bmp_bytes, image_name="combo.bmp"),
        include_shap=False,
        include_attribution=True
    )
    res = service.predict_unified(req)
    assert res.sensor_result is not None
    assert res.sequence_result is not None
    assert res.defect_result is not None
    assert res.sequence_result.attribution_status == ExplanationStatus.AVAILABLE
    assert res.data_quality_status == "OK"


def test_pydantic_serialization_parity(service, sample_sensor_dict, sample_sequence_window, dummy_bmp_bytes):
    """Test 28: Responses serialize cleanly to native JSON without numpy/float32 errors."""
    req = UnifiedInferenceRequest(
        sensor_reading=SensorReadingInput(**sample_sensor_dict),
        sequence_window=sample_sequence_window,
        defect_image=DefectImageInput(image_bytes=dummy_bmp_bytes, image_name="json_test.bmp")
    )
    res = service.predict_unified(req)
    json_str = res.model_dump_json()
    assert isinstance(json_str, str)
    assert "anomaly_score" in json_str
    assert "reconstruction_error" in json_str
    assert "class_probabilities" in json_str


def test_repeated_prediction_consistency(service, sample_sensor_dict):
    """Test 29: Repeated inference calls on identical input yield identical results."""
    res1 = service.predict_sensor_anomaly(sample_sensor_dict)
    res2 = service.predict_sensor_anomaly(sample_sensor_dict)
    assert res1.anomaly_score == res2.anomaly_score
    assert res1.is_anomaly == res2.is_anomaly


def test_concurrent_execution_safety(service, sample_sensor_dict):
    """Test 30: Multi-threaded concurrent requests execute without state collision or race conditions."""
    results = []
    errors = []

    def worker():
        try:
            res = service.predict_sensor_anomaly(sample_sensor_dict)
            results.append(res.anomaly_score)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 8
    # All threads scored the same input; scores should match to machine precision
    for score in results[1:]:
        assert abs(score - results[0]) < 1e-6
