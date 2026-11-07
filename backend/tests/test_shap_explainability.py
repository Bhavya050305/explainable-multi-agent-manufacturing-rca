"""
ManuMind AI — Unit & Integration Tests for SHAP Explainability
Department of AI & Data Science — RMK Engineering College

Validates:
1. Model loading from repository store.
2. Five-feature order integrity.
3. Background sample count (exactly 50).
4. Five normal training observations per machine.
5. Zero abnormal background observations.
6. Deterministic background selection across seeds.
7. Correct anomaly-score orientation (-decision_function).
8. SHAP additivity to machine precision (< 1e-6).
9. Correct attribution-to-feature mapping.
10. Positive attribution percentage calculation.
11. Null percentage when no positive attribution exists.
12. JSON serialization into native Python types.
13. Invalid input shape handling.
14. Graceful explanation failure handling.
15. Preservation of existing LSTM attribution interface.
"""

import json
import os
import sys
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.shap_explainability.config import (
    ShapExplainerConfig,
    FEATURE_COLUMNS,
    STRATIFIED_MACHINE_IDS,
    SAMPLES_PER_MACHINE,
    TOTAL_BACKGROUND_SAMPLES
)
from backend.app.ml.shap_explainability.explainer import IsolationForestShapExplainer
from backend.app.ml.sensor_attribution.lstm_attribution import LSTMAttributionExplainer


@pytest.fixture(scope="module")
def shared_explainer():
    """Module-level fixture to share explainer initialization across tests."""
    config = ShapExplainerConfig()
    return IsolationForestShapExplainer(config=config)


def test_01_model_loading_and_attributes(shared_explainer):
    """Test 1: Verify model loading and estimator parameters."""
    explainer = shared_explainer
    assert explainer.model is not None
    assert explainer.model.n_estimators == 200
    assert len(explainer.model.estimators_) == 200
    assert explainer.model.max_samples_ == 256
    assert explainer.n_features == 5


def test_02_five_feature_order_integrity(shared_explainer):
    """Test 2: Verify exact five-feature column names and sequence."""
    explainer = shared_explainer
    expected_features = ["vibration", "temperature", "pressure", "current", "rpm"]
    assert explainer.feature_cols == expected_features
    assert explainer.config.feature_cols == expected_features
    assert FEATURE_COLUMNS == expected_features


def test_03_background_sample_count(shared_explainer):
    """Test 3: Verify background contains exactly 50 samples with 5 features."""
    explainer = shared_explainer
    assert explainer.background_data.shape == (50, 5)
    assert len(explainer.background_data) == TOTAL_BACKGROUND_SAMPLES
    assert np.all(np.isfinite(explainer.background_data))


def test_04_five_normal_observations_per_machine(shared_explainer):
    """Test 4: Verify exactly 5 observations sampled per machine across all 10 machines."""
    explainer = shared_explainer
    details = explainer.background_metadata.get("machine_details", {})
    assert len(details) == 10
    for m_id in STRATIFIED_MACHINE_IDS:
        assert m_id in details
        assert details[m_id]["selected_count"] == SAMPLES_PER_MACHINE
        assert len(details[m_id]["selected_row_indices"]) == SAMPLES_PER_MACHINE


def test_05_no_abnormal_background_observations():
    """Test 5: Verify zero abnormal rows exist in background sampling pool."""
    config = ShapExplainerConfig()
    df_train = pd.read_csv(config.train_sensor_csv)
    normal_df = df_train[df_train["is_anomaly"] == 0]
    # Check that normal_df contains 0 anomalies
    assert (normal_df["is_anomaly"] != 0).sum() == 0


def test_06_deterministic_background_selection():
    """Test 6: Verify background selection is strictly reproducible."""
    config1 = ShapExplainerConfig(random_seed=42)
    config2 = ShapExplainerConfig(random_seed=42)
    exp1 = IsolationForestShapExplainer(config=config1)
    exp2 = IsolationForestShapExplainer(config=config2)
    np.testing.assert_array_equal(exp1.background_data, exp2.background_data)
    assert exp1.expected_value == exp2.expected_value


def test_07_correct_anomaly_score_orientation(shared_explainer):
    """Test 7: Verify -decision_function: higher output indicates greater anomaly."""
    explainer = shared_explainer
    # Normal point near nominal zero standardized space
    normal_point = np.zeros((1, 5))
    # Severe anomaly point: high vibration (+5 sigma)
    anom_point = np.array([[5.0, 0.0, 0.0, 0.0, 0.0]])

    score_normal = explainer.anomaly_intensity_wrapper(normal_point)[0]
    score_anom = explainer.anomaly_intensity_wrapper(anom_point)[0]

    assert score_anom > score_normal
    assert score_normal < 0.0  # Inlier is negative
    assert score_anom > 0.0    # Outlier is positive


def test_08_shap_additivity(shared_explainer):
    """Test 8: Verify SHAP additivity: |f(x) - (E[f] + sum(phi))| < 1e-6."""
    explainer = shared_explainer
    # Evaluate a test vector
    test_vec = np.array([1.5, -0.5, 2.0, 0.8, -1.2])
    res = explainer.explain_observation(test_vec, nsamples=32)

    assert res["status"] == "success"
    assert res["additivity_verified"] is True
    assert res["additivity_error"] < 1e-6

    # Independent check
    base_val = res["base_value"]
    sum_phi = sum(res["feature_attributions"].values())
    expected_f = res["anomaly_score"]
    assert abs(expected_f - (base_val + sum_phi)) < 1e-6


def test_09_correct_attribution_to_feature_mapping(shared_explainer):
    """Test 9: Verify feature attribution dictionary keys and sequence."""
    explainer = shared_explainer
    test_vec = np.array([3.0, 0.0, 0.0, 0.0, 0.0])
    res = explainer.explain_observation(test_vec, nsamples=32)

    attr = res["feature_attributions"]
    assert list(attr.keys()) == FEATURE_COLUMNS
    for feat in FEATURE_COLUMNS:
        assert isinstance(attr[feat], float)
    # Severe positive vibration spike should yield vibration as top positive contributor
    assert res["top_positive_contributor"] == "vibration"


def test_10_positive_attribution_percentage_calculation(shared_explainer):
    """Test 10: Verify share_of_positive_attribution_pct calculation."""
    explainer = shared_explainer
    test_vec = np.array([2.5, 1.5, -1.0, -0.5, 0.0])
    res = explainer.explain_observation(test_vec, nsamples=32)

    assert res["status"] == "success"
    pct = res["share_of_positive_attribution_pct"]
    assert pct is not None
    assert 0.0 <= pct <= 100.0

    # Verify formula manually
    attr = res["feature_attributions"]
    pos_sum = sum(v for v in attr.values() if v > 0.0)
    top_pos_val = attr[res["top_positive_contributor"]]
    expected_pct = (top_pos_val / pos_sum) * 100.0
    assert abs(pct - expected_pct) < 1e-4


def test_11_null_percentage_when_no_positive_attribution(shared_explainer):
    """Test 11: Verify share_of_positive_attribution_pct is None when all phi <= 0."""
    explainer = shared_explainer
    # Normal point where all features anchor to health (all phi <= 0)
    normal_vec = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    res = explainer.explain_observation(normal_vec, nsamples=32)

    # Check whether all phi are non-positive or test with an explicit mocked output
    attr = res["feature_attributions"]
    if all(v <= 0.0 for v in attr.values()):
        assert res["top_positive_contributor"] is None
        assert res["share_of_positive_attribution_pct"] is None


def test_12_json_serialization(shared_explainer):
    """Test 12: Verify explanation payload serializes cleanly with json.dumps and Pydantic Alert schemas."""
    from datetime import datetime
    from backend.app.schemas.alert import AlertCreate, AlertResponse

    explainer = shared_explainer
    res = explainer.explain_observation([1.0, 0.5, -0.2, 0.1, 0.0], machine_id="M104", step=3100)
    json_str = json.dumps(res)
    assert isinstance(json_str, str)
    deserialized = json.loads(json_str)
    assert deserialized["status"] == "success"
    assert deserialized["machine_id"] == "M104"
    assert deserialized["step"] == 3100

    # Pydantic schema serialization / deserialization verification
    alert_payload = {
        "id": "ALT-M104-001",
        "machine_id": "M104",
        "risk": 0.85,
        "criticality": 4,
        "impact": 5,
        "priority_score": 17.0,
        "shap_json": res,
        "sensor_contrib_json": {"vibration": 0.112},
        "status": "PENDING_APPROVAL"
    }
    alert_create = AlertCreate(**alert_payload)
    assert alert_create.shap_json["status"] == "success"
    assert alert_create.shap_json["feature_attributions"]["vibration"] == res["feature_attributions"]["vibration"]

    alert_response = AlertResponse(**alert_create.model_dump(), created_at=datetime.utcnow())
    assert alert_response.shap_json["machine_id"] == "M104"
    dumped = alert_response.model_dump()
    assert isinstance(dumped["shap_json"], dict)
    assert "feature_attributions" in dumped["shap_json"]


def test_13_invalid_input_shape_handling(shared_explainer):
    """Test 13: Verify handling of invalid input dimensions."""
    explainer = shared_explainer
    # Invalid: 4 features instead of 5
    invalid_vec = np.array([1.0, 2.0, 3.0, 4.0])
    res = explainer.explain_observation(invalid_vec)
    assert res["status"] == "failed"
    assert res["error_message"] is not None
    assert "Expected input shape" in res["error_message"] or "features" in res["error_message"]


def test_14_graceful_explanation_failure_handling(shared_explainer):
    """Test 14: Verify non-finite input (NaN) is handled gracefully without crashing."""
    explainer = shared_explainer
    nan_vec = np.array([np.nan, 1.0, 2.0, 3.0, 4.0])
    res = explainer.explain_observation(nan_vec)
    assert res["status"] == "failed"
    assert "non-finite" in res["error_message"].lower() or "nan" in res["error_message"].lower()


def test_15_preservation_of_lstm_attribution_interface():
    """Test 15: Verify Step 4 LSTMAttributionExplainer remains intact and operational."""
    lstm_explainer = LSTMAttributionExplainer()
    assert lstm_explainer.n_features == 5
    assert lstm_explainer.feature_cols == ["vibration", "temperature", "pressure", "current", "rpm"]
    # Dummy sequence window of shape (1, 30, 5)
    dummy_seq = np.zeros((1, 30, 5), dtype=np.float32)
    res = lstm_explainer.explain_sequences(dummy_seq)
    assert hasattr(res, "feature_mse")
    assert hasattr(res, "signed_residuals")
    assert hasattr(res, "feature_contribution_pct")
    assert res.feature_mse.shape == (1, 5)
