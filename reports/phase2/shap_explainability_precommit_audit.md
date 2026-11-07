# ManuMind AI — Phase 2 Step 6: SHAP Explainability Pre-Commit Audit Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Component:** Phase 2 Step 6 — Isolation Forest Kernel SHAP Explainability Engine  
**Role:** Senior XAI Research Engineer, Python Backend Engineer, and Independent Code Auditor  
**Date:** November 2026  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Audit Status:** **AUDITED, VERIFIED & RECOMMENDED FOR COMMIT**  

---

## 1. Executive Audit Decision

Following targeted source inspection, instrumentation, schema compatibility resolution, and full regression testing, this audit issues an unequivocal **READY FOR COMMIT** recommendation for Phase 2 Step 6.

All four pre-commit audit issues have been conclusively resolved:
1. **Pydantic/API Compatibility:** Updated `backend/app/schemas/alert.py` from `Optional[Dict[str, float]]` to `Optional[Dict[str, Any]]`, enabling full validation and serialization of rich structured SHAP payloads without database migrations. Verified via expanded unit test `test_12_json_serialization`.
2. **Background Seed Provenance:** Conclusively documented that the base seed is `42`, per-machine selection seeds are derived deterministically as `42 + machine_num` (e.g. M101 = 143, M104 = 146, M110 = 152), and the payload records the master base seed `42`. Verified that the identical 50-exemplar background is constructed once and reused for all explanations.
3. **Model Artifact Hash Verification:** Verified that `ml/models_store/isolation_forest.joblib` matches exact SHA-256 hash `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2`. Explicitly documented that this cryptographic hash is tracked at the evaluation report and repository level, while the per-alert JSON payload stores the artifact filename `isolation_forest.joblib`.
4. **Kernel SHAP Coalition Evaluation Accounting:** Empirically instrumented the model wrapper to establish exact forward-pass counts across both lifecycle phases:
   - **Initialization:** 1 model call of shape `(50, 5)` (50 rows) to evaluate the background and establish $\mathbb{E}[f(X)] = -0.04778226$.
   - **Per-Observation Explanation:** 3 model calls totaling 1,502 rows (1 call of shape `(1, 5)` for explainer score computation, 1 call of shape `(1, 5)` inside `KernelExplainer` for the grand coalition, and 1 vectorized call of shape `(1500, 5)` evaluating all 30 non-trivial coalitions $\times$ 50 background exemplars). Verified that `nsamples=32` capped at `2^5 - 2 = 30` produces exhaustive coalition coverage.

---

## 2. Exact Files Inspected and Modified

### Inspected Files:
- `backend/app/schemas/alert.py` (Pydantic alert schema definition)
- `backend/app/models/alert.py` (SQLAlchemy `Alert` model with `Column(JSON)`)
- `backend/app/services/ticket_service.py` (Human-in-the-loop approval service)
- `backend/app/ml/shap_explainability/config.py` (Configuration and sampling parameters)
- `backend/app/ml/shap_explainability/explainer.py` (Kernel SHAP explainer core)
- `backend/tests/test_shap_explainability.py` (Unit and integration test suite)
- `ml/models_store/isolation_forest.joblib` (Trained model artifact)
- `shap.explainers._kernel.py` (Installed SHAP 0.51.0 source implementation)

### Modified Files:
1. [`backend/app/schemas/alert.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/schemas/alert.py):
   - Relaxed `shap_json` and `sensor_contrib_json` from `Optional[Dict[str, float]]` to `Optional[Dict[str, Any]]` to support full structured explainability dictionaries while preserving full backward compatibility with flat float dictionaries.
2. [`backend/tests/test_shap_explainability.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_shap_explainability.py):
   - Expanded `test_12_json_serialization` to validate that the rich explanation payload instantiates, validates, and serializes cleanly within `AlertCreate` and `AlertResponse` Pydantic models.

---

## 3. Pydantic / API JSON Compatibility Resolution

### 3.1 Problem Identification
The database column `Alert.shap_json` is declared as generic SQLAlchemy `Column(JSON, nullable=True)`, capable of persisting arbitrary JSON objects. However, `backend/app/schemas/alert.py` previously declared:
```python
shap_json: Optional[Dict[str, float]] = None
```
Because the production `IsolationForestShapExplainer` returns a rich structured dictionary containing strings (`status`, `machine_id`, `explained_model`, `attribution_units`), floats (`anomaly_score`, `base_value`, `computation_time_ms`), booleans (`additivity_verified`), integers (`step`, `background_samples`, `background_seed`), lists (`feature_order`), and nested dictionaries (`feature_attributions`), any attempt to pass the full explanation dictionary through `AlertCreate` or serialize it via `AlertResponse` failed Pydantic schema validation.

### 3.2 Implemented Resolution
In [`backend/app/schemas/alert.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/schemas/alert.py), the declarations were updated:
```python
class AlertBase(BaseModel):
    id: str
    machine_id: str
    risk: float = Field(..., ge=0.0, le=1.0)
    criticality: int = Field(..., ge=1, le=5)
    impact: int = Field(..., ge=1, le=5)
    priority_score: float
    shap_json: Optional[Dict[str, Any]] = None
    sensor_contrib_json: Optional[Dict[str, Any]] = None
    status: str = "PENDING_APPROVAL"
```

### 3.3 Verification Evidence
`test_12_json_serialization` in `backend/tests/test_shap_explainability.py` was updated with:
```python
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
```
Result: **PASSED**. Zero database migrations were introduced, and existing Phase 1 database tests (`test_phase1_db_and_generator.py`) continue to pass 100%.

---

## 4. Background Seed Provenance Verification

### 4.1 Exact Code Implementation
Source inspection of `backend/app/ml/shap_explainability/config.py` and `explainer.py` establishes:
1. **Base Master Seed:** `RANDOM_SEED = 42` (defined in `config.py:46`).
2. **Per-Machine Seed Derivation:** Inside `_build_background()` (`explainer.py:163`):
   ```python
   m_seed = self.config.random_seed + int(machine_id.replace("M", ""))
   rng = np.random.RandomState(m_seed)
   ```
   Each machine draws from its own independent pseudo-random stream:
   - `M101`: Seed $42 + 101 = 143$
   - `M102`: Seed $42 + 102 = 144$
   - `M103`: Seed $42 + 103 = 145$
   - `M104`: Seed $42 + 104 = 146$
   - `M105`: Seed $42 + 105 = 147$
   - `M106`: Seed $42 + 106 = 148$
   - `M107`: Seed $42 + 107 = 149$
   - `M108`: Seed $42 + 108 = 150$
   - `M109`: Seed $42 + 109 = 151$
   - `M110`: Seed $42 + 110 = 152$
3. **Samples Per Machine:** Exactly 5 normal training rows sampled per machine (`samples_per_machine = 5`).
4. **Total Background Size:** Exactly 50 observations ($10 \text{ machines} \times 5 = 50$).
5. **Reusability:** The background dataset is constructed **once** during explainer instantiation (`_build_background()` in `__init__`) and passed into `shap.KernelExplainer`. The identical background matrix is preserved in memory and reused for every explanation across the entire lifetime of the explainer instance.
6. **Report Clarification:** In the explanation JSON output, `"background_seed": 42` records the master configuration base seed (`self.config.random_seed`), while the per-machine selection logic uses the deterministic derivation documented above.

---

## 5. Model Artifact Hash Verification

### 5.1 Artifact Integrity
The SHA-256 hash of [`ml/models_store/isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib) was computed:
```text
Computed SHA-256: afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2
Matches Expected: True
```

### 5.2 Provenance Storage Limitation
- **In-Payload Field:** The per-observation explanation JSON records `"model_artifact": "isolation_forest.joblib"`, tracking the file basename.
- **Report-Level Tracking:** The full 64-character cryptographic SHA-256 hash is recorded in `reports/phase2/shap_explainability_report.md` and verified by automated unit tests (`test_01_model_loading_and_attributes`).
- **Limitation Statement:** The SHA-256 hash is tracked at the evaluation report and test level, not embedded inside individual telemetry alert records. In accordance with strict audit preservation rules, the frozen test cohort was **not** rerun to alter this payload schema.

---

## 6. Kernel SHAP Initialization & Coalition Accounting

### 6.1 Empirical Instrumentation Results
By instrumenting `IsolationForestShapExplainer.anomaly_intensity_wrapper` on Python 3.11 with SHAP 0.51.0, the exact model calls and row counts were captured:

| Execution Stage | Number of Calls | Input Shapes | Total Rows | Purpose |
| :--- | :---: | :---: | :---: | :--- |
| **Explainer Initialization** | 1 | `(50, 5)` | 50 | Evaluates background data to precompute $\mathbb{E}[f(X)] = -0.04778226$ |
| **Explanation: Score Calculation** | 1 | `(1, 5)` | 1 | Evaluates target observation $f(x)$ in `explainer.py` for reporting & additivity |
| **Explanation: Grand Coalition ($F$)** | 1 | `(1, 5)` | 1 | Evaluates target input in `KernelExplainer.explain()` |
| **Explanation: Non-Trivial Coalitions**| 1 | `(1500, 5)` | 1,500 | Evaluates 30 masked feature subsets $\times$ 50 background rows |
| **Total During Single Explanation** | **3** | — | **1,502** | Complete single observation explanation |

### 6.2 Source-Code Verification of Exhaustive Coverage
Source inspection of `shap/explainers/_kernel.py` confirms the coalition accounting logic:
```python
self.max_samples = 2**self.M - 2  # For M=5: 2^5 - 2 = 30
if self.nsamples > self.max_samples:
    self.nsamples = self.max_samples
```
1. **Empty Coalition ($\emptyset$):** Assigned precomputed expected value $\mathbb{E}[f(X)]$. While it requires zero model evaluations *during inference*, it required 1 model evaluation over the 50 background rows during *initialization*.
2. **Grand Coalition ($F$):** Evaluated once on the input point ($1$ row).
3. **Coalition Budget Capping:** When `nsamples = 32` is configured, SHAP's kernel regression routine caps `nsamples` at `max_samples = 30`.
4. **Exhaustiveness:** Because all 30 non-trivial subsets are enumerated deterministically with analytic Shapley kernel weights, **100% of the coalition lattice is evaluated**. There is zero Monte Carlo sampling or random subset selection.

---

## 7. Test Results with Actual Outputs

### 7.1 SHAP Explainability Test Suite
```text
(venv) PS D:\Desktop\FInal year project\manumind-ai> python -m pytest backend/tests/test_shap_explainability.py -q
...............                                                          [100%]
15 passed, 10 warnings in 27.63s
```

### 7.2 Full Backend Regression Suite
```text
(venv) PS D:\Desktop\FInal year project\manumind-ai> python -m pytest backend/tests -q
..................................................................       [100%]
66 passed, 10 warnings in 38.13s
```
*Regression Rate:* **0.0%** (all 66 existing unit, integration, database, and model tests pass).

---

## 8. Protected Artifact Integrity Verification

| Protected Component | Checksum / Verification Target | Audit Status |
| :--- | :--- | :---: |
| **Isolation Forest Model** | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | **VERIFIED IMMUTABLE** |
| **StandardScaler Artifact** | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | **VERIFIED IMMUTABLE** |
| **Training Dataset** | `5198e60432aab3fa4318742fa9766a422d4feaaa536324ef34ff0d61285d7646` | **VERIFIED IMMUTABLE** |
| **Validation Dataset** | `2fb4536523cec55154b50020502788bb7200d08f813af67941b4a74068c2e9a2` | **VERIFIED IMMUTABLE** |
| **Test Dataset** | `988911fb3f83a17d7604cc25558070aa45f28c6c9a67c143b646ac85cedffbca` | **VERIFIED IMMUTABLE** |
| **Alembic Migrations** | Exactly 1 version (`1273f18b72a2_initial_tables.py`); zero new migrations | **VERIFIED IMMUTABLE** |
| **Completed Steps 0–5** | Code, reports, models, and test assertions preserved | **VERIFIED IMMUTABLE** |
| **Robustness Experiments** | E1–E7 remain unexecuted (proposed designs only) | **VERIFIED IMMUTABLE** |

---

## 9. Frozen Test Evaluation Preservation

- The frozen 70-observation test cohort (`scaled_sensor_test.csv`, steps 3400–3999) was evaluated **strictly once** during initial Step 6 pipeline execution.
- No test data was used for background construction or calibration.
- Zero test evaluations were repeated, recalculated, or tuned during this pre-commit audit.
- `reports/phase2/shap_explainability/shap_evaluation_results.json` remains preserved.

---

## 10. Final Git Status Inspection

```text
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   backend/app/schemas/alert.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/app/ml/shap_explainability/
	backend/tests/test_shap_explainability.py
	reports/phase2/shap_explainability/
	reports/phase2/shap_explainability_inspection_plan.md
	reports/phase2/shap_explainability_precommit_audit.md
	reports/phase2/shap_explainability_report.md

no changes added to commit (use "git add" to track)
```

- `git diff --stat`:
  ```text
  backend/app/schemas/alert.py | 4 ++--
  1 file changed, 2 insertions(+), 2 deletions(-)
  ```
- `git diff --cached --stat`: `(empty — zero files staged)`
- `git branch --show-current`: `main`

---

## 11. Remaining Limitations

1. **Interventional Independence Assumption:** Standard Kernel SHAP perturbs features along marginal distributions rather than conditional distributions ($p(x_{\bar{S}} | x_S) \approx p(x_{\bar{S}})$), which can evaluate off-manifold combinations when features are correlated.
2. **Model Attribution vs. Physical Causality:** SHAP attributes credit according to the Isolation Forest mathematical decision geometry. It does not establish physical causal breakdown sequences.
3. **Component Latency:** Measured P95 explanation latency ($107.58\text{ ms}$) is a standalone component benchmark and does not constitute an end-to-end production pipeline latency guarantee.

---

## 12. Recommendation: READY FOR COMMIT

**Audit Conclusion:** **READY FOR COMMIT**

Phase 2 Step 6 has fulfilled all algorithmic, mathematical, architectural, and governance criteria. All code modifications are validated, all tests are passing (66/66), and all protected assets remain strictly unmodified.

**Awaiting user authorization to stage, commit, and push.**
