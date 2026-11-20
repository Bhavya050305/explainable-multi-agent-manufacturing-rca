# ManuMind AI — Phase 5 Step 4: Anomaly Detection Agent Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Milestone:** Phase 5 Step 4 — Anomaly Detection Agent Implementation  
**Supabase Migration Revision:** `f3a9082b1c42`  
**Execution Timestamp:** 2026-11-19 22:05:00 IST  
**Final Verdict:** `SUCCESS`

---

## 1. Executive Summary

In Phase 5 Step 4, the **ManuMind Anomaly Detection Agent** was implemented as the second operational LangGraph node in the Phase 5 multi-agent architecture. The Anomaly Detection Agent is responsible for analyzing industrial machine telemetry, detecting multivariate anomalies using calibrated machine learning models (Isolation Forest and LSTM Autoencoder), extracting feature-level explainability (Kernel SHAP and analytical MSE attribution), and producing structured, typed evidence items for the Supervisor Agent.

The implementation satisfies all architectural, security, and verification requirements:
- **Canonical Feature Ordering:** Strictly enforces the canonical 5-channel feature invariant: `["vibration", "temperature", "pressure", "current", "rpm"]`.
- **Calibrated Baseline Envelopes:** Evaluates sensor deviations against calibrated normal operational boundaries (e.g., vibration baseline $\le 4.5\text{ mm/s}$ based on ISO 10816 Class II).
- **Explainable Anomaly Assessments:** Formulates structured `AnomalyAssessment` models containing machine IDs, observed readings, baseline envelopes, taxonomy classifications (`VIBRATION_SPIKE`, `OVERHEATING`, `PRESSURE_DROP`, `ELECTRICAL_FAULT`, `MULTIVARIATE_ANOMALY`), bounded confidence scores $[0.60, 0.99]$, and honest limitation disclosures.
- **Traceable Evidence Provenance:** Automatically generates `EvidenceItem` records with unique identifiers, source references (`telemetry_channel_<sensor>`), observation timestamps, and synthetic data flags (`is_synthetic=True`).
- **Strict Security Governance:** Operates within worker agent boundaries. State updates are validated via `validate_agent_state_update(AgentName.ANOMALY_DETECTION, update)`, strictly forbidding writes to `human_approval`, `verification_decisions`, or `workflow_status`. The agent cannot self-verify root causes, generate approval tokens, or invoke ticket-creation tools.
- **Fail-Safe Inference Fallback:** Under degraded conditions (missing telemetry, non-numeric values, NaN/Inf, or model crashes), the agent logs an execution failure record and safely returns `anomaly_detected=False` with zero confidence. No false alarms or fabricated anomalies are ever generated.
- **Comprehensive Test Suite:** Authored 24 dedicated unit tests in [test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) covering all functional, edge-case, and security scenarios. The complete Phase 5 regression suite (88 tests) passes with a 100% pass rate in 6.64 seconds.

---

## 2. Preflight Inspection & Existing Capabilities Integration

Before authoring code, an audit was conducted across the Phase 1 and Phase 2 machine learning inference pipeline:
1. **Unified Inference Facade:** [service.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/inference/service.py) provides `UnifiedInferenceService`, which coordinates:
   - Tabular Isolation Forest (`predict_sensor_anomaly`) calibrated at threshold `0.0269`.
   - Sequence LSTM Autoencoder (`predict_sequence_anomaly`) calibrated at threshold `0.901464`.
   - Explainability facades (`explain_sensor_shap` using Kernel SHAP and `explain_sequence_attribution` using analytical MSE reconstruction error).
2. **Canonical Feature Ordering:** Machine learning models were pre-trained and serialized using the exact feature order `["vibration", "temperature", "pressure", "current", "rpm"]`. Permuted or scrambled feature dictionaries must be canonicalized prior to vectorization.
3. **Deterministic Mock Service:** To ensure high-speed, deterministic unit testing and CI/CD validation without requiring GPU memory or 15-second TensorFlow model initializations, `MockInferenceService` was implemented mirroring the exact production interface. In production environments, `AnomalyDetectionAgent` dynamically resolves `UnifiedInferenceService`.

---

## 3. Files Created and Modified

| File | Action | Purpose |
| :--- | :--- | :--- |
| [backend/app/agents/schemas.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/schemas.py) | Modified | Added `AnomalyAssessment` Pydantic V2 schema with finite float validators (rejecting NaN, Inf, non-finite values) and text sanitization. |
| [backend/app/agents/state.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/state.py) | Modified | Added `anomaly_assessment: Annotated[Optional[AnomalyAssessment], overwrite_supervisor_field]` channel to `ManuMindState` and `ManuMindStateModel`. |
| [backend/app/agents/anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/anomaly_agent.py) | Created | Implemented `AnomalyDetectionAgent` class, `MockInferenceService`, and the LangGraph-compatible `anomaly_detection_node` entry point. |
| [backend/app/agents/__init__.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/__init__.py) | Modified | Exported `AnomalyAssessment`, `AnomalyDetectionAgent`, `MockInferenceService`, and `anomaly_detection_node`. |
| [backend/tests/test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) | Created | Authored 24 comprehensive unit tests verifying functional inference, feature ordering, provenance, security boundaries, and LangGraph node compilation. |
| [docs/reports/phase5_step4_anomaly_agent.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/phase5_step4_anomaly_agent.json) | Created | Machine-readable audit artifact documenting all technical verification evidence. |
| [docs/reports/phase5_step4_anomaly_agent.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/phase5_step4_anomaly_agent.md) | Created | Human-readable comprehensive completion report. |

---

## 4. Anomaly Detection Agent Architecture

```
                            +---------------------------------+
                            |       Incoming Shared State     |
                            |   (ManuMindState: Telemetry)    |
                            +----------------+----------------+
                                             |
                                             v
                            +---------------------------------+
                            | Telemetry Validation Engine     |
                            | - Finite numeric checks         |
                            | - Rejects NaN, Inf, Strings     |
                            | - Canonical 5-channel ordering  |
                            +----------------+----------------+
                                             |
                                             v
                            +---------------------------------+
                            | Unified ML Inference Service    |
                            | - Isolation Forest (0.0269)     |
                            | - LSTM Autoencoder (0.901464)   |
                            | - Kernel SHAP Attribution       |
                            +----------------+----------------+
                                             |
                                             v
                            +---------------------------------+
                            | Evidence & Assessment Synthesis |
                            | - Domain taxonomy mapping       |
                            | - Bounded confidence scoring    |
                            | - Traceable EvidenceItem with   |
                            |   provenance & synthetic flags  |
                            +----------------+----------------+
                                             |
                                             v
                            +---------------------------------+
                            | Security Write-Boundary Gate    |
                            | validate_agent_state_update()   |
                            | (Blocks human_approval writes)  |
                            +----------------+----------------+
                                             |
                                             v
                            +---------------------------------+
                            | Return Partial State Update     |
                            | (anomaly_assessment, evidence)  |
                            +---------------------------------+
```

### 4.1 Canonical Features and Calibrated Envelopes
The agent strictly preserves the 5-channel telemetry structure:
- **`vibration`** ($\text{mm/s}$): Normal $[0.0, 4.5]$. ISO 10816 Class II threshold.
- **`temperature`** ($^\circ\text{C}$): Normal $[20.0, 75.0]$.
- **`pressure`** ($\text{bar}$): Normal $[1.0, 4.5]$.
- **`current`** ($\text{A}$): Normal $[5.0, 25.0]$.
- **`rpm`** ($\text{RPM}$): Normal $[1000.0, 3500.0]$.

### 4.2 Bounded Confidence Calculation
Confidence is never represented as an unbounded float or naive probability. Confidence for detected anomalies is calibrated against the margin by which the anomaly score exceeds the frozen threshold:
$$\text{confidence} = \min\left(0.99, \max\left(0.60, 0.65 + \min\left(0.30, \frac{\text{score} - \text{threshold}}{\text{threshold}} \times 0.25\right)\right)\right)$$
For telemetry operating within the baseline envelope, baseline confidence is recorded as $0.95$.

---

## 5. Security & Governance Invariants

1. **Worker Write-Boundary Governance:** The agent cannot directly modify:
   - `human_approval` (cannot self-authorize ticket staging or maintenance work).
   - `verification_decisions` (cannot self-verify root cause hypotheses).
   - `workflow_status` (cannot prematurely complete or restart workflows).
   Attempting to write to any of these fields triggers an immediate `PermissionError` via `validate_agent_state_update`.
2. **No Token Generation or Tool Calls:** The agent contains no cryptographic HMAC signing utilities, no token table models, and no tool bindings to the Supabase ticket creation MCP server.
3. **Prompt Injection Resistance:** Malicious strings embedded within sensor telemetry descriptions or unit annotations cannot modify agent permissions or bypass validation boundaries.
4. **Input State Immutability:** The input `ManuMindState` is treated as strictly read-only and is verified to remain unmutated across execution cycles.
5. **Non-Fabricating Fallback:** In the event of model errors, missing telemetry, or out-of-memory exceptions, the agent records an execution failure and returns `anomaly_detected=False`. No phantom alerts or speculative alarms are produced during system degradation.

---

## 6. Unit Test Verification Results

All 24 dedicated unit tests in [backend/tests/test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) passed:

| # | Test Case Description | Result | Duration |
| :-: | :--- | :-: | :-: |
| 1 | Valid telemetry produces a valid anomaly assessment | `PASSED` | 0.003s |
| 2 | Normal telemetry is not incorrectly labeled anomalous | `PASSED` | 0.002s |
| 3 | Abnormal telemetry is identified (e.g. vibration > 4.5 mm/s) | `PASSED` | 0.003s |
| 4 | Missing telemetry produces a controlled result without crash | `PASSED` | 0.003s |
| 5 | Invalid sensor values (non-numeric) are rejected | `PASSED` | 0.003s |
| 6 | NaN and infinity in sensor readings are rejected | `PASSED` | 0.003s |
| 7 | Invalid confidence values are rejected by AnomalyAssessment | `PASSED` | 0.003s |
| 8 | Model inference failures are handled safely (controlled degraded state) | `PASSED` | 0.004s |
| 9 | Existing preprocessing feature extraction is reused correctly | `PASSED` | 0.003s |
| 10 | Feature ordering is preserved ([vibration, temperature, pressure, current, rpm]) | `PASSED` | 0.003s |
| 11 | Anomaly evidence includes provenance (machine_id, source_reference, observed_at) | `PASSED` | 0.004s |
| 12 | Synthetic evidence remains labeled synthetic (is_synthetic=True) | `PASSED` | 0.003s |
| 13 | SHAP or explainability metadata is preserved when available | `PASSED` | 0.004s |
| 14 | Missing explainability is reported honestly in limitations | `PASSED` | 0.003s |
| 15 | Agent cannot modify human_approval (raises PermissionError via validate_agent_state_update) | `PASSED` | 0.002s |
| 16 | Agent cannot modify verification_decisions (raises PermissionError) | `PASSED` | 0.002s |
| 17 | Agent cannot mark root causes VERIFIED | `PASSED` | 0.004s |
| 18 | Agent cannot create tickets or approval tokens | `PASSED` | 0.003s |
| 19 | Prompt injection in input text cannot alter permissions | `PASSED` | 0.003s |
| 20 | Input shared state remains immutable | `PASSED` | 0.003s |
| 21 | LangGraph node execution works correctly (anomaly_detection_node(state)) | `PASSED` | 0.018s |
| 22 | State update validation executes at the real node boundary | `PASSED` | 0.003s |
| 23 | Serialized anomaly assessments can be reconstructed (model_validate_json) | `PASSED` | 0.005s |
| 24 | Inference fallback never fabricates a successful anomaly prediction | `PASSED` | 0.003s |

---

## 7. Phase 5 Regression Test Suite Results

Running the full Phase 5 test suite across all 5 test files:
```powers
pytest backend/tests/test_agent_state.py \
       backend/tests/test_agent_reducers.py \
       backend/tests/test_agent_verification_governance.py \
       backend/tests/test_supervisor_agent.py \
       backend/tests/test_anomaly_agent.py -v --durations=0
```

| Test File | Total Tests | Passed | Failed |
| :--- | :-: | :-: | :-: |
| [backend/tests/test_agent_state.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_state.py) | 10 | 10 | 0 |
| [backend/tests/test_agent_reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_reducers.py) | 11 | 11 | 0 |
| [backend/tests/test_agent_verification_governance.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_verification_governance.py) | 23 | 23 | 0 |
| [backend/tests/test_supervisor_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_supervisor_agent.py) | 20 | 20 | 0 |
| [backend/tests/test_anomaly_agent.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_anomaly_agent.py) | 24 | 24 | 0 |
| **Total** | **88** | **88** | **0** |

**Execution Duration:** 6.64 seconds.  
**Pass Rate:** 100.0%.

---

## 8. Environmental & System Invariants

All baseline system invariants were verified immediately following test execution:
- **Python Version:** 3.11.9
- **LangGraph Version:** 0.2.45
- **LangChain Core Version:** 0.3.15
- **Pydantic Version:** 2.13.4
- **Pip Check:** `No broken requirements found.`
- **RAG Lockfile:** [backend/requirements-rag.lock](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/requirements-rag.lock) SHA256: `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` (verified unchanged).
- **ChromaDB Document Count:** 564 embeddings in [knowledge_base/index/chroma_bge_small_v1](file:///D:/Desktop/FInal%20year%20project/manumind-ai/knowledge_base/index/chroma_bge_small_v1) (verified unchanged).
- **Supabase Database Revision:** `f3a9082b1c42` (verified unchanged; no mutations performed).
- **Git HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` on branch `main` (0 staged changes).

---

## 9. Conclusion & Next Steps

Phase 5 Step 4 is **COMPLETE** with a final verdict of `SUCCESS`. The Anomaly Detection Agent is operational, strictly governed by typed schema boundaries, resilient against malicious or corrupted input, and fully integrated with LangGraph.

Per the project scope restrictions:
- The Root Cause Analysis Agent (Phase 5 Step 5) has not been implemented.
- The complete multi-agent orchestrator graph (Phase 5 Step 6) has not been implemented.
- No Git commits, pushes, or resets were performed.
- All live database tables and model weights remain strictly preserved.
