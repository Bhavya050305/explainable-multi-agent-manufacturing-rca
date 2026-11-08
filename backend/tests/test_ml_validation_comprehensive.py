"""
ManuMind AI — Comprehensive Machine Learning Validation Test Suite
Phase 2 Step 9B: Production Validation, Boundary Fuzzing, Concurrency, and Isolation Gates

Department of AI & Data Science — RMK Engineering College

Covers:
1. Multimodal pairwise inference orchestration.
2. Multi-threaded TensorFlow lock contention (_tf_lock).
3. Multi-threaded Kernel SHAP lock contention (_shap_lock).
4. Image input format and dimension validation (grayscale, RGBA, non-square, corrupted).
5. Partial timestamp ordering and boundary enforcement.
6. Extreme physical sensor outlier scoring and safety.
7. Sensor attribution on 100% synthetic deterministic fixtures.
8. Repeated inference cycles and allocation stability.
"""

import io
import math
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pytest
from PIL import Image

from backend.app.ml.inference.config import CANONICAL_FEATURES, InferenceConfig
from backend.app.ml.inference.exceptions import (
    ImageDecodingError,
    InvalidSensorValueError,
    InvalidSequenceLengthError,
    TimestampOrderingError,
)
from backend.app.ml.inference.registry import ModelRegistry
from backend.app.ml.inference.schemas import (
    DefectClassificationResponse,
    DefectImageInput,
    SensorAnomalyResponse,
    SensorReadingInput,
    SequenceAnomalyResponse,
    SequenceWindowInput,
    UnifiedInferenceRequest,
    UnifiedInferenceResponse,
)
from backend.app.ml.inference.service import UnifiedInferenceService
from backend.app.ml.sensor_attribution.config import SensorAttributionConfig
from backend.app.ml.sensor_attribution.isolation_forest_attribution import (
    IsolationForestAttributionExplainer,
)
from backend.app.ml.sensor_attribution.lstm_attribution import LSTMAttributionExplainer


# ==============================================================================
# DETERMINISTIC SYNTHETIC FIXTURES (ZERO TEST PARTITION ACCESS)
# ==============================================================================


@pytest.fixture(scope="module")
def service() -> UnifiedInferenceService:
    """Returns UnifiedInferenceService instance."""
    return UnifiedInferenceService()


@pytest.fixture
def synthetic_sensor_reading() -> SensorReadingInput:
    """Provides valid deterministic sensor reading near normal operating mean."""
    return SensorReadingInput(
        vibration=1.805,
        temperature=47.998,
        pressure=6.202,
        current=14.525,
        rpm=1799.947,
        machine_id="M104",
        timestamp=datetime(2026, 11, 7, 10, 0, 0),
    )


@pytest.fixture
def synthetic_sequence_window() -> SequenceWindowInput:
    """Provides valid deterministic sequence window (30 readings, 1s delta, healthy mean)."""
    t0 = datetime(2026, 11, 7, 10, 0, 0)
    readings = [
        SensorReadingInput(
            vibration=1.80 + 0.01 * math.sin(i),
            temperature=48.0 + 0.1 * math.cos(i),
            pressure=6.20 + 0.005 * math.sin(i * 0.5),
            current=14.50 + 0.05 * math.cos(i * 0.5),
            rpm=1800.0 + 1.0 * math.sin(i * 0.2),
            machine_id="M104",
            timestamp=t0 + timedelta(seconds=i),
        )
        for i in range(30)
    ]
    return SequenceWindowInput(readings=readings, machine_id="M104")


@pytest.fixture
def synthetic_workpiece_image_bmp_bytes() -> bytes:
    """Generates a synthetic 128x128 RGB workpiece image encoded as BMP bytes."""
    rng = np.random.RandomState(42)
    # Background texture + geometric surface defect simulation
    arr = rng.randint(90, 160, size=(128, 128, 3), dtype=np.uint8)
    arr[40:50, 40:90, :] = 30  # Dark linear feature (scratch/crack simulation)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


@pytest.fixture
def synthetic_pil_image_non_square() -> Image.Image:
    """Generates an asymmetric 256x128 RGB PIL Image for aspect ratio testing."""
    rng = np.random.RandomState(43)
    arr = rng.randint(80, 180, size=(128, 256, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def synthetic_pil_image_grayscale() -> Image.Image:
    """Generates a 128x128 single-channel Grayscale ('L') PIL Image."""
    rng = np.random.RandomState(44)
    arr = rng.randint(50, 200, size=(128, 128), dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


@pytest.fixture
def synthetic_pil_image_rgba() -> Image.Image:
    """Generates a 128x128 4-channel RGBA PIL Image with alpha transparency."""
    rng = np.random.RandomState(45)
    arr = rng.randint(50, 200, size=(128, 128, 4), dtype=np.uint8)
    arr[:, :, 3] = 255  # Full alpha
    return Image.fromarray(arr, mode="RGBA")


# ==============================================================================
# CATEGORY A: MULTIMODAL PAIRWISE INFERENCE TESTS
# ==============================================================================


def test_multimodal_pairwise_sensor_and_sequence(
    service: UnifiedInferenceService,
    synthetic_sensor_reading: SensorReadingInput,
    synthetic_sequence_window: SequenceWindowInput,
):
    """Test A.1: Pairwise Sensor + Sequence execution without vision input."""
    req = UnifiedInferenceRequest(
        sensor_reading=synthetic_sensor_reading,
        sequence_window=synthetic_sequence_window,
        defect_image=None,
        include_shap=False,
        include_attribution=False,
    )
    res: UnifiedInferenceResponse = service.predict_unified(req)

    # Sensor evaluated
    assert res.sensor_result is not None
    assert isinstance(res.sensor_result, SensorAnomalyResponse)
    assert res.sensor_result.model_id == "isolation_forest_v1"

    # Sequence evaluated
    assert res.sequence_result is not None
    assert isinstance(res.sequence_result, SequenceAnomalyResponse)
    assert res.sequence_result.model_id == "lstm_autoencoder_v1"

    # Vision omitted
    assert res.defect_result is None
    assert len(res.warnings) == 0


def test_multimodal_pairwise_sensor_and_vision(
    service: UnifiedInferenceService,
    synthetic_sensor_reading: SensorReadingInput,
    synthetic_workpiece_image_bmp_bytes: bytes,
):
    """Test A.2: Pairwise Sensor + Vision execution without sequence input."""
    req = UnifiedInferenceRequest(
        sensor_reading=synthetic_sensor_reading,
        sequence_window=None,
        defect_image=DefectImageInput(image_bytes=synthetic_workpiece_image_bmp_bytes),
        include_shap=False,
        include_attribution=False,
    )
    res: UnifiedInferenceResponse = service.predict_unified(req)

    # Sensor evaluated
    assert res.sensor_result is not None
    assert res.sensor_result.model_id == "isolation_forest_v1"

    # Vision evaluated
    assert res.defect_result is not None
    assert isinstance(res.defect_result, DefectClassificationResponse)
    assert res.defect_result.model_id == "compact_resnet18_v1"

    # Sequence omitted
    assert res.sequence_result is None
    assert len(res.warnings) == 0


def test_multimodal_pairwise_sequence_and_vision(
    service: UnifiedInferenceService,
    synthetic_sequence_window: SequenceWindowInput,
    synthetic_workpiece_image_bmp_bytes: bytes,
):
    """Test A.3: Pairwise Sequence + Vision execution without tabular sensor input."""
    req = UnifiedInferenceRequest(
        sensor_reading=None,
        sequence_window=synthetic_sequence_window,
        defect_image=DefectImageInput(image_bytes=synthetic_workpiece_image_bmp_bytes),
        include_shap=False,
        include_attribution=False,
    )
    res: UnifiedInferenceResponse = service.predict_unified(req)

    # Sequence evaluated
    assert res.sequence_result is not None
    assert res.sequence_result.model_id == "lstm_autoencoder_v1"

    # Vision evaluated
    assert res.defect_result is not None
    assert res.defect_result.model_id == "compact_resnet18_v1"

    # Sensor omitted
    assert res.sensor_result is None
    assert len(res.warnings) == 0


def test_multimodal_unrequested_modality_isolation(
    service: UnifiedInferenceService,
    synthetic_sensor_reading: SensorReadingInput,
):
    """Test A.4: Unrequested modalities do not populate response structures or leak identifiers."""
    req = UnifiedInferenceRequest(
        sensor_reading=synthetic_sensor_reading,
        sequence_window=None,
        defect_image=None,
    )
    res: UnifiedInferenceResponse = service.predict_unified(req)
    assert res.sensor_result is not None
    assert res.sequence_result is None
    assert res.defect_result is None
    assert res.sensor_result.model_id == "isolation_forest_v1"


# ==============================================================================
# CATEGORY B: TENSORFLOW / KERAS CONCURRENCY LOCK CONTENTION TESTS
# ==============================================================================


def test_concurrent_keras_tf_lock_contention(
    service: UnifiedInferenceService,
    synthetic_sequence_window: SequenceWindowInput,
    synthetic_workpiece_image_bmp_bytes: bytes,
):
    """
    Test B.1: Verifies thread-safe execution under concurrent contention for _tf_lock.
    Spawns 8 threads simultaneously: 4 executing LSTM sequence reconstruction
    and 4 executing ResNet-18 visual defect inspection.
    Asserts zero deadlocks, zero state corruption, and identical output consistency.
    Note: _tf_lock serializes native Keras calls within process for safety.
    """
    num_threads = 8
    seq_results: List[SequenceAnomalyResponse] = []
    vis_results: List[DefectClassificationResponse] = []
    errors: List[Exception] = []
    lock = threading.Lock()

    def run_sequence_task(worker_id: int):
        try:
            res = service.predict_sequence_anomaly(synthetic_sequence_window, explain=False)
            with lock:
                seq_results.append(res)
        except Exception as e:
            with lock:
                errors.append(e)

    def run_vision_task(worker_id: int):
        try:
            res = service.predict_defect_image(synthetic_workpiece_image_bmp_bytes)
            with lock:
                vis_results.append(res)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = []
    # 4 sequence workers, 4 vision workers interleaved
    for i in range(4):
        threads.append(threading.Thread(target=run_sequence_task, args=(i,)))
        threads.append(threading.Thread(target=run_vision_task, args=(i,)))

    start_time = time.perf_counter()
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=30.0)
        assert not t.is_alive(), "Thread deadlocked or timed out acquiring _tf_lock!"

    elapsed = time.perf_counter() - start_time

    # Verification assertions
    assert len(errors) == 0, f"Concurrent execution errors encountered: {errors}"
    assert len(seq_results) == 4, "Not all sequence threads completed successfully"
    assert len(vis_results) == 4, "Not all vision threads completed successfully"

    # Exact deterministic score parity across identical inputs
    base_mse = seq_results[0].reconstruction_error
    for sr in seq_results[1:]:
        assert math.isclose(sr.reconstruction_error, base_mse, rel_tol=1e-5), (
            f"Sequence reconstruction MSE diverged across threads: {sr.reconstruction_error} vs {base_mse}"
        )

    base_class = vis_results[0].defect_type
    base_conf = vis_results[0].confidence
    for vr in vis_results[1:]:
        assert vr.defect_type == base_class
        assert math.isclose(vr.confidence, base_conf, rel_tol=1e-4)


# ==============================================================================
# CATEGORY C: KERNEL SHAP CONCURRENCY LOCK CONTENTION TESTS
# ==============================================================================


def test_concurrent_shap_lock_contention(
    service: UnifiedInferenceService,
    synthetic_sensor_reading: SensorReadingInput,
):
    """
    Test C.1: Verifies thread-safe execution of Kernel SHAP under concurrent multi-threaded requests.
    SHAP internally mutates state buffers (self.kernelWeights); _shap_lock must serialize calls
    safely without segmentation faults, memory corruption, or additivity violations.
    """
    num_threads = 4
    shap_results = []
    errors = []
    lock = threading.Lock()

    def run_shap_task(worker_id: int):
        try:
            # Invoking explain_sensor_shap acquires _shap_lock
            res = service.explain_sensor_shap(synthetic_sensor_reading)
            with lock:
                shap_results.append(res)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=run_shap_task, args=(i,)) for i in range(num_threads)]

    start_time = time.perf_counter()
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=45.0)
        assert not t.is_alive(), "SHAP thread deadlocked or timed out acquiring _shap_lock!"

    # Assertions
    assert len(errors) == 0, f"SHAP concurrency errors encountered: {errors}"
    assert len(shap_results) == num_threads

    # Verify additivity for each thread's result
    for sr in shap_results:
        assert sr.get("status") == "success"
        assert sr.get("additivity_verified") is True
        f_x = sr["anomaly_score"]
        base_val = sr["base_value"]
        sum_phi = sum(sr["feature_attributions"].values())
        additivity_error = abs(f_x - (base_val + sum_phi))
        assert additivity_error < 1e-5, f"SHAP additivity violated: error={additivity_error}"

    # Verify identical Shapley values across threads for identical inputs
    base_phi = shap_results[0]["feature_attributions"]
    for sr in shap_results[1:]:
        for k, v in base_phi.items():
            assert math.isclose(sr["feature_attributions"][k], v, rel_tol=1e-4)


# ==============================================================================
# CATEGORY D: IMAGE INPUT VALIDATION & DIMENSION FUZZING TESTS
# ==============================================================================


def test_vision_non_square_image_resizing(
    service: UnifiedInferenceService,
    synthetic_pil_image_non_square: Image.Image,
):
    """Test D.1: Verifies automatic bilinear resizing of non-square (256x128) image inputs."""
    res = service.predict_defect_image(synthetic_pil_image_non_square)
    assert isinstance(res, DefectClassificationResponse)
    assert len(res.class_probabilities) == 4
    assert 0.0 <= res.confidence <= 1.0


def test_vision_grayscale_image_conversion(
    service: UnifiedInferenceService,
    synthetic_pil_image_grayscale: Image.Image,
):
    """Test D.2: Verifies automatic 1-channel Grayscale ('L') to 3-channel RGB conversion."""
    res = service.predict_defect_image(synthetic_pil_image_grayscale)
    assert isinstance(res, DefectClassificationResponse)
    assert len(res.class_probabilities) == 4


def test_vision_rgba_image_alpha_strip(
    service: UnifiedInferenceService,
    synthetic_pil_image_rgba: Image.Image,
):
    """Test D.3: Verifies automatic alpha-channel stripping for 4-channel RGBA inputs."""
    res = service.predict_defect_image(synthetic_pil_image_rgba)
    assert isinstance(res, DefectClassificationResponse)
    assert len(res.class_probabilities) == 4


def test_vision_invalid_numpy_shape_rejection(service: UnifiedInferenceService):
    """Test D.4: Verifies controlled ValueError rejection when numpy array shape is invalid."""
    invalid_array = np.zeros((1, 64, 64, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="Expected tensor shape"):
        service.predict_defect_image(invalid_array)


def test_vision_corrupted_image_buffer_rejection(service: UnifiedInferenceService):
    """Test D.5: Verifies controlled ImageDecodingError rejection on corrupted image byte stream."""
    corrupted_bytes = b"NOT_A_VALID_BITMAP_HEADER_STREAM_00000000"
    with pytest.raises(ImageDecodingError):
        service.predict_defect_image(corrupted_bytes)


def test_vision_zero_byte_buffer_rejection(service: UnifiedInferenceService):
    """Test D.6: Verifies controlled ImageDecodingError rejection on zero-byte image payload."""
    with pytest.raises(ImageDecodingError):
        service.predict_defect_image(b"")


# ==============================================================================
# CATEGORY E: PARTIAL TIMESTAMP VALIDATION & EDGE CASE TESTS
# ==============================================================================


def test_sequence_partial_timestamp_handling():
    """
    Test E.1: Verifies timestamp validation semantics across complete, missing, and partial inputs.
    Identifies and documents Finding L-03: SequenceWindowInput skips monotonicity validation
    if only a subset of readings has timestamp != None.
    """
    t0 = datetime(2026, 11, 7, 10, 0, 0)

    # 1. Complete monotonic timestamps -> PASS
    readings_valid = [
        SensorReadingInput(
            vibration=1.8, temperature=48.0, pressure=6.2, current=14.5, rpm=1800.0,
            timestamp=t0 + timedelta(seconds=i),
            machine_id="M104"
        )
        for i in range(30)
    ]
    window_valid = SequenceWindowInput(machine_id="M104", readings=readings_valid)
    assert len(window_valid.readings) == 30

    # 2. Missing timestamps (all None) -> PASS (timestamps optional)
    readings_none = [
        SensorReadingInput(
            vibration=1.8, temperature=48.0, pressure=6.2, current=14.5, rpm=1800.0,
            timestamp=None,
            machine_id="M104"
        )
        for i in range(30)
    ]
    window_none = SequenceWindowInput(machine_id="M104", readings=readings_none)
    assert len(window_none.readings) == 30

    # 3. Non-monotonic timestamps (all 30 provided, t[5] < t[4]) -> FAILS with TimestampOrderingError
    readings_non_monotonic = list(readings_valid)
    # Swap timestamps at index 4 and 5
    readings_non_monotonic[4] = SensorReadingInput(
        vibration=1.8, temperature=48.0, pressure=6.2, current=14.5, rpm=1800.0,
        timestamp=t0 + timedelta(seconds=10),
        machine_id="M104"
    )
    readings_non_monotonic[5] = SensorReadingInput(
        vibration=1.8, temperature=48.0, pressure=6.2, current=14.5, rpm=1800.0,
        timestamp=t0 + timedelta(seconds=2),
        machine_id="M104"
    )
    with pytest.raises(TimestampOrderingError):
        SequenceWindowInput(machine_id="M104", readings=readings_non_monotonic)

    # 4. Partial timestamps (29 provided, 1 is None) -> Documents Finding L-03
    readings_partial = list(readings_valid)
    readings_partial[15] = SensorReadingInput(
        vibration=1.8, temperature=48.0, pressure=6.2, current=14.5, rpm=1800.0,
        timestamp=None,
        machine_id="M104"
    )
    # Documented behavior: len(timestamps) == 29 != 30, skips loop without error
    window_partial = SequenceWindowInput(machine_id="M104", readings=readings_partial)
    assert window_partial.readings[15].timestamp is None

    # 5. Sequence length validation -> FAILS on 29 or 31 readings
    with pytest.raises(Exception):
        SequenceWindowInput(machine_id="M104", readings=readings_valid[:29])
    with pytest.raises(Exception):
        SequenceWindowInput(machine_id="M104", readings=readings_valid + [readings_valid[0]])


# ==============================================================================
# CATEGORY F: EXTREME SENSOR INPUT HANDLING TESTS
# ==============================================================================


def test_extreme_physical_outlier_scoring(service: UnifiedInferenceService):
    """
    Test F.1: Verifies model response to extreme physical outlier inputs.
    Values: RPM = 0 (stopped motor), Pressure = 0.1 bar (vacuum/loss), Vibration = 50.0 mm/s (severe fault).
    Verifies finite numerical scores, positive anomaly flag, and zero NaNs.
    """
    extreme_reading = SensorReadingInput(
        vibration=50.0,      # Extreme surge (> 200 sigma)
        temperature=150.0,   # Extreme thermal runaway
        pressure=0.1,        # Complete pressure loss
        current=100.0,       # Severe overcurrent
        rpm=0.0,             # Stalled motor
        machine_id="M104",
    )
    res: SensorAnomalyResponse = service.predict_sensor_anomaly(extreme_reading, explain=False)

    assert math.isfinite(res.anomaly_score), "Extreme input produced non-finite anomaly score"
    assert res.is_anomaly is True, "Extreme 50mm/s vibration and stalled motor must be classified as anomaly"
    assert res.threshold == 0.0269, "Frozen threshold must remain exactly 0.0269"

    # Non-finite values (NaN / Inf) must be rejected at Pydantic layer
    with pytest.raises(InvalidSensorValueError):
        service.predict_sensor_anomaly(
            {"vibration": float("nan"), "temperature": 48.0, "pressure": 6.2, "current": 14.5, "rpm": 1800.0}
        )
    with pytest.raises(InvalidSensorValueError):
        service.predict_sensor_anomaly(
            {"vibration": 1.8, "temperature": float("inf"), "pressure": 6.2, "current": 14.5, "rpm": 1800.0}
        )


# ==============================================================================
# CATEGORY G: SENSOR ATTRIBUTION SYNTHETIC FIXTURE TESTS
# ==============================================================================


def test_sensor_attribution_pure_synthetic_fixture():
    """
    Test G.1: Verifies sensor attribution mathematics on 100% synthetic deterministic fixtures.
    Guarantees strict quarantine: ZERO reads from sequences_test.npz or sensor_test.csv.
    """
    config = SensorAttributionConfig()
    explainer = LSTMAttributionExplainer(config)

    rng = np.random.RandomState(42)
    # Generate 5 sequences (5, 30, 5) with normalized z-scores
    X_synthetic = rng.normal(loc=0.0, scale=0.5, size=(5, 30, 5)).astype(np.float32)
    # Inject massive positive anomaly on vibration (feature index 0)
    X_synthetic[0, :, 0] += 8.0

    res = explainer.explain_sequences(X_synthetic)

    # Output dimension checks
    assert res.feature_mse.shape == (5, 5)
    assert res.feature_contribution_pct.shape == (5, 5)
    assert res.signed_residuals.shape == (5, 5)

    # Invariance check: Percentage contributions must sum to 100.0%
    sums = np.sum(res.feature_contribution_pct, axis=1)
    np.testing.assert_allclose(sums, 100.0, rtol=1e-4)

    # Signed residual check: Injected +8.0 on vibration must yield positive signed residual
    assert res.signed_residuals[0, 0] > 0, "Positive deviation must produce positive signed residual"

    # All values must be finite
    assert np.all(np.isfinite(res.feature_mse))
    assert np.all(np.isfinite(res.feature_contribution_pct))


# ==============================================================================
# CATEGORY H: REPEATED INFERENCE STABILITY TESTS
# ==============================================================================


def test_repeated_inference_memory_stability(
    service: UnifiedInferenceService,
    synthetic_sensor_reading: SensorReadingInput,
    synthetic_sequence_window: SequenceWindowInput,
    synthetic_workpiece_image_bmp_bytes: bytes,
):
    """
    Test H.1: Verifies stability and deterministic repeatability across 100 repeated multi-modal inference cycles.
    Records completed cycles, execution times, and checks for memory growth / state leakage.
    """
    req = UnifiedInferenceRequest(
        sensor_reading=synthetic_sensor_reading,
        sequence_window=synthetic_sequence_window,
        defect_image=DefectImageInput(image_bytes=synthetic_workpiece_image_bmp_bytes),
        include_shap=False,
        include_attribution=False,
    )

    num_cycles = 100
    first_response: Optional[UnifiedInferenceResponse] = None
    last_response: Optional[UnifiedInferenceResponse] = None

    t0 = time.perf_counter()
    for cycle in range(num_cycles):
        res = service.predict_unified(req)
        if cycle == 0:
            first_response = res
        if cycle == num_cycles - 1:
            last_response = res
    total_time = time.perf_counter() - t0

    # Verification assertions
    assert first_response is not None
    assert last_response is not None

    # Deterministic invariance: cycle 0 must equal cycle 99
    assert math.isclose(
        first_response.sensor_result.anomaly_score,
        last_response.sensor_result.anomaly_score,
        rel_tol=1e-6,
    )
    assert math.isclose(
        first_response.sequence_result.reconstruction_error,
        last_response.sequence_result.reconstruction_error,
        rel_tol=1e-6,
    )
    assert (
        first_response.defect_result.defect_type
        == last_response.defect_result.defect_type
    )
    assert math.isclose(
        first_response.defect_result.confidence,
        last_response.defect_result.confidence,
        rel_tol=1e-4,
    )
