# ManuMind AI — Phase 5 Step 4.1: Independent Anomaly Agent Integration and Security Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Audit Milestone:** Phase 5 Step 4.1 — Independent Anomaly Agent Integration and Security Audit  
**Audit Mode:** Strictly Read-Only  
**Supabase Database Revision:** `f3a9082b1c42`  
**Execution Timestamp:** 2026-11-19 22:16:30 IST  
**Final Audit Verdict:** `APPROVED WITH CONDITIONS`

---

## 1. Executive Summary & Audit Verdict

An independent, strictly read-only technical audit of the Phase 5 Step 4 **Anomaly Detection Agent** implementation was conducted. The audit analyzed source files, model stores, preprocessing pipelines, test suites, failure paths, and runtime execution behavior to establish whether the agent genuinely integrates Phase 2 machine learning models or primarily relies on mock/rule-based heuristics.

### Audit Verdict: `APPROVED WITH CONDITIONS`

The implementation satisfies core architectural, typing, and security requirements. However, the audit identified **four critical discrepancies** that must be formally documented and remediated before or alongside Phase 5 Step 5:

1. **Failure Semantics Masking in Downstream Supervisor (`FAILED`):** When anomaly detection encounters fatal execution failures (missing telemetry, non-numeric values, NaN/Inf, or inference exceptions), it generates an execution failure record and sets `confidence = 0.0`. However, it also emits `anomaly_detection_result = AnomalyDetectionResult(is_anomaly=False, anomaly_type=AnomalyType.NONE)`. Downstream, [supervisor.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/supervisor.py) checks only `if not anom_res.is_anomaly`, immediately deciding `SupervisorAction.COMPLETE_WORKFLOW` with $95\%$ confidence and declaring the machine **healthy**. A system crash is thus masked as a normal machine.
2. **Missing LSTM Autoencoder Integration (`FAILED`):** While docstrings and constants (`LSTM_AUTOENCODER_FROZEN_THRESHOLD = 0.901464`) reference the LSTM Autoencoder, `predict_sequence_anomaly` is **never invoked** anywhere in [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py). The agent operates solely on single-timestep tabular readings.
3. **Hard-Coded Baseline Contradiction on Pressure Envelope (`FAILED`):** The baseline envelope constant `DEFAULT_BASELINE_RANGES["pressure"]` is hardcoded as $[1.0, 4.5]\text{ bar}$. In the actual synthetic training dataset, nominal mean pressure is $6.20\text{ bar}$ ($3\sigma = [5.83, 6.57]$). As a result, perfectly healthy nominal telemetry from the dataset is falsely flagged with `affected_sensors: ['pressure']`.
4. **100% Mock Dependency in Unit Tests (`PARTIALLY VERIFIED`):** All 24 unit tests in [test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) execute exclusively against `MockInferenceService`. Not a single test exercises real model inference via `UnifiedInferenceService`. While live execution of the real model pipeline was verified independently during this audit, automated test coverage for real inference is currently zero.

---

## 2. Complete Execution Path Trace

The execution path was traced from the LangGraph node through the inference service down to the serialized model weights:

```
[LangGraph Runtime]
       |
       v
anomaly_detection_node(state)  [anomaly_agent.py:568]
       |
       v
AnomalyDetectionAgent.analyze(state)  [anomaly_agent.py:306]
       |
       +---> _extract_and_validate_telemetry(state)  [anomaly_agent.py:207]
       |        - Validates machine_id
       |        - Checks finite floats (rejects NaN, Inf, non-numeric strings)
       |        - Enforces canonical order: [vibration, temperature, pressure, current, rpm]
       |
       +---> _get_service()  [anomaly_agent.py:191]
       |        - Inspects MANUMIND_ML_PROVIDER (default: 'real')
       |        - Imports & instantiates UnifiedInferenceService [service.py:57]
       |
       +---> UnifiedInferenceService.predict_sensor_anomaly(readings, explain=True) [service.py:105]
       |        |
       |        +---> ModelRegistry.get_scaler() -> sensor_scaler.joblib [registry.py:145]
       |        |        - Applies StandardScaler.transform(raw_vec)
       |        |
       |        +---> ModelRegistry.get_isolation_forest() -> isolation_forest.joblib [registry.py:157]
       |        |        - Calls if_predictor.score(scaled_vec)
       |        |        - Evaluates: score > 0.0269 -> is_anomaly (bool)
       |        |
       |        +---> UnifiedInferenceService.explain_sensor_shap() [service.py:294]
       |                 - Acquires self._shap_lock
       |                 - IsolationForestShapExplainer.explain_observation()
       |                 - Loads background matrix from data/processed/scaled_sensor_train.csv
       |                 - Computes additive Shapley values phi
       |
       +---> Heuristic Taxonomy & Severity Post-Processing  [anomaly_agent.py:435-459]
       |        - Rule-based sensor boundary checks against DEFAULT_BASELINE_RANGES
       |        - Secondary SHAP threshold check (imp > 0.30)
       |        - Severity ratio calculation
       |        - Bounded confidence calculation [0.60, 0.99]
       |
       +---> Provenance & Assessment Generation  [anomaly_agent.py:484-540]
       |        - Synthesizes EvidenceItem with source_reference and is_synthetic flag
       |        - Constructs typed AnomalyAssessment
       |        - Appends AgentExecutionRecord(status=COMPLETED)
       |
       +---> Security Write-Boundary Validation  [anomaly_agent.py:563]
                - Calls validate_agent_state_update(AgentName.ANOMALY_DETECTION, update)
                - Blocks writes to human_approval, verification_decisions, workflow_status
```

---

## 3. ML Integration Verification

| Component | Status | Source File & Function | Reality & Implementation Distinction |
| :--- | :---: | :--- | :--- |
| **Isolation Forest** | `PARTIALLY VERIFIED` | [service.py:105](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py#L105) `predict_sensor_anomaly` | **Real Model Inference** in production. Loads `ml/models_store/isolation_forest.joblib` (SHA256: `afdf3973...`). Evaluates continuous decision score against frozen threshold `0.0269`. However, **100% of unit tests used MockInferenceService**. |
| **LSTM Autoencoder** | `FAILED` | [service.py:165](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py#L165) `predict_sequence_anomaly` | **NOT INVOKED**. Docstrings in [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py) claim integration, but `predict_sequence_anomaly` is never called. The agent only ingests point-in-time readings, not 30-step temporal sequence windows. |
| **StandardScaler Preprocessing** | `VERIFIED` | [service.py:129](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py#L129) `predict_sensor_anomaly` | **Real Preprocessing**. Loads `ml/models_store/sensor_scaler.joblib` (SHA256: `f21f0899...`). Means match training set: `[1.80, 48.00, 6.20, 14.53, 1800.00]`. Scales features via `.transform()` before inference. |
| **Canonical Feature Ordering** | `VERIFIED` | [anomaly_agent.py:44](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py#L44), [service.py:77](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py#L77) | **Real Validation**. Strictly enforces `["vibration", "temperature", "pressure", "current", "rpm"]`. Permuted input dictionaries are canonicalized. |
| **Anomaly Thresholds** | `VERIFIED` | [config.py:41](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/config.py#L41), [anomaly_agent.py:70](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py#L70) | **Real Thresholds**. Isolation Forest calibrated threshold `0.0269` is preserved and checked by both real and mock services. |
| **Kernel SHAP Explainability** | `PARTIALLY VERIFIED` | [service.py:294](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py#L294), [explainer.py:80](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/shap_explainability/explainer.py#L80) | **Mixed Reality**. Real Kernel SHAP runs on 50 background exemplars from `scaled_sensor_train.csv` when `explain=True`. However, `affected_sensors` in [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py) is primarily populated by **hardcoded rule-based envelopes**, with SHAP only used as a secondary filter (`imp > 0.30`). |

---

## 4. Failure Semantics Audit & Downstream Masking Gap

A critical safety defect was uncovered when analyzing failure paths:

### 4.1 Agent Failure Emission
When input telemetry is missing, sensor values are non-numeric, or model inference crashes:
1. `AgentExecutionRecord` is recorded with `execution_status = AgentExecutionStatus.FAILED`.
2. `AnomalyAssessment` is recorded with `confidence = 0.0` and error summary in `explanation`.
3. **DEFECT:** The agent also populates:
   ```python
   "anomaly_detection_result": AnomalyDetectionResult(
       is_anomaly=False,
       anomaly_type=AnomalyType.NONE,
       severity=AnomalySeverity.INFO,
       affected_sensors=[],
       raw_model_scores={"error": 1.0}
   )
   ```
4. Neither `error_details` nor `errors` channels are written by the agent.

### 4.2 Downstream Supervisor Misclassification
In [supervisor.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/supervisor.py#L241-L259):
```python
if state_model.anomaly_detection_result is not None:
    anom_res = state_model.anomaly_detection_result
    if not anom_res.is_anomaly or anom_res.anomaly_type == AnomalyType.NONE:
        return SupervisorDecision(
            next_action=SupervisorAction.COMPLETE_WORKFLOW,
            target_agent=None,
            reason="Anomaly Detection Agent evaluated telemetry within normal operational envelope. No anomaly detected; concluding workflow.",
            decision_confidence=0.95,
            ...
        )
```
The Supervisor does not inspect `agent_executions` for `FAILED`, does not check `confidence == 0.0`, and does not inspect `anomaly_assessment.explanation`.

### 4.3 Verified Impact
A live verification script confirmed this failure masking:
- Input: `sensor_measurements = None` (fatal extraction failure).
- Agent Result: `AgentExecutionStatus.FAILED`, `confidence = 0.0`.
- Supervisor Decision: `next_action = COMPLETE_WORKFLOW`, `decision_confidence = 0.95`, declaring `machine_health = NORMAL`.
- **Verdict:** `FAILED`. Zero confidence from a failed run currently causes the system to conclude that the machine is healthy.

---

## 5. Baseline Operating Envelope & ISO 10816 Audit

The reported operating limits in [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py#L61-L67) were inspected:

```python
DEFAULT_BASELINE_RANGES = {
    "vibration": {"min": 0.0, "max": 4.5},      # mm/s (ISO 10816 Class II threshold)
    "temperature": {"min": 20.0, "max": 75.0},   # °C
    "pressure": {"min": 1.0, "max": 4.5},        # bar
    "current": {"min": 5.0, "max": 25.0},        # A
    "rpm": {"min": 1000.0, "max": 3500.0},       # RPM
}
```

### 5.1 Nature of the Thresholds
- **Classification:** **Hard-coded software constants** representing provisional synthetic assumptions. They are NOT model-trained parameters (the models were trained on scaled Z-scores).

### 5.2 The Pressure Parameter Contradiction (`FAILED`)
- In [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py), `pressure["max"]` is set to `4.5 bar`.
- In the actual synthetic training data generator ([generate_sensor_data.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/data_generator/generate_sensor_data.py#L60)), nominal baseline pressure is generated as:
  $$\text{pressure} = 6.2 + 0.12 \times \mathcal{N}(0, 1) + 0.1 \times \text{shift\_factor}$$
- Inspection of `sensor_scaler.joblib` confirmed the training mean is `6.2017 bar` ($3\sigma = [5.83, 6.57]$).
- **Result:** When normal telemetry from the dataset ($6.20\text{ bar}$) is evaluated, `AnomalyDetectionAgent` falsely reports `affected_sensors: ['pressure']` even when Isolation Forest correctly computes a negative anomaly score (e.g. $-0.1226$).

### 5.3 ISO 10816 Class II Claim Audit
- ISO 10816-1 / ISO 10816-3 defines vibration severity zones for Class II medium-sized industrial machines (15 kW to 75 kW on rigid foundations):
  - Zone A (Good): $< 1.4\text{ mm/s}$ RMS
  - Zone B (Acceptable): $1.4 - 2.8\text{ mm/s}$ RMS
  - Zone C (Unsatisfactory / Warning): $2.8 - 4.5\text{ mm/s}$ RMS
  - Zone D (Unacceptable / Danger): $> 4.5\text{ mm/s}$ RMS
- The value $4.5\text{ mm/s}$ matches the Zone C/D boundary in published engineering standards.
- **However**, in the codebase, this is merely an **inline code comment**. There is no machine-type-specific calibration, no standards lookup module, and no dynamic asset configuration. A CNC Lathe (M101), a 5-Axis Milling Center (M103), a Conveyor (M106), and a Centrifugal Compressor (M107) all share the identical hardcoded envelope.

---

## 6. Security & State Validation Findings

| Security Requirement | Status | Verification Evidence |
| :--- | :---: | :--- |
| **`validate_agent_state_update` at Node Boundary** | `VERIFIED` | Invoked at lines 372, 432, and 563 of [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py). Validates channel updates before LangGraph returns. |
| **Worker `human_approval` Restriction** | `VERIFIED` | Raises `PermissionError` if `human_approval` is in update dictionary. Tested by Test 15. |
| **Worker `verification_decisions` Restriction** | `VERIFIED` | Raises `PermissionError` if `verification_decisions` is in update dictionary. Tested by Test 16. |
| **Worker `workflow_status` Restriction** | `VERIFIED` | Enforced by `FORBIDDEN_WORKER_FIELDS` in [reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/reducers.py#L335). |
| **No Root-Cause Self-Verification** | `VERIFIED` | `CandidateRootCause` model validator forbids `verification_status = VERIFIED`. Tested by Test 17. |
| **No Ticket / Approval Token Generation** | `VERIFIED` | Agent has no bindings to MCP ticket creation tools, no HMAC token generation keys, and no database write access. Tested by Test 18. |
| **Input State Immutability** | `VERIFIED` | Deepcopy comparison confirms input state dictionary is not mutated in-place. Tested by Test 20. |
| **Evidence Provenance & Synthetic Labeling** | `VERIFIED` | `EvidenceItem` correctly preserves `source_type=TELEMETRY`, `source_reference`, `observed_at`, and `synthetic_data_indicator`. Tested by Tests 11 & 12. |
| **Prompt Injection Resistance** | `VERIFIED` | Tested by Test 19. The agent does not execute LLM prompts, and string sanitizers neutralize malicious markup. |

---

## 7. Test Quality & Mock Reliance Audit

| Category | Finding | Detail |
| :--- | :---: | :--- |
| **Total Tests** | 24 | All 24 tests pass in 5.35 seconds. |
| **Mocked Inference Tests** | **24 (100%)** | All 24 tests explicitly inject `MockInferenceService` or set `MANUMIND_ML_PROVIDER=mock`. |
| **Real Inference Tests** | **0 (0%)** | Zero unit tests in [test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) instantiate real `UnifiedInferenceService`. |
| **Reason for Mock Reliance** | Performance | Real inference imports TensorFlow, Matplotlib, and scikit-learn, causing a ~45-second cold-start delay on Windows. Mocks were used to keep CI test execution under 6 seconds. |
| **Testing Gap** | Integration | While live execution confirmed that `UnifiedInferenceService` works with `AnomalyDetectionAgent`, this path is entirely unmonitored by automated test suites. |

---

## 8. Environmental Invariants Audit

All environmental invariants were cryptographically and programmatically verified in read-only mode:

- **Python Version:** 3.11.9 (`VERIFIED`)
- **LangGraph Version:** 0.2.45 (`VERIFIED`)
- **LangChain Core Version:** 0.3.15 (`VERIFIED`)
- **Pydantic Version:** 2.13.4 (`VERIFIED`)
- **Base Environment `pip check`:** Clean (`No broken requirements found.`)
- **RAG Lockfile:** [backend/requirements-rag.lock](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/requirements-rag.lock) SHA256: `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` (`VERIFIED`)
- **ChromaDB Store:** Collection `manumind_bge_small_v1` in `knowledge_base/index/chroma_bge_small_v1` contains **564 documents** of dimension **384** (`VERIFIED`)
- **Supabase Migration Revision:** `f3a9082b1c42` (`VERIFIED` — no mutations performed)
- **Model Store Artifact Hashes:** All 7 model files in `ml/models_store/` match their baseline SHA-256 hashes (`VERIFIED`)
- **Git HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` on branch `main` with 0 staged changes (`VERIFIED`)

---

## 9. Conditions for Proceeding to Phase 5 Step 5

To proceed safely to Phase 5 Step 5 (Root Cause Analysis Agent Implementation), the following four conditions must be addressed:

### Condition 1: Remediate Downstream Failure Masking in Supervisor
- **Action:** In [supervisor.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/supervisor.py), update the Post-Anomaly Detection evaluation block to check:
  1. `any(rec.execution_status == AgentExecutionStatus.FAILED for rec in state_model.agent_executions)`
  2. `state_model.anomaly_assessment.confidence == 0.0`
  3. `state_model.error_details is not None`
- If any failure is detected, the Supervisor must NOT decide `COMPLETE_WORKFLOW`. It must route to `SupervisorAction.FAIL_WORKFLOW` or `SupervisorAction.ESCALATE_TO_HUMAN_GATE`.

### Condition 2: Correct Baseline Pressure Envelope Contradiction
- **Action:** In [anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py#L64), update `DEFAULT_BASELINE_RANGES["pressure"]` to reflect the synthetic dataset distribution:
  ```python
  "pressure": {"min": 4.5, "max": 8.0},  # bar (calibrated to training distribution mean 6.20 bar)
  ```
  Alternatively, dynamically load machine operational envelopes from the asset profiles table.

### Condition 3: Formally Define Architectural Scope for LSTM Autoencoder
- **Action:** Formally clarify whether sequence reconstruction with the LSTM Autoencoder is:
  1. Deferred to a dedicated temporal sequence analysis node in Phase 5 Step 6,
  2. Integrated as a diagnostic tool for the Root Cause Analysis Agent (Phase 5 Step 5), or
  3. Intended to be added to `AnomalyDetectionAgent` when a 30-reading sequence window is available.
  Update docstrings and remove dead imports/constants accordingly.

### Condition 4: Add Production Model Integration Test
- **Action:** Add at least one explicit integration test (or an opt-in test using a `--run-real-models` flag) that executes `AnomalyDetectionAgent` with `UnifiedInferenceService` without mocks, verifying that `sensor_scaler.joblib`, `isolation_forest.joblib`, and Kernel SHAP load and infer correctly.

---

## 10. Conclusion

The Anomaly Detection Agent represents a functional, typed, and secure LangGraph node. However, the discovery of downstream failure masking and parameter envelope contradictions validates the necessity of this independent audit. With the four conditions clearly identified and ready for remediation, the system is **APPROVED WITH CONDITIONS**.
