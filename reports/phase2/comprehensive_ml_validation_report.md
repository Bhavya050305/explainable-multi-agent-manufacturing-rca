# ManuMind AI — Phase 2 Step 9B: Comprehensive ML Testing and Validation Report

**Department:** Department of AI & Data Science, RMK Engineering College  
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Baseline HEAD:** `31fef2fd2b5c9d7e758d9584e4c0b110470599e6`  
**Milestone:** Phase 2 Step 9B — Comprehensive ML Testing and Validation  
**Execution Timestamp:** 2026-11-07T17:19:00Z  
**Verdict:** **VALIDATION COMPLETE — READY FOR INDEPENDENT AUDIT**

---

## 1. Executive Summary

This validation audit report documents the implementation and results of Phase 2 Step 9B for the ManuMind AI machine learning subsystem, reconciled with final Step 9D test isolation corrections. In this milestone, two critical quality and governance objectives were achieved:

1. **Elimination of Frozen Evaluation Partition Dependencies:** Ordinary validation tests were decoupled from frozen test data (`sequences_test.npz`). Both `backend/tests/test_sensor_attribution.py` and `backend/tests/test_lstm_autoencoder.py` were refactored to use deterministic synthetic fixtures (`np.random.RandomState(42)`), guaranteeing zero-read quarantine of test partitions during routine CI/CD test execution while preserving 100% of mathematical attribution and reconstruction assertions.
2. **Comprehensive Multi-Modal and Edge Validation Suite:** A new production-grade validation suite (`backend/tests/test_ml_validation_comprehensive.py`) comprising 16 test functions was implemented and verified across 8 critical risk dimensions: multimodal pairwise orchestration, thread concurrency contention (`_tf_lock` and `_shap_lock`), optical image input format and dimension fuzzing, sequence timestamp validation, extreme physical sensor input handling, pure synthetic sensor attribution, and a 100-cycle repeated inference stability benchmark.

Following implementation, the complete backend regression suite was executed:
- **Baseline Test Items (Step 8):** 102 tests passed across 9 test suites.
- **Post-Validation Test Items (Step 9B/9D):** **118 tests passed across 10 test suites (0 failures, 0 errors, 100% pass rate in 61.53s)**.
- **Protected Model Store Integrity:** All 7 model binaries, scalers, and metadata sidecars remain 100% bit-identical to their cryptographic baseline hashes.
- **Production Asset Integrity:** Zero modifications were made to production ML source code, trained models, scalers, metadata sidecars, datasets, database schemas, or migrations.

---

## 2. Full Test Inventory & Categorization

The test inventory increased from 102 to 118 test items, completely covering point anomaly detection, sequence temporal autoencoding, visual workpiece inspection, analytical MSE attribution, game-theoretic Kernel SHAP explanation, unified orchestration, and concurrent multi-threading.

| Test Module | Step 8 Count | Step 9B/9D Count | Delta | Scope & Coverage |
| :--- | :---: | :---: | :---: | :--- |
| `backend/tests/test_inference_service.py` | 25 | 25 | 0 | Model registry lifecycle, hash validation, tabular/sequence/vision prediction, composite requests, Pydantic JSON serialization, thread safety. |
| `backend/tests/test_isolation_forest.py` | 10 | 10 | 0 | Isolation Forest training isolation, 5-feature schema, binary predictions, finite anomaly scores, serialization parity. |
| `backend/tests/test_lstm_autoencoder.py` | 10 | 10 | 0 | LSTM Autoencoder input/output shapes (30, 5), normal-only sequence training, scaler reuse, threshold calibration (**Refactored to synthetic data**). |
| `backend/tests/test_phase1_audit_and_expansion.py` | 9 | 9 | 0 | Data pipeline integrity, temporal train/val/test split boundaries, sensor reading validation schemas. |
| `backend/tests/test_phase1_db_and_generator.py` | 4 | 4 | 0 | PostgreSQL schema fixtures, synthetic time-series generation, metadata constraints. |
| `backend/tests/test_resnet_defect_classifier.py` | 11 | 11 | 0 | Compact ResNet-18 architecture, 4-class Softmax outputs, synthetic dataset evaluation, confusion matrix parity. |
| `backend/tests/test_sensor_attribution.py` | 10 | 10 | 0 | Step 4 analytical MSE reconstruction attribution, 100% percentage normalization, signed residuals (**Refactored to 100% synthetic fixtures**). |
| `backend/tests/test_sensor_preprocessing.py` | 8 | 8 | 0 | Feature scaling fit, rolling window construction, inversion roundtrip, non-overlapping windows. |
| `backend/tests/test_shap_explainability.py` | 15 | 15 | 0 | Step 6 Kernel SHAP game-theoretic additivity, feature importance rankings, background distribution caching. |
| `backend/tests/test_ml_validation_comprehensive.py` | 0 | **16** | **+16** | **Step 9B comprehensive validation suite covering Categories A through H.** |
| **Total Test Items** | **102** | **118** | **+16** | **100% Passing (61.53s wall-clock duration)** |

---

## 3. Elimination of Frozen Test-Partition Dependencies

### 3.1 Problem Statement
During the Phase 2 Step 9A repository inspection, it was discovered that `backend/tests/test_sensor_attribution.py` directly loaded `ml/models_store/sequences_test.npz` in 5 test functions (`test_03`, `test_06`, `test_07`, `test_08`, and `test_10`). This violated strict ML evaluation governance: ordinary validation tests executed repeatedly in development or CI/CD pipelines must never consume frozen evaluation partitions reserved exclusively for held-out benchmark reporting.

### 3.2 Implemented Refactoring in `test_sensor_attribution.py`
In `backend/tests/test_sensor_attribution.py`:
- Added a module-scoped deterministic synthetic fixture:
  ```python
  @pytest.fixture(scope="module")
  def synthetic_sequence_batch() -> np.ndarray:
      """Generates a deterministic synthetic sequence batch of shape (50, 30, 5)."""
      rng = np.random.RandomState(42)
      return rng.normal(loc=0.0, scale=1.0, size=(50, 30, 5)).astype(np.float32)
  ```
- Replaced all 5 invocations of `np.load(attribution_config.test_sequences_path)` with the `synthetic_sequence_batch` fixture.
- Preserved all mathematical assertions: 100.0% sum normalization, per-channel residual signing, finite metrics, and shape invariance.
- **Result:** `pytest backend/tests/test_sensor_attribution.py` passed 10/10 tests in 21.16s with zero reads from `sequences_test.npz`.

### 3.3 Implemented Refactoring in `test_lstm_autoencoder.py` (Step 9D Correction)
In `backend/tests/test_lstm_autoencoder.py`:
- In the `lstm_artifacts` fixture and `test_reconstruction_error_non_negative_and_finite` (Test 5), replaced `np.load(config.test_sequences_path)` with a deterministic synthetic sequence batch:
  ```python
  rng = np.random.RandomState(42)
  synthetic_sequences = rng.normal(loc=0.0, scale=1.0, size=(580, 30, 5)).astype(np.float32)
  ```
- Preserved the mathematical property assertion: non-negative and finite reconstruction errors across all 580 sequence windows without querying frozen test partitions.
- **Result:** `pytest backend/tests/test_lstm_autoencoder.py` passed 10/10 tests with zero reads from `sequences_test.npz`.

---

## 4. Comprehensive Validation Suite Analysis (`test_ml_validation_comprehensive.py`)

The new test suite implements 16 focused test functions across 8 categories:

### 4.1 Category A: Multimodal Pairwise Orchestration & Isolation
- **`test_multimodal_pairwise_sensor_and_sequence`**: Evaluates simultaneous sensor reading + sequence window without optical vision input. Verified that `sensor_result` and `sequence_result` are populated with their canonical model IDs (`isolation_forest_v1` and `lstm_autoencoder_v1`), while `defect_result` is strictly `None`.
- **`test_multimodal_pairwise_sensor_and_vision`**: Evaluates sensor reading + optical workpiece image without sequence window. Verified that `sequence_result` is strictly `None` and `defect_result` contains 4-class Softmax outputs.
- **`test_multimodal_pairwise_sequence_and_vision`**: Evaluates sequence window + optical workpiece image without point sensor reading. Verified that `sensor_result` is strictly `None`.
- **`test_multimodal_unrequested_modality_isolation`**: Confirms that unrequested modalities do not trigger lazy loading, do not allocate result dictionaries, and do not leak model identifiers into output payloads.

### 4.2 Category B: Multi-Threaded Keras/TensorFlow Concurrency Contention
- **`test_concurrent_keras_tf_lock_contention`**: Concurrently spawns 8 worker threads against the singleton `UnifiedInferenceService` (4 executing LSTM sequence reconstruction and 4 executing ResNet-18 defect inspection).
- **Concurrency Architecture:** Native Keras 3 / TensorFlow CPU graph evaluation is protected by `_tf_lock` in `UnifiedInferenceService`.
- **Outcome:** All 8 worker threads completed within 30 seconds with 0 deadlocks, 0 thread timeouts, and 100% deterministic identical outputs across threads.

### 4.3 Category C: Multi-Threaded Kernel SHAP Lock Contention
- **`test_concurrent_shap_lock_contention`**: Concurrently spawns 4 worker threads requesting Kernel SHAP feature attribution on tabular sensor observations.
- **Internal State Protection:** Kernel SHAP internally mutates state buffers (`self.kernelWeights`, `self.nsamples`). Thread safety is guaranteed via `_shap_lock`.
- **Outcome:** All 4 threads completed without race conditions. Strict additivity was verified across all threads:
  $$\left| f(x) - \left( \mathbb{E}[f] + \sum_{i=1}^{5} \phi_i \right) \right| < 10^{-6}$$
  Identical Shapley values were produced across all concurrent worker threads.

### 4.4 Category D: Vision Input Format & Dimension Fuzzing
- **`test_vision_non_square_image_resizing`**: Asymmetric non-square inputs (256x128 RGB) are automatically bilinearly resized to $(128, 128, 3)$ without tensor distortion or crashing.
- **`test_vision_grayscale_image_conversion`**: Single-channel grayscale PIL images (`mode="L"`) are automatically expanded to 3-channel RGB before tensor normalization.
- **`test_vision_rgba_image_alpha_strip`**: 4-channel transparent RGBA images have their alpha channel cleanly stripped to produce valid 3-channel RGB tensors.
- **`test_vision_invalid_numpy_shape_rejection`**: Arbitrary invalid numpy array inputs (e.g. $(1, 64, 64, 3)$) are rejected with a descriptive `ValueError`.
- **`test_vision_corrupted_image_buffer_rejection`**: Corrupted binary byte headers are safely caught and rejected with `ImageDecodingError`.
- **`test_vision_zero_byte_buffer_rejection`**: Empty byte streams (`b""`) are safely caught and rejected with `ImageDecodingError`.

### 4.5 Category E: Sequence Timestamp Validation & Finding L-03
- **`test_sequence_partial_timestamp_handling`**:
  - Valid monotonic timestamps: Accepted and processed.
  - Omitted timestamps (all `None`): Accepted (timestamps are optional in sequence windows).
  - Strictly non-monotonic timestamps ($t_5 < t_4$ with 30 timestamps provided): Rejected with `TimestampOrderingError`.
  - Boundary lengths (29 or 31 readings): Rejected with validation errors.
  - **Finding L-03 / DEFECT-01 Verification:** When a sequence window payload supplies 29 valid timestamps and 1 `None`, `len(timestamps) == 29 != len(self.readings) == 30`, which bypasses the chronological monotonicity validation loop in `schemas.py:86-94`. This behavior was verified, documented, and flagged for Phase 3 schema hardening.

### 4.6 Category F: Extreme Physical Sensor Outlier Scoring
- **`test_extreme_physical_outlier_scoring`**: Evaluates model behavior under extreme physical sensor fault conditions:
  - $\text{Vibration} = 50.0\text{ mm/s}$ ($> 200\sigma$ surge).
  - $\text{Temperature} = 150.0^\circ\text{C}$ (thermal runaway).
  - $\text{Pressure} = 0.1\text{ bar}$ (vacuum / catastrophic pressure loss).
  - $\text{Current} = 100.0\text{ A}$ (severe electrical overcurrent).
  - $\text{RPM} = 0.0$ (complete motor stall).
- **Outcome:** Yielded continuous anomaly score of $+0.2858$ ($> 0.0269$ frozen threshold), flag `is_anomaly = True`, with zero numerical underflows, zero overflows, and zero NaNs. `NaN` and `Infinity` sensor values are strictly rejected at the Pydantic schema gate with `InvalidSensorValueError`.

### 4.7 Category G: Sensor Attribution on Pure Synthetic Fixtures
- **`test_sensor_attribution_pure_synthetic_fixture`**: Evaluates the analytical Step 4 MSE reconstruction attribution explainer on 50 deterministic synthetic windows of shape $(30, 5)$ without loading `sequences_test.npz`.
- **Outcome:** Verified 100.0% sum normalization across all 50 windows ($\sum_{j=1}^5 \text{contribution}_j = 100.0 \pm 10^{-5}$), signed per-channel residuals, and finite numerical values.

### 4.8 Category H: 100-Cycle Repeated Multi-Modal Inference Benchmark
- **`test_repeated_inference_memory_stability`**: Executes 100 consecutive full multi-modal inference cycles (tabular sensor + 30-step sequence + workpiece image) through `UnifiedInferenceService.predict_unified`.
- **Deterministic Parity:**
  $$\text{anomaly\_score}_{\text{cycle } 0} = \text{anomaly\_score}_{\text{cycle } 99} \quad (\Delta < 10^{-6})$$
  $$\text{reconstruction\_error}_{\text{cycle } 0} = \text{reconstruction\_error}_{\text{cycle } 99} \quad (\Delta < 10^{-6})$$
  $$\text{defect\_type}_{\text{cycle } 0} = \text{defect\_type}_{\text{cycle } 99} = \text{"normal\_surface"}$$
  $$\text{confidence}_{\text{cycle } 0} = \text{confidence}_{\text{cycle } 99} \quad (\Delta < 10^{-4})$$

---

## 5. 100-Cycle Repeated Multi-Modal Latency & Resource Telemetry

A 100-cycle repeated multi-modal benchmark was executed using Python's standard library `tracemalloc` to record observational latency percentiles and process allocations under the local test environment.

### 5.1 Benchmark Observations Table

| Metric | Measured Value | Unit / Observational Description |
| :--- | :---: | :--- |
| **Total Iterations** | 100 | Full multi-modal composite requests (Sensor + Sequence + Vision) |
| **Total Wall-Clock Time** | 54.18 | Seconds |
| **Minimum Latency** | 387.06 | Milliseconds |
| **Median Latency ($p_{50}$)** | 473.31 | Milliseconds per multi-modal composite inference |
| **Mean Latency** | 541.77 | Milliseconds |
| **90th Percentile Latency ($p_{90}$)** | 572.55 | Milliseconds |
| **95th Percentile Latency ($p_{95}$)** | 631.52 | Milliseconds |
| **Maximum Latency ($p_{100}$)** | 6041.57 | Milliseconds (Cycle 0 initial evaluation) |
| **Deterministic Parity** | **100% Identical** | Cycle 0 outputs match Cycle 99 to machine precision ($\Delta < 10^{-6}$) |
| **Tracemalloc Baseline (Start)** | 0.00 | MB (Relative Python-tracked memory at test loop start) |
| **Tracemalloc Peak** | 63.76 | MB |
| **Tracemalloc Net Delta (End)** | 29.89 | MB (Python-tracked heap delta at cycle 99 completion) |

### 5.2 Methodological Limitations on Memory Evidence
- **Python-Tracked Scope:** These observations reflect only Python-level allocations tracked by standard library `tracemalloc`. Native C/C++ memory allocated by TensorFlow, Keras runtime graphs, oneDNN primitives, or PyTorch backends is not fully represented.
- **Leakage and Stability Scope:** Deterministic output parity demonstrates numerical consistency across repetitions, but does not prove memory stability. The 100-cycle experiment does not establish zero memory leakage, process-wide memory stability, or the absence of unbounded memory growth over extended production runtimes.
- **Characterization:** This measurement must be interpreted strictly as a limited observational check under a single-process harness, not as a formal memory-leak certification.

### 5.3 Methodological Limitations on Latency Evidence
- **Local Environment Scope:** The measured latency distribution represents empirical observations under the specific local execution environment, hardware configuration, and single-worker test harness.
- **Cold-Start Hypothesis:** While the first cycle latency (6041.57 ms) coincides with initial model invocation, its precise attribution (e.g. graph compilation versus runtime module initialization) is an observational hypothesis rather than an instrumented root cause.
- **Production Suitability:** These measurements do not establish compliance with a production SLA. Production suitability requires evaluation against an explicitly defined deployment environment, target hardware, production concurrency, serving harness (e.g. ASGI/Triton), and verified operational latency budget.

---

## 6. Model Artifact Cryptographic Integrity Verification

All 7 production machine learning artifacts in `ml/models_store/` were cryptographically hashed using SHA-256 post-validation. All 7 hashes match their approved baseline digests exactly.

| Artifact Filename | Baseline SHA-256 Digest | Post-Validation SHA-256 Digest | Status |
| :--- | :--- | :--- | :---: |
| `sensor_scaler.joblib` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | **MATCH** |
| `isolation_forest.joblib` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | **MATCH** |
| `isolation_forest_metadata.json` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | **MATCH** |
| `lstm_autoencoder.keras` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | **MATCH** |
| `lstm_autoencoder_metadata.json` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | **MATCH** |
| `resnet_defect_classifier.keras` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | **MATCH** |
| `resnet_defect_classifier_metadata.json` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | **MATCH** |

---

## 7. Findings & Limitations Log

| Finding ID | Severity | Category | Summary & Evidence | Resolution / Recommendation |
| :--- | :---: | :---: | :--- | :--- |
| **Finding L-03 / DEFECT-01** | Low | Data Validation | In `backend/app/ml/inference/schemas.py:86-94`, `SequenceWindowInput` checks chronological monotonicity only when `len(timestamps) == len(self.readings)`. If a sequence window has 29 valid timestamps and 1 `None`, the loop is bypassed and out-of-order readings are not caught. | Tested and surfaced in `test_sequence_partial_timestamp_handling`. Production source code was not modified per strict Step 9B governance boundaries. Recommended for Phase 3 schema hardening. |
| **Limitation LIM-01** | Info | Architectural | Multi-threaded concurrency for Keras models (`_tf_lock`) and Kernel SHAP (`_shap_lock`) relies on in-process serialization locks. This design prevents crashes on CPU architectures but limits multi-threaded throughput. | Validated under concurrent stress (8 threads). Horizontal scaling across multi-process workers (e.g. Uvicorn/Gunicorn workers) is recommended for production deployment. |
| **Limitation LIM-02** | Info | Performance | Initial composite inference cycle exhibits high latency (~6.0s), empirically observed during initial execution. | Subsequent cycles in local benchmark exhibited median latency of ~473ms. In production, pre-warming models and serving processes is recommended to mitigate cold-start impact. |

---

## 8. Non-Destructive Compliance & Scope Boundary Audit

| Verification Item | Target Status | Actual Status | Compliance Result |
| :--- | :---: | :---: | :---: |
| Production ML source code modified (`backend/app/ml/`) | Prohibited | None | **COMPLIANT** |
| Model binaries or metadata sidecars modified | Prohibited | None | **COMPLIANT** |
| Training or evaluation datasets modified | Prohibited | None | **COMPLIANT** |
| Database schemas, migrations, or Supabase touched | Prohibited | None | **COMPLIANT** |
| Project roadmap (`plan.md`) modified | Prohibited | None | **COMPLIANT** |
| Git commit or Git push executed | Prohibited | None | **COMPLIANT** |
| Frozen evaluation partitions quarantined from tests | Enforced | Verified | **COMPLIANT** |
| Total backend test suite passing | 118 / 118 | 118 / 118 | **COMPLIANT** |

---

## 9. Governance Verdict & Next Milestone Gate

**Final Quality Verdict:** **VALIDATION COMPLETE — APPROVED**

The ManuMind AI machine learning subsystem has demonstrated rigorous mathematical correctness, full multimodal orchestration capability, robust concurrency locking, strict input validation, and complete test-partition quarantine. All 118 tests pass with 0 failures and 0 errors.

**Next Milestone:** **Phase 2 Step 9C — Independent ML Testing & Validation Audit**.
