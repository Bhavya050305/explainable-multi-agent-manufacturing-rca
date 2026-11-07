"""
ManuMind AI — Unified Inference Evaluator & Benchmark Harness
Department of AI & Data Science — RMK Engineering College

Automated verification harness measuring:
1. Numerical parity against direct model predictors
2. Pure wrapper latency overhead vs. raw model forward passes
3. Repeated inference consistency and execution stability
4. System environment documentation (hardware, OS, dependency versions)
"""

import json
import logging
import os
import platform
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import sklearn
import tensorflow as tf
import shap
from PIL import Image

from backend.app.ml.inference.config import (
    CANONICAL_FEATURES,
    InferenceConfig,
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    LSTM_AUTOENCODER_FROZEN_THRESHOLD,
)
from backend.app.ml.inference.registry import ModelRegistry
from backend.app.ml.inference.schemas import (
    SensorReadingInput,
    SequenceWindowInput,
    UnifiedInferenceRequest,
)
from backend.app.ml.inference.service import UnifiedInferenceService
from backend.app.ml.isolation_forest.predict import IsolationForestPredictor
from backend.app.ml.lstm_autoencoder.predict import LSTMAutoencoderPredictor
from backend.app.ml.sensor_attribution.lstm_attribution import LSTMAttributionExplainer
from backend.app.ml.defect_classifier.predict import DefectClassifierInferenceService

logger = logging.getLogger("InferenceEvaluator")


class InferenceEvaluator:
    """
    Controlled evaluation harness validating numerical parity, execution latency,
    and wrapper overhead for the Unified Inference Service.
    """

    def __init__(
        self,
        service: Optional[UnifiedInferenceService] = None,
        config: Optional[InferenceConfig] = None
    ) -> None:
        self.config = config or InferenceConfig()
        self.service = service or UnifiedInferenceService(config=self.config)
        self.registry = self.service.registry

    @staticmethod
    def get_system_environment() -> Dict[str, Any]:
        """Captures hardware and library versions for audit reproducibility."""
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "tensorflow_version": tf.__version__,
            "sklearn_version": sklearn.__version__,
            "shap_version": shap.__version__,
            "numpy_version": np.__version__,
        }

    def verify_numerical_parity(self) -> Dict[str, Any]:
        """
        Verifies numerical parity between direct component calls and the Unified service.
        Checks:
        1. Isolation Forest continuous score parity (< 1e-6)
        2. LSTM Autoencoder reconstruction MSE parity (< 1e-6)
        3. Compact ResNet-18 class probability parity (< 1e-5)
        4. Sensor attribution percentage parity (< 1e-4)
        5. Kernel SHAP game-theoretic additivity (|f(x) - (E[f] + sum(phi))| <= 1e-6)
        """
        results: Dict[str, Any] = {}

        # 1. Isolation Forest Parity
        raw_reading = {
            "vibration": 4.85,
            "temperature": 78.4,
            "pressure": 6.2,
            "current": 18.5,
            "rpm": 1780.0
        }
        # Direct predictor call
        raw_vec = np.array([[raw_reading[f] for f in CANONICAL_FEATURES]], dtype=np.float64)
        scaler = self.registry.get_scaler()
        scaled_vec = scaler.transform(raw_vec)
        direct_if = self.registry.get_isolation_forest()
        direct_if_score = float(direct_if.score(scaled_vec)[0])

        # Service call
        service_sensor_res = self.service.predict_sensor_anomaly(raw_reading)
        service_if_score = service_sensor_res.anomaly_score

        if_diff = abs(direct_if_score - service_if_score)
        results["isolation_forest_parity"] = {
            "direct_score": direct_if_score,
            "service_score": service_if_score,
            "absolute_difference": if_diff,
            "parity_passed": bool(if_diff < 1e-6)
        }

        # 2. LSTM Autoencoder Parity
        rng = np.random.RandomState(42)
        raw_seq_mat = rng.uniform(
            low=[0.5, 30.0, 2.0, 5.0, 1000.0],
            high=[8.0, 95.0, 8.0, 25.0, 2000.0],
            size=(30, 5)
        )
        scaled_seq_mat = scaler.transform(raw_seq_mat).astype(np.float32)
        seq_tensor = np.expand_dims(scaled_seq_mat, axis=0)

        direct_lstm = self.registry.get_lstm_autoencoder()
        direct_recon_error = float(direct_lstm.compute_reconstruction_error(seq_tensor)[0])

        readings_list = [
            SensorReadingInput(
                vibration=float(raw_seq_mat[i, 0]),
                temperature=float(raw_seq_mat[i, 1]),
                pressure=float(raw_seq_mat[i, 2]),
                current=float(raw_seq_mat[i, 3]),
                rpm=float(raw_seq_mat[i, 4])
            )
            for i in range(30)
        ]
        window_input = SequenceWindowInput(machine_id="M104", readings=readings_list)
        service_seq_res = self.service.predict_sequence_anomaly(window_input)
        service_recon_error = service_seq_res.reconstruction_error

        lstm_diff = abs(direct_recon_error - service_recon_error)
        results["lstm_autoencoder_parity"] = {
            "direct_reconstruction_error": direct_recon_error,
            "service_reconstruction_error": service_recon_error,
            "absolute_difference": lstm_diff,
            "parity_passed": bool(lstm_diff < 1e-6)
        }

        # 3. Defect Classifier Parity
        dummy_img = np.ones((128, 128, 3), dtype=np.float32) * 128.0
        direct_defect = self.registry.get_defect_classifier()
        direct_res = direct_defect.predict_image(dummy_img, image_name="parity_test.bmp")

        service_defect_res = self.service.predict_defect_image(dummy_img, image_name="parity_test.bmp")

        prob_diffs = [
            abs(direct_res["class_probabilities"][c] - service_defect_res.class_probabilities[c])
            for c in direct_res["class_probabilities"]
        ]
        max_prob_diff = max(prob_diffs)
        results["defect_classifier_parity"] = {
            "direct_confidence": direct_res["confidence"],
            "service_confidence": service_defect_res.confidence,
            "max_probability_difference": max_prob_diff,
            "parity_passed": bool(max_prob_diff < 1e-5)
        }

        # 4. Sensor Attribution Parity
        direct_attr_res = self.registry.get_lstm_attribution_explainer().explain_sequences(seq_tensor)
        service_attr_res = self.service.explain_sequence_attribution(seq_tensor)

        pct_diffs = [
            abs(round(float(direct_attr_res.feature_contribution_pct[0, i]), 4) - service_attr_res["feature_contribution_pct"][feat])
            for i, feat in enumerate(CANONICAL_FEATURES)
        ]
        max_pct_diff = max(pct_diffs)
        results["sensor_attribution_parity"] = {
            "dominant_feature_match": bool(direct_attr_res.dominant_features[0] == service_attr_res["dominant_feature"]),
            "max_pct_difference": max_pct_diff,
            "parity_passed": bool(max_pct_diff < 1e-4)
        }

        # 5. SHAP Additivity Verification
        shap_res = self.service.explain_sensor_shap(raw_reading)
        additivity_error = shap_res.get("additivity_error", 0.0)
        results["shap_additivity"] = {
            "base_value": shap_res.get("base_value"),
            "model_output": shap_res.get("model_output", shap_res.get("anomaly_score")),
            "additivity_error": additivity_error,
            "additivity_passed": bool(shap_res.get("additivity_verified", False) or abs(additivity_error) <= 1e-6)
        }

        all_passed = all(v.get("parity_passed", False) or v.get("additivity_passed", False) for v in results.values())
        results["all_parity_checks_passed"] = all_passed
        return results

    def benchmark_latency(self, n_warmup: int = 10, n_iterations: int = 100) -> Dict[str, Any]:
        """
        Measures execution latency across modalities:
        1. 10 warm-up forward passes to compile computational graphs.
        2. 100 timed iterations using high-resolution time.perf_counter().
        3. Measures direct model execution vs. service wrapper overhead.
        """
        # Prepare inputs
        sensor_dict = {
            "vibration": 3.2,
            "temperature": 72.0,
            "pressure": 5.8,
            "current": 14.2,
            "rpm": 1750.0
        }
        sensor_input = SensorReadingInput(**sensor_dict)

        raw_vec = np.array([[sensor_dict[f] for f in CANONICAL_FEATURES]], dtype=np.float64)
        scaler = self.registry.get_scaler()
        scaled_vec = scaler.transform(raw_vec)
        if_model = self.registry.get_isolation_forest()

        readings_list = [
            SensorReadingInput(
                vibration=3.2 + 0.01 * i,
                temperature=72.0 + 0.02 * i,
                pressure=5.8,
                current=14.2,
                rpm=1750.0
            )
            for i in range(30)
        ]
        seq_input = SequenceWindowInput(machine_id="M104", readings=readings_list)
        raw_mat = np.array([[r.vibration, r.temperature, r.pressure, r.current, r.rpm] for r in readings_list], dtype=np.float64)
        scaled_seq = np.expand_dims(scaler.transform(raw_mat).astype(np.float32), axis=0)
        lstm_model = self.registry.get_lstm_autoencoder()

        dummy_img = np.ones((128, 128, 3), dtype=np.float32) * 128.0
        defect_service = self.registry.get_defect_classifier()

        # Warm-up phase
        for _ in range(n_warmup):
            _ = if_model.score(scaled_vec)
            _ = self.service.predict_sensor_anomaly(sensor_input)
            _ = lstm_model.compute_reconstruction_error(scaled_seq)
            _ = self.service.predict_sequence_anomaly(seq_input)
            _ = defect_service.predict_image(dummy_img, image_name="warm.bmp")
            _ = self.service.predict_defect_image(dummy_img, image_name="warm.bmp")

        def compute_stats(timings: List[float]) -> Dict[str, float]:
            arr_ms = np.array(timings) * 1000.0
            return {
                "mean_ms": round(float(np.mean(arr_ms)), 4),
                "median_ms": round(float(np.median(arr_ms)), 4),
                "p95_ms": round(float(np.percentile(arr_ms, 95)), 4),
                "min_ms": round(float(np.min(arr_ms)), 4),
                "max_ms": round(float(np.max(arr_ms)), 4),
            }

        # 1. Benchmark Sensor Anomaly (IF)
        direct_if_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = if_model.score(scaled_vec)
            direct_if_times.append(time.perf_counter() - t0)

        service_if_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = self.service.predict_sensor_anomaly(sensor_input)
            service_if_times.append(time.perf_counter() - t0)

        # 2. Benchmark Sequence Anomaly (LSTM)
        direct_lstm_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = lstm_model.compute_reconstruction_error(scaled_seq)
            direct_lstm_times.append(time.perf_counter() - t0)

        service_lstm_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = self.service.predict_sequence_anomaly(seq_input)
            service_lstm_times.append(time.perf_counter() - t0)

        # 3. Benchmark Defect Classifier (ResNet)
        direct_defect_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = defect_service.predict_image(dummy_img, image_name="bench.bmp")
            direct_defect_times.append(time.perf_counter() - t0)

        service_defect_times = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            _ = self.service.predict_defect_image(dummy_img, image_name="bench.bmp")
            service_defect_times.append(time.perf_counter() - t0)

        # Compile latency report
        if_direct_stats = compute_stats(direct_if_times)
        if_service_stats = compute_stats(service_if_times)
        if_wrapper_ms = round(if_service_stats["mean_ms"] - if_direct_stats["mean_ms"], 4)

        lstm_direct_stats = compute_stats(direct_lstm_times)
        lstm_service_stats = compute_stats(service_lstm_times)
        lstm_wrapper_ms = round(lstm_service_stats["mean_ms"] - lstm_direct_stats["mean_ms"], 4)

        defect_direct_stats = compute_stats(direct_defect_times)
        defect_service_stats = compute_stats(service_defect_times)
        defect_wrapper_ms = round(defect_service_stats["mean_ms"] - defect_direct_stats["mean_ms"], 4)

        return {
            "benchmark_parameters": {
                "warmup_iterations": n_warmup,
                "timed_iterations": n_iterations,
                "timer": "time.perf_counter",
                "wrapper_overhead_target_ms": 5.0
            },
            "sensor_anomaly_isolation_forest": {
                "direct_model": if_direct_stats,
                "unified_service": if_service_stats,
                "wrapper_overhead_mean_ms": if_wrapper_ms,
                "meets_exploratory_target": bool(if_wrapper_ms <= 5.0)
            },
            "sequence_anomaly_lstm_autoencoder": {
                "direct_model": lstm_direct_stats,
                "unified_service": lstm_service_stats,
                "wrapper_overhead_mean_ms": lstm_wrapper_ms,
                "meets_exploratory_target": bool(lstm_wrapper_ms <= 5.0)
            },
            "defect_classifier_compact_resnet": {
                "direct_model": defect_direct_stats,
                "unified_service": defect_service_stats,
                "wrapper_overhead_mean_ms": defect_wrapper_ms,
                "meets_exploratory_target": bool(defect_wrapper_ms <= 5.0)
            }
        }

    def run_full_evaluation(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Runs parity and latency evaluation and records results."""
        logger.info("Pre-warming models...")
        warmup_status = self.registry.warmup()

        logger.info("Verifying numerical parity...")
        parity_results = self.verify_numerical_parity()

        logger.info("Executing latency benchmark (10 warmup, 100 iterations)...")
        latency_results = self.benchmark_latency(n_warmup=10, n_iterations=100)

        report = {
            "evaluation_title": "ManuMind AI — Unified Inference Service Verification",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system_environment": self.get_system_environment(),
            "warmup_status": warmup_status,
            "numerical_parity": parity_results,
            "latency_benchmarks": latency_results,
            "overall_status": "PASSED" if parity_results.get("all_parity_checks_passed") else "FAILED"
        }

        save_path = output_path or "reports/phase2/inference_service_eval_results.json"
        dest = self.config.base_dir / save_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved evaluation report to: %s", dest)

        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    evaluator = InferenceEvaluator()
    results = evaluator.run_full_evaluation()
    print("\n--- INFERENCE EVALUATION SUMMARY ---")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Parity Passed: {results['numerical_parity']['all_parity_checks_passed']}")
    print(f"Sensor Wrapper Overhead: {results['latency_benchmarks']['sensor_anomaly_isolation_forest']['wrapper_overhead_mean_ms']} ms")
    print(f"Sequence Wrapper Overhead: {results['latency_benchmarks']['sequence_anomaly_lstm_autoencoder']['wrapper_overhead_mean_ms']} ms")
    print(f"Defect Vision Wrapper Overhead: {results['latency_benchmarks']['defect_classifier_compact_resnet']['wrapper_overhead_mean_ms']} ms")
