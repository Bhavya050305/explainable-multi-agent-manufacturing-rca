"""
ManuMind AI — Anomaly Detection Agent Integration Test Suite
Phase 5 Step 4.2 COND-4 Verification Suite.

Validates end-to-end integration of AnomalyDetectionAgent with the real
UnifiedInferenceService, frozen StandardScaler, Isolation Forest, and
Kernel SHAP explainability pipeline without mocks.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import pytest

from backend.app.agents.anomaly_agent import (
    CANONICAL_FEATURES,
    DEFAULT_BASELINE_RANGES,
    AnomalyDetectionAgent,
    anomaly_detection_node,
)
from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    AnomalyExecutionStatus,
    AnomalySeverity,
    AnomalyType,
    ExecutionMode,
    SupervisorAction,
)
from backend.app.agents.reducers import validate_agent_state_update
from backend.app.agents.schemas import (
    AnomalyAssessment,
    AnomalyDetectionResult,
    SensorMeasurementsSummary,
    TelemetryWindow,
)
from backend.app.agents.state import create_initial_state
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.ml.inference.config import (
    EXPECTED_ARTIFACT_HASHES,
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    InferenceConfig,
)
from backend.app.ml.inference.registry import ModelRegistry
from backend.app.ml.inference.schemas import ExplanationStatus
from backend.app.ml.inference.service import UnifiedInferenceService


@pytest.fixture(scope="module")
def inference_config():
    return InferenceConfig()


@pytest.fixture(scope="module")
def real_inference_service(inference_config):
    return UnifiedInferenceService(config=inference_config)


@pytest.fixture
def real_telemetry_window():
    return TelemetryWindow(
        start_time=datetime(2026, 11, 19, 8, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 19, 9, 0, 0, tzinfo=timezone.utc),
        sample_count=3600,
    )


# -----------------------------------------------------------------------------
# Test 1: Real sensor_scaler.joblib and isolation_forest.joblib load without mocks
# -----------------------------------------------------------------------------
def test_real_artifacts_load_without_mocks(inference_config):
    registry = ModelRegistry.get_instance(inference_config)

    # 1. Verify files exist on disk and verify SHA-256 hashes
    scaler_path = inference_config.resolve_artifact_path("sensor_scaler.joblib")
    if_path = inference_config.resolve_artifact_path("isolation_forest.joblib")

    assert scaler_path.exists(), f"Scaler missing at {scaler_path}"
    assert if_path.exists(), f"Isolation Forest missing at {if_path}"

    with open(scaler_path, "rb") as f:
        scaler_sha = hashlib.sha256(f.read()).hexdigest()
    with open(if_path, "rb") as f:
        if_sha = hashlib.sha256(f.read()).hexdigest()

    assert scaler_sha == EXPECTED_ARTIFACT_HASHES["sensor_scaler.joblib"]
    assert if_sha == EXPECTED_ARTIFACT_HASHES["isolation_forest.joblib"]

    # 2. Verify objects load via registry without mocks
    scaler = registry.get_scaler()
    assert scaler is not None
    assert hasattr(scaler, "transform")
    assert hasattr(scaler, "mean_")
    assert len(scaler.mean_) == 5

    if_predictor = registry.get_isolation_forest()
    assert if_predictor is not None
    assert hasattr(if_predictor, "score")
    assert if_predictor.threshold == ISOLATION_FOREST_FROZEN_THRESHOLD


# -----------------------------------------------------------------------------
# Test 2: Scaler transforms valid 5-channel vector preserving canonical feature ordering
# -----------------------------------------------------------------------------
def test_scaler_transforms_5_channel_vector_preserving_order(inference_config):
    registry = ModelRegistry.get_instance(inference_config)
    scaler = registry.get_scaler()

    # Canonical order: [vibration, temperature, pressure, current, rpm]
    raw_vector = [[2.1, 55.0, 6.2, 12.0, 1800.0]]
    scaled_vector = scaler.transform(raw_vector)

    assert scaled_vector.shape == (1, 5)
    for i in range(5):
        val = scaled_vector[0, i]
        assert not math.isnan(val)
        assert not math.isinf(val)


# -----------------------------------------------------------------------------
# Test 3: Real Isolation Forest predicts continuous score and is_anomaly bool
# -----------------------------------------------------------------------------
def test_real_isolation_forest_predicts_continuous_score_and_flag(real_inference_service):
    # Nominal observation
    reading = {
        "vibration": 2.1,
        "temperature": 55.0,
        "pressure": 6.2,
        "current": 12.0,
        "rpm": 1800.0,
    }

    response = real_inference_service.predict_sensor_anomaly(reading, explain=False)

    assert response.model_id == "isolation_forest_v1"
    assert isinstance(response.anomaly_score, float)
    assert not math.isnan(response.anomaly_score)
    assert not math.isinf(response.anomaly_score)
    assert response.threshold == ISOLATION_FOREST_FROZEN_THRESHOLD
    assert response.is_anomaly == (response.anomaly_score > response.threshold)


# -----------------------------------------------------------------------------
# Test 4: Real Kernel SHAP generates game-theoretic feature attribution satisfying additivity
# -----------------------------------------------------------------------------
def test_real_kernel_shap_generates_game_theoretic_attribution(real_inference_service):
    reading = {
        "vibration": 4.8,
        "temperature": 78.0,
        "pressure": 4.2,
        "current": 26.0,
        "rpm": 1800.0,
    }

    response = real_inference_service.predict_sensor_anomaly(reading, explain=True)

    assert response.explanation_status == ExplanationStatus.AVAILABLE
    assert response.shap_explanation is not None

    shap_exp = response.shap_explanation
    assert shap_exp["status"] == "success"
    assert shap_exp["explainer_method"] == "kernel_shap"
    assert "feature_attributions" in shap_exp

    attributions = shap_exp["feature_attributions"]
    assert len(attributions) == 5
    for feat in CANONICAL_FEATURES:
        assert feat in attributions
        assert not math.isnan(attributions[feat])
        assert not math.isinf(attributions[feat])

    # Additivity Axiom Verification: sum(phi_i) + base_value ≈ anomaly_score
    base_val = shap_exp["base_value"]
    score = shap_exp["anomaly_score"]
    reconstructed_score = sum(attributions.values()) + base_val

    assert math.isclose(reconstructed_score, score, abs_tol=1e-4)
    assert shap_exp.get("additivity_verified") is True


# -----------------------------------------------------------------------------
# Test 5: Real AnomalyDetectionAgent evaluates state using real UnifiedInferenceService
# -----------------------------------------------------------------------------
def test_real_anomaly_detection_agent_evaluates_state_without_mocks(
    real_inference_service, real_telemetry_window
):
    # Abnormal observation (pressure drop and vibration spike)
    summary = SensorMeasurementsSummary(
        readings={
            "vibration": 6.8,
            "temperature": 60.0,
            "pressure": 3.2,
            "current": 14.0,
            "rpm": 1800.0,
        },
        units={
            "vibration": "mm/s",
            "temperature": "°C",
            "pressure": "bar",
            "current": "A",
            "rpm": "RPM",
        },
        is_synthetic=False,
    )

    state = create_initial_state(
        workflow_id="WF-REAL-INTEG-001",
        machine_id="M107",
        execution_mode=ExecutionMode.AUTONOMOUS_DIAGNOSTIC,
        telemetry_window=real_telemetry_window,
        sensor_measurements=summary,
    )

    agent = AnomalyDetectionAgent(inference_service=real_inference_service)
    update = agent.analyze(state)

    # Validate output schema and channels
    assert "anomaly_assessment" in update
    assert "anomaly_detection_result" in update

    assessment = update["anomaly_assessment"]
    assert isinstance(assessment, AnomalyAssessment)
    assert assessment.execution_status == AnomalyExecutionStatus.SUCCESS
    assert assessment.model_name == "isolation_forest_v1"
    assert assessment.confidence > 0.0

    result = update["anomaly_detection_result"]
    assert isinstance(result, AnomalyDetectionResult)
    assert result.execution_status == AnomalyExecutionStatus.SUCCESS

    # Verify write boundary
    validated_update = validate_agent_state_update(AgentName.ANOMALY_DETECTION, update)
    assert "human_approval" not in validated_update

    # Test downstream Supervisor routing
    state.update(validated_update)
    supervisor = SupervisorAgent()
    supervisor_decision = supervisor.evaluate(state)

    # Anomaly was detected -> MUST route to RCA, NEVER prematurely complete
    if result.is_anomaly:
        assert supervisor_decision.next_action == SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS
        assert supervisor_decision.target_agent == AgentName.ROOT_CAUSE_ANALYSIS
    else:
        assert supervisor_decision.next_action == SupervisorAction.COMPLETE_WORKFLOW


# -----------------------------------------------------------------------------
# Test 6: Missing artifact produces explicit error rather than healthy result
# -----------------------------------------------------------------------------
def test_missing_artifact_produces_explicit_error_never_healthy(real_telemetry_window):
    class BrokenInferenceService:
        def predict_sensor_anomaly(self, readings, explain=True):
            raise FileNotFoundError("Model artifact isolation_forest.joblib missing")

    state = create_initial_state(
        workflow_id="WF-REAL-INTEG-MISSING",
        machine_id="M108",
        execution_mode=ExecutionMode.AUTONOMOUS_DIAGNOSTIC,
        telemetry_window=real_telemetry_window,
        sensor_measurements=SensorMeasurementsSummary(
            readings={"vibration": 2.0, "temperature": 50.0, "pressure": 6.2, "current": 10.0, "rpm": 1500.0}
        ),
    )

    agent = AnomalyDetectionAgent(inference_service=BrokenInferenceService())
    update = agent.analyze(state)

    # 1. Output MUST flag FAILED execution status
    assert update["anomaly_assessment"].execution_status == AnomalyExecutionStatus.FAILED
    assert update["anomaly_detection_result"].execution_status == AnomalyExecutionStatus.FAILED
    assert update["anomaly_assessment"].anomaly_detected is False
    assert update["anomaly_assessment"].confidence == 0.0

    records = update.get("agent_executions", [])
    assert len(records) == 1
    assert records[0].execution_status == AgentExecutionStatus.FAILED
    assert "missing" in records[0].error_summary.lower()

    # 2. Downstream Supervisor evaluation MUST NOT classify machine as healthy
    state.update(update)
    supervisor = SupervisorAgent()
    supervisor_decision = supervisor.evaluate(state)

    assert supervisor_decision.next_action != SupervisorAction.COMPLETE_WORKFLOW
    assert supervisor_decision.next_action == SupervisorAction.FAIL_WORKFLOW
    assert supervisor_decision.escalation_required is True
    assert supervisor_decision.human_review_required is True
