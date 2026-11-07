# ManuMind AI — Phase 2 Step 6: SHAP Explainability Inspection & Implementation Plan

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science  
**Component:** Phase 2 Step 6 — SHAP Explainability Architecture & Audit Planning  
**Date:** November 2026  
**Status:** **FINAL PRE-IMPLEMENTATION AUDIT COMPLETED — CONDITIONAL GO (AWAITING APPROVAL)**  

---

## 1. Executive Summary

This report delivers the comprehensive technical inspection, independent audit, and implementation roadmap for **Phase 2 Step 6: SHAP Explainability** within the ManuMind AI platform.

The objective of Step 6 is to integrate game-theoretic feature attribution (SHAP — Shapley Additive Explanations) into the manufacturing anomaly detection supervisory pipeline. Following the formal closure of Step 5 (which rejected supervised failure-risk tree regression due to chronological target distribution shift and absence of training fault progression), Step 6 realigns explainability directly with the **verified Phase 2 anomaly detection models**:
- **Model 1: Isolation Forest** (tabular multivariate anomaly detection on 5 telemetry channels).
- **Model 2: LSTM Autoencoder** (temporal multivariate sequence reconstruction on 30-step windows).

### Key Audit & Re-Audit Findings:
1. **Existing Infrastructure Alignment:** The database schema ([`backend/app/models/alert.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/alert.py)) already contains dedicated columns for dual-layer attribution: `shap_json` (tabular game-theoretic attribution) and `sensor_contrib_json` (LSTM reconstruction error per sensor).
2. **Library Availability:** `shap` (version **0.51.0**) and `scikit-learn` (version **1.9.0**) are verified in the production environment.
3. **TreeExplainer Production Rejection:** Empirical verification demonstrates that `shap.TreeExplainer` on `sklearn.ensemble.IsolationForest` explains the **average isolation tree traversal depth (path length $h(x)$)** in tree edges, **NOT** the production anomaly-intensity function $f(X) = -\text{decision\_function}(X)$. Because the transformation from path length to anomaly score is nonlinear ($2^{-h/c}$), `TreeExplainer` cannot provide additive explanations for the production anomaly score. **`TreeExplainer` is explicitly rejected as the production anomaly-score explainer.**
4. **Kernel SHAP Methodology:** `shap.KernelExplainer` using the scalar wrapper $f(X) = -\text{decision\_function}(X)$ directly explains continuous anomaly severity with **exact mathematical additivity** ($|f(X) - (\mathbb{E}[f] + \sum \phi_i)| \le 2.78 \times 10^{-17}$). A background set of 50 representative normal training exemplars provides stable, leak-free baseline reference points.
5. **LSTM Autoencoder Boundary:** Sampling-based SHAP on $30 \times 5 = 150$ temporal inputs is **technically unjustified**. The closed-form analytical sequence decomposition from Step 4 (per-sensor MSE, RMSE, and signed physical residuals in original engineering units) is mathematically exact, non-approximated, and instantaneous ($O(1)$). Step 4 Method A is strictly preserved as the canonical temporal explainer.
6. **Provenance & Scaler Corrections:** Prior informal feature aliases (`oil_temperature`, `coolant_pressure`) are retired in favor of the 5 verified production column names: `vibration`, `temperature`, `pressure`, `current`, and `rpm`. The production scaler is verified as `StandardScaler` (fitted with $\mu$ and $\sigma$), correcting earlier textual references to `MinMaxScaler`.
7. **Tree Count & Hash Reconciled:** The serialized model artifact [`ml/models_store/isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib) contains exactly **200 trees** (`n_estimators = 200`, `len(model.estimators_) = 200`), with verified SHA-256 hash `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2`. The earlier 100-tree claim was an informal reference to scikit-learn's default constructor parameter.
8. **Test Suite Reconciled:** The backend test suite contains **51 tests** when targeting `backend/tests/`, and **52 tests** when targeting root/`backend/` (due to `backend/test_connection.py::test_database_connection`). Both target commands pass 100% green.
9. **Empirical Additivity Validated:** Reproducible additivity evidence across 6 development samples (3 normal, 3 anomalous) confirms absolute additivity error $\le 2.78 \times 10^{-17}$, with zero exposure of the held-out test partition.
10. **Audit Recommendation:** **CONDITIONAL GO** — proceed with the modular implementation of the Isolation Forest Kernel SHAP Explainer (`backend/app/ml/shap_explainability/`) following formal user authorization of the audit findings and scope boundaries.

---

## 2. Task 1 — Repository & Dependency Inspection

We conducted a thorough inspection of the repository structure, existing ML modules, model store artifacts, and schema definitions.

### 2.1 File Responsibilities & Existing Components

| File / Directory | Module / Subsystem | Primary Responsibility & Current State |
| :--- | :--- | :--- |
| [`ml/models_store/isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib) | Model Store | Serialized scikit-learn `IsolationForest` ($N=200$ trees, `max_samples=256`, 5 input features, SHA-256: `afdf3973...`). |
| [`ml/models_store/lstm_autoencoder.keras`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/lstm_autoencoder.keras) | Model Store | Serialized Keras LSTM Encoder-Decoder model (reconstruction MSE threshold $\tau = 0.901464$). |
| [`ml/models_store/sensor_scaler.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib) | Model Store | Serialized `StandardScaler` fitted strictly on normal training data (scale parameters: $\sigma \in [0.122, 7.495]$, means: $\mu \in [1.80, 1800.0]$). |
| [`backend/app/ml/isolation_forest/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/isolation_forest/) | Model 1 Pipeline | Training, prediction, threshold calibration, and evaluation scripts for Isolation Forest. |
| [`backend/app/ml/lstm_autoencoder/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/lstm_autoencoder/) | Model 2 Pipeline | Keras functional architecture, sequence batch generator, threshold calibration, and evaluation. |
| [`backend/app/ml/sensor_attribution/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/sensor_attribution/) | Step 4 Attribution | Implements **Method A** (`lstm_attribution.py`: non-negative reconstruction MSE, RMSE, signed physical residuals) and **Method B** (`isolation_forest_attribution.py`: single-feature healthy reference ablation). |
| [`backend/app/models/alert.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/alert.py) | Database Schema | SQLAlchemy ORM model with `shap_json` and `sensor_contrib_json` columns. |
| [`backend/app/schemas/alert.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/schemas/alert.py) | API Schema | Pydantic response schemas validating `shap_json` dictionary structure. |
| [`reports/phase2/failure_risk_feasibility_assessment.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/failure_risk_feasibility_assessment.md) | Step 5 Report | Formal audit report establishing NO-GO on supervised tree risk regression; approved and committed (`e76ea11`). |
| [`backend/requirements.txt`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/requirements.txt) | Dependency Config | Lists `shap>=0.42.0` (installed version is **0.51.0**). |

### 2.2 Existing Step 4 Attribution Mechanism
Step 4 implemented two distinct attribution methodologies:
- **Method A (LSTM Autoencoder):** Evaluates non-negative per-feature reconstruction error $\text{MSE}_c = \frac{1}{T} \sum_{t=1}^T (X_{t, c} - \hat{X}_{t, c})^2$, normalized error percentage $\text{contrib\_pct}_c \ge 0$, and signed physical residuals $R_c = (\bar{X}_c - \bar{\hat{X}}_c) \cdot \sigma_c$ in physical engineering units ($\text{mm/s}, ^\circ\text{C}, \text{bar}, \text{A}, \text{RPM}$).
- **Method B (Isolation Forest Ablation):** Computes feature attribution by perturbing one feature at a time to a healthy reference value: $\Delta_c = \text{Score}(X) - \text{Score}(X_{\text{ablated } c})$.

*Audit Finding:* Step 4 provides exact directional physical residuals for sequence reconstruction. However, Method B (single-feature ablation) does not account for multi-feature interaction effects in tree splits and is not strictly additive. Kernel SHAP provides the cooperative game-theoretic framework to resolve these limitations for tabular anomaly scoring.

---

## 3. Task 2 — Technical Feasibility Analysis

### 3.1 Explainability for Model 1: Isolation Forest

#### Option A: `shap.TreeExplainer` (Path Length Decomposition) — **REJECTED FOR PRODUCTION SCORE**
- **Empirical Behavior:** `TreeExplainer` decomposes average isolation tree depth:
  $$\sum_{j=1}^5 \phi_j^{\text{path}}(x) + \mathbb{E}[h(X)] = h(x)$$
  where $h(x)$ is the average path length across all 200 trees (measured in tree branch edges).
- **Additivity Target:** Additivity holds *only* with respect to $h(x)$, where $\mathbb{E}[h(X)] = 11.8975$.
- **Orientation:** Shorter path length indicates an anomaly (rapid isolation). Therefore, an anomalous feature produces a **negative** SHAP value (reducing search depth).
- **Production Score Incompatibility:** The production anomaly intensity is $f(X) = -\text{decision\_function}(X) = \text{offset\_} + 2^{-\frac{h(X)}{c(n)}}$. Because the exponential function $2^{-x}$ is nonlinear, $\sum \phi_j^{\text{path}} \ne f(X) - \mathbb{E}[f(X)]$.
- **Verdict:** Explicitly rejected as the production anomaly-score explainer. It may only be retained as an optional, secondary diagnostic metric labelled `"isolation_path_length"`.

#### Option B: `shap.KernelExplainer` (Score Function Explanation) — **RECOMMENDED**
- **Mathematical Mechanism:** Wraps the continuous anomaly-intensity function $f(X) = -\text{decision\_function}(X)$ as a black-box scalar scoring function:
  $$\sum_{j=1}^5 \phi_j^{\text{score}}(x) + \mathbb{E}[f(X)] = f(x)$$
- **Interpretation:** Positive $\phi_j^{\text{score}} > 0$ directly indicates that sensor $j$ increased the anomaly score above the healthy baseline expectation. Negative $\phi_j^{\text{score}} < 0$ indicates the sensor anchored the reading toward normal behavior.
- **Additivity Verification:** Empirically verified across development samples to machine precision ($|f(X) - (\mathbb{E}[f] + \sum \phi_i)| \le 2.78 \times 10^{-17}$).
- **Computational Cost:** Evaluates $2^5 = 32$ coalitional subsets. With $N_{\text{bg}} = 50$ background training exemplars, each sample requires 1,600 forward scoring passes (estimated at $\sim 75\text{–}110\text{ ms}$ per sample).

---

### 3.2 Explainability for Model 2: LSTM Autoencoder

We evaluated whether model-agnostic SHAP is technically justified for the LSTM Autoencoder:

#### Feasibility of SHAP for Sequence Autoencoders:
1. **Input Dimensionality:** A sequence window contains $30\text{ timesteps} \times 5\text{ features} = 150\text{ inputs}$.
2. **Combinatorial Explosion:** Running `KernelExplainer` on 150 inputs requires evaluating $2^{150}$ combinations. Even sampling 2,000 coalitions per sequence for 580 test sequences requires over 1.16 million LSTM forward passes, leading to excessive latency.
3. **Temporal Autocorrelation Violation:** Randomly masking individual timesteps disrupts the physical momentum and autocorrelation of the telemetry time series, evaluating the network on unphysical, off-manifold artifacts.
4. **Analytical Exactness of Step 4:** The LSTM reconstruction error is defined as:
   $$\text{MSE}(X, \hat{X}) = \frac{1}{30 \times 5} \sum_{t=1}^{30} \sum_{j=1}^5 (X_{t, j} - \hat{X}_{t, j})^2 = \frac{1}{5} \sum_{j=1}^5 \text{MSE}_j$$
   Because the loss function is **identically and linearly separable across the 5 sensor channels**, the per-feature reconstruction error $\text{MSE}_j$ is **already an exact, non-approximated decomposition** of the anomaly score.

#### Technical Recommendation for LSTM:
- **Do NOT apply sampling-based SHAP to the LSTM Autoencoder.** Introducing a stochastic approximation on top of a closed-form analytical identity introduces sampling noise and compute overhead with zero added explanatory value.
- **Preserve Step 4 Method A:** Retain per-sensor reconstruction MSE, normalized contribution percentage, and signed physical residuals as the canonical temporal sequence explainer.

---

### 3.3 Multi-Sensor Attribution Synergy (SHAP vs. Step 4)

| Dimension | Step 4 Method B (Feature Ablation) | Step 6 SHAP (KernelExplainer) | Step 4 Method A (LSTM Reconstruction) |
| :--- | :--- | :--- | :--- |
| **Target Model** | Isolation Forest | Isolation Forest | LSTM Autoencoder |
| **Mathematical Basis** | Single-variable counterfactual replacement | Cooperative Game Theory (Shapley values) | Closed-form squared error decomposition |
| **Additivity** | Non-additive ($\sum \Delta_c \ne \Delta\text{Score}$) | **Strictly additive** ($\sum \phi_i = f(x) - \mathbb{E}[f]$) | **Strictly additive** ($\sum \text{MSE}_j = 5 \times \text{MSE}$) |
| **Interaction Handling** | Ignores multi-sensor coupling | Averages marginals across all $2^M$ coalitions | Captured in recurrent temporal bottleneck |
| **Attribution Units** | Dimensionless score difference | **Anomaly-score force** ($-\Delta\text{decision\_function}$) | **Non-negative MSE** & **Signed Physical Units** |
| **Computational Cost** | 5 forward passes ($O(M)$) | 32 coalitions ($O(2^M)$) | 1 forward pass ($O(1)$) |

---

## 4. Task 3 — Leakage & Evaluation Audit

### 4.1 Data Partition Boundaries
- **Explainer Calibration & Background Selection:** Strictly restricted to the **Training Partition (steps 0–2799)**, filtered to verified normal operation (`is_anomaly == 0`, $N = 27,200$ rows).
- **Validation Partition (steps 2800–3399):** Used exclusively for verifying background exemplar stability, convergence, and development additivity checks.
- **Untouched Test Partition (steps 3400–3999):** Completely held out. The explainer is frozen prior to evaluating test sequences. Ground-truth test labels (`is_anomaly`) are never used to select explanation parameters.

### 4.2 Background Sample Selection Protocol
- **Centroids vs. Exemplars:**
  - $K$-means centroids represent synthetic arithmetic averages $\mu_k = \frac{1}{|C_k|} \sum x_i$. In multi-sensor telemetry, synthetic centroids can interpolate between physical operating regimes, generating unphysical feature combinations.
  - Actual **exemplar observations** (selected via stratified representative subsampling of normal training data, $N_{\text{bg}} = 50$, 5 per machine) represent physically verified operating states across all 10 machines.
- **Sampling Budget:** With $N_{\text{bg}} = 50$ and $M = 5$, exactly $50 \times 32 = 1,600$ forward passes are executed per explained alert.

### 4.3 Feature Scaling Preservation
- The production scaler is [`ml/models_store/sensor_scaler.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib), verified as an `sklearn.preprocessing.StandardScaler`.
- **Delineation of Four Metric Spaces:**
  1. *Scaled Model-Input Space ($z$):* Standardized $z$-scores ($z = \frac{x - \mu}{\sigma}$).
  2. *Original Engineering Units ($x$):* Physical sensor values ($x = z \cdot \sigma + \mu$, in $\text{mm/s}, ^\circ\text{C}, \text{bar}, \text{A}, \text{RPM}$).
  3. *SHAP Contributions ($\phi_i$):* Measured in **model-output units** (dimensionless anomaly-score intensity delta $\Delta f(X)$). SHAP values are **NOT** physical sensor residuals.
  4. *Step 4 Physical Residuals ($R_c$):* Directional deviations between actual and reconstructed telemetry ($R_c = (z - \hat{z}) \cdot \sigma$, in physical units).

### 4.4 Explanation Stability & Feature Correlation
- **Interventional Masking Assumption:** Standard Kernel SHAP assumes feature independence during feature masking ($p(x_{\bar{S}} | x_S) \approx p(x_{\bar{S}})$).
- **Attribution Distortion:** When sensor features are physically coupled (e.g., motor current and vibration during load surges, $\rho > 0.65$), interventional masking queries the model in unphysical regions of feature space and may split or redistribute credit across correlated features.
- **Behavioral vs. Causal:** SHAP explanations represent **model-behavior attribution** (how the Isolation Forest partitions feature space), **NOT causal proof of physical root cause**. Causal root cause requires Phase 3 multi-agent domain logic, physical rules, and temporal lead-lag analysis.

---

## 5. Task 4 — Proposed Implementation Plan

### 5.1 Architecture & Directory Structure
Step 6 will be implemented as a modular package:
```text
backend/app/ml/shap_explainability/
├── __init__.py                  # Public exports: IsolationForestKernelExplainer, ShapConfig
├── config.py                    # Hyperparameters, background exemplar paths, feature metadata
├── explainer.py                 # Core IsolationForestKernelExplainer (wraps -decision_function)
├── visualize.py                 # Publication-grade waterfall plots and summary beeswarm plots
└── evaluate.py                  # Fleet-wide benchmark, stability testing, and JSON output
```

### 5.2 Attribution Output Schema (`Alert.shap_json`)

Below is the verified production-standard JSON dictionary, instantiated from an actual development evaluation on Machine M104 (step 3100, Validation partition):

```json
{
  "status": "success",
  "machine_id": "M104",
  "step": 3100,
  "timestamp": "2026-11-02 09:00:00",
  "explained_model": "isolation_forest",
  "explained_output": "anomaly_intensity",
  "explainer_method": "kernel_shap",
  "anomaly_score": 0.08656664,
  "base_value": -0.04672914,
  "attribution_units": "dimensionless_anomaly_score_delta",
  "feature_attributions": {
    "vibration": 0.11046788,
    "temperature": 0.05571839,
    "pressure": -0.01067008,
    "current": -0.00713335,
    "rpm": -0.01508705
  },
  "top_contributor": "vibration",
  "share_of_positive_attribution_pct": 66.47,
  "background_samples": 50,
  "computation_time_ms": 78.4,
  "error_message": null
}
```

*Schema Safeguards and Arithmetic Verification:*
- **Mathematical Additivity:**
  $$\text{base\_value} + \sum_{i=1}^5 \phi_i = -0.04672914 + 0.13329578 = 0.08656664 = \text{anomaly\_score}$$
  Additivity error is strictly $0.0$ ($< 10^{-17}$).
- **`share_of_positive_attribution_pct` Definition:**
  Represents the selected positive attribution divided by the sum of all positive attributions, multiplied by 100:
  $$\text{share\_of\_positive\_attribution\_pct} = \frac{\max(0, \phi_{\text{top}})}{\sum_{k=1}^5 \max(0, \phi_k)} \times 100\% = \frac{0.11046788}{0.11046788 + 0.05571839} \times 100\% = 66.47\%$$
  When there are no positive attributions ($\sum \max(0, \phi_k) = 0$, e.g. normal operation where all sensors anchor toward health), this field evaluates strictly to `null`.
- **Status & Error Handling:** The `status` field (`"success"`, `"failed"`, `"unavailable"`) allows downstream agents to distinguish explainer errors from zero attributions.

### 5.3 Local & Global Explanation Strategy
1. **Local Explanations:** For each triggered anomaly, generate a local **Waterfall Plot** illustrating how each sensor drove the anomaly intensity from baseline $\mathbb{E}[f]$ to the triggered score.
2. **Global Explanations:** For the entire test partition, generate a fleet-wide **SHAP Summary Beeswarm Plot** and **Feature Importance Bar Chart**, revealing the global drivers of anomalies across machines.

### 5.4 Test Suite Integration
Implement `backend/tests/test_shap_explainability.py` covering 8 unit tests:
1. Explainer initialization and background exemplar extraction.
2. Additivity verification ($|f(x) - (\mathbb{E}[f] + \sum \phi_i)| < 10^{-6}$).
3. Deterministic execution and seed stability across repeated runs ($\text{CV} \le 1.0\%$).
4. Correct attribution behavior on verified anomalous patterns.
5. Output dictionary compliance with `Alert.shap_json` schema.
6. Execution latency threshold compliance ($< 250\text{ ms}$ per sample).
7. Zero-leakage partition isolation check (zero test-set exposure during calibration).
8. Scaler parameter validation (StandardScaler $\mu, \sigma$ integrity).

---

## 6. Implementation Sequence

```mermaid
flowchart LR
    P1["1. Implement config.py & explainer.py"] --> P2["2. Build visualize.py & evaluate.py"]
    P2 --> P3["3. Develop test_shap_explainability.py (8 tests)"]
    P3 --> P4["4. Run fleet evaluation on untouched test set"]
    P4 --> P5["5. Generate graphs & shap_explainability_report.md"]
```

---

## 7. Current Git State & Integrity Verification

```text
$ git status
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	reports/phase2/shap_explainability_inspection_plan.md

nothing added to commit but untracked files present (use "git add" to track)
```

- **Branch:** `main` (synchronized with `origin/main` at commit `e76ea11`).
- **Workspace:** Clean; only the single approved inspection plan file is untracked.
- **Model Files:** [`isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib), [`lstm_autoencoder.keras`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/lstm_autoencoder.keras), [`sensor_scaler.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib) untouched.
- **Database & Data:** SQLite `manumind.db`, Supabase cloud records, and CSV/NPZ partitions untouched.
- **Completed Steps 0–5:** Fully preserved and unaffected.

---

## 8. Final Recommendation & Audit Sign-off

### Recommendation: **CONDITIONAL GO**

#### Conditions Required Before Execution:
1. **Scope Boundary Approved:** Approval to restrict Step 6 implementation to the **Isolation Forest Kernel SHAP Explainer** (wrapping continuous anomaly intensity $f(X) = -\text{decision\_function}(X)$), while formally preserving Step 4 Method A as the canonical temporal sequence explainer for the LSTM Autoencoder.
2. **TreeExplainer Rejection Acknowledged:** Formal acknowledgment that `shap.TreeExplainer` is rejected as the production anomaly-score explainer due to mathematical incompatibility with continuous anomaly score $f(X)$.
3. **Background Calibration Protocol Approved:** Approval to extract background baseline exemplars ($N_{\text{bg}} = 50$) strictly from the verified normal training partition (`scaled_sensor_train.csv` / `is_anomaly == 0`), ensuring zero leakage from validation or test partitions.
4. **Database Schema Compliance:** Approval of the revised `Alert.shap_json` output schema with `share_of_positive_attribution_pct`.

---

## 9. Independent Technical Audit Corrections — Phase 2 Step 6

This section documents the formal resolution of all 10 technical audit items raised during the independent audit review of Step 6.

### 9.1 Item 1: TreeExplainer Compatibility Evidence

#### Environment & Model Verification:
- **Python Version:** 3.11
- **scikit-learn Version:** `1.9.0`
- **SHAP Version:** `0.51.0`
- **Model Artifact:** [`ml/models_store/isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib) (`sklearn.ensemble._iforest.IsolationForest`, `n_estimators = 200`, `max_samples_ = 256`, `n_features_in_ = 5`).

#### Empirical Compatibility Test:
`shap.TreeExplainer(if_model)` initializes successfully. However, empirical inspection reveals:
1. **Target Quantity:** `TreeExplainer` explains the **average isolation tree traversal depth (path length $h(x)$)** across all 200 trees, including the leaf termination adjustment $c(n_{\text{node}})$:
   $$\mathbb{E}[h(x)] = \frac{1}{200} \sum_{t=1}^{200} \left( \text{depth}_t(x) + c(n_{\text{leaf}}) \right)$$
   For test evaluation points, the reconstructed output $\mathbb{E}[h(X)] + \sum \phi_i^{\text{path}}$ matched the direct scikit-learn isolation path length exactly:
   - Sample 0 (Normal): Reconstructed $= 14.43703891$, Exact Path Length $= 14.43703891$
   - Sample 1 (Vibration): Reconstructed $= 10.11423549$, Exact Path Length $= 10.11423549$
   - Sample 2 (Overheating): Reconstructed $= 9.33937938$, Exact Path Length $= 9.33937938$
   - Sample 3 (Pressure/Current): Reconstructed $= 8.15559701$, Exact Path Length $= 8.15559701$
2. **Additivity Target:** Additivity holds *only* against average path length $h(x)$, with base value $\mathbb{E}[h(X)] = 11.8974779$ (tree depth in edges).
3. **Directionality Inversion:** Shorter path length indicates faster isolation (higher anomaly severity). Thus, anomalous features yield **negative** path-length SHAP values (reducing depth).
4. **Production Score Incompatibility:**
   The production anomaly-intensity function is:
   $$f(X) = -\text{model.decision\_function}(X) = \text{offset\_} + 2^{-\frac{h(X)}{c(n)}}$$
   Because $2^{-x}$ is a nonlinear exponential transformation, the linear sum of path-length SHAP values **cannot** reconstruct $f(X)$:
   $$\sum_{i=1}^5 \phi_i^{\text{path}}(X) + \mathbb{E}[f(X)] \ne f(X)$$
   For Sample 0, path length is $14.437$ edges, while $f(X) = -0.1235$. For Sample 3, path length is $8.156$ edges, while $f(X) = +0.0759$.
5. **Audit Decision:** **`TreeExplainer` is EXPLICITLY REJECTED as the production anomaly-score explainer.** It cannot explain continuous anomaly score $f(X)$. Path length may only be retained as an optional secondary diagnostic metric.

---

### 9.2 Item 2: Kernel SHAP Methodology & Limitations

#### Exact Scalar Prediction Wrapper:
```python
def anomaly_intensity_wrapper(X: np.ndarray) -> np.ndarray:
    """
    Production Anomaly Intensity Wrapper for Isolation Forest.
    Higher output strictly denotes greater anomaly intensity.
    Nominal / healthy operation: f(X) < 0 (typically -0.15 to -0.05).
    Threshold boundary: f(X) ≈ 0.0.
    Severe anomaly: f(X) > 0 (up to +0.35).
    """
    return -if_model.decision_function(X)
```

#### Background Distribution & Terminology Correction:
- **Centroids vs. Medoids / Exemplars:**
  - *Centroids ($K$-means):* Arithmetic averages of feature clusters. They are synthetic points that do not represent real machine states and can interpolate across operating regimes.
  - *Exemplars / Medoids:* Real, physically recorded observations from healthy machines.
- **Selection Protocol:** To avoid unphysical synthetic combinations, the production background will draw **$N_{\text{bg}} = 50$ real telemetry exemplars** from the training partition (`data/processed/scaled_sensor_train.csv`, filtered by `is_anomaly == 0`), stratified across all 10 machines (5 nominal readings per machine).
- **Sampling Budget & Masking:**
  - With $M = 5$ sensor channels, the full coalition space is $2^5 = 32$. Setting `nsamples = 32` allows evaluating the complete coalition lattice.
  - Evaluation passes per alert: $50 \times 32 = 1,600$ forward passes.
  - Masking mechanism: Interventional marginal replacement ($x_{\bar{S}} \sim p(X_{\text{bg}})$).
- **Additivity Verification:** Empirically verified across development samples to machine precision:
  $$|f(X) - (\text{explainer.expected\_value} + \sum \phi_i)| \le 2.78 \times 10^{-17}$$

---

### 9.3 Item 3: Feature-Correlation Limitations

#### Revision of Previous Claim:
The previous claim that "Shapley averaging handles sensor correlation" is formally revised.

#### Methodological Limitations:
1. **Interventional Independence Assumption:** Standard Kernel SHAP assumes that features are independent during masking ($p(x_{\bar{S}} | x_S) \approx p(x_{\bar{S}})$).
2. **Off-Manifold Sampling:** When features are physically coupled (e.g., motor current and shaft vibration, $\rho > 0.65$; or pump pressure and fluid temperature), interventional masking samples feature values independently from the background, creating synthetic evaluations outside the physical operating manifold of the equipment.
3. **Credit Redistribution:** When two features are correlated and co-occur in tree splits, Shapley attribution splits credit between them. If the ensemble splits on `vibration` in 55% of trees and `current` in 45% of trees, both features receive comparable attribution, which can obscure which sensor was the physical initiator of the fault.
4. **Causal Boundary:** SHAP explanations represent **model-behavior attributions** (how the Isolation Forest scoring function partitions feature space). They do **NOT** constitute causal evidence of physical root cause. Physical root cause requires Phase 3 multi-agent domain logic, physical equations, and temporal lead-lag analysis.

---

### 9.4 Item 4: Scaler & Engineering-Unit Claims

#### Model Scaler Inspection:
Inspection of [`ml/models_store/sensor_scaler.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib) confirms:
- **Class:** `sklearn.preprocessing._data.StandardScaler` (NOT `MinMaxScaler`).
- **Fitted Parameters:**
  - `mean_` ($\mu$): `[1.80459579, 47.99805036, 6.20172929, 14.52517214, 1799.94745]`
  - `scale_` ($\sigma$): `[0.22664751, 2.19574850, 0.12222276, 0.71113453, 7.49504460]`
  - `var_` ($\sigma^2$): `[0.05136909, 4.82131146, 0.01493840, 0.50571232, 56.17569350]`

#### Inverse Transformation Formulas:
- **StandardScaler (Actual Production Pipeline):**
  $$z_j = \frac{x_j - \mu_j}{\sigma_j} \iff x_j = z_j \cdot \text{scale\_}[j] + \text{mean\_}[j]$$
- **MinMaxScaler (Theoretical Reference for Completeness):**
  If a `MinMaxScaler` had been utilized, the transformation would be:
  $$x_{\text{scaled}} = x_{\text{orig}} \cdot \text{scale\_} + \text{min\_} \iff x_{\text{orig}} = \frac{x_{\text{scaled}} - \text{min\_}}{\text{scale\_}}$$
  where $\text{scale\_} = \frac{1}{\text{data\_max} - \text{data\_min}}$ and $\text{min\_} = -\frac{\text{data\_min}}{\text{data\_max} - \text{data\_min}}$.

#### Delineation of Four Distinct Metric Spaces:
1. **Scaled Model-Input Space ($z$):** Standardized dimensionless inputs ($z \in \mathbb{R}$, zero mean, unit variance).
2. **Physical Engineering Units ($x$):** Physical sensor telemetry ($x = z \cdot \sigma + \mu$, in $\text{mm/s}, ^\circ\text{C}, \text{bar}, \text{A}, \text{RPM}$).
3. **SHAP Attribution Values ($\phi_i$):** Dimensionless units of anomaly score intensity delta ($\Delta f(X)$). SHAP values are **NOT** physical sensor residuals.
4. **Step 4 Physical Residuals ($R_c$):** Signed directional reconstruction errors ($R_c = (z - \hat{z}) \cdot \sigma$, in physical units).

---

### 9.5 Item 5: Verified Sensor Feature Names

Inspection of [`backend/app/ml/preprocessing/sensor_preprocessing.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/preprocessing/sensor_preprocessing.py) and [`data/raw/sensor_readings.csv`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/data/raw/sensor_readings.csv) confirms the exact production feature order:

| Index | Feature Name | Physical Engineering Unit | Nominal Mean ($\mu$) | Nominal Std ($\sigma$) |
| :---: | :--- | :---: | :---: | :---: |
| 0 | `vibration` | $\text{mm/s}$ | $1.8046$ | $0.2266$ |
| 1 | `temperature` | $^\circ\text{C}$ | $47.9981$ | $2.1957$ |
| 2 | `pressure` | $\text{bar}$ | $6.2017$ | $0.1222$ |
| 3 | `current` | $\text{A}$ | $14.5252$ | $0.7111$ |
| 4 | `rpm` | $\text{RPM}$ | $1799.9475$ | $7.4950$ |

*Correction of Narrative Aliases:* Terms such as `oil_temperature`, `coolant_pressure`, and `coolant_temp` were informal domain scenario descriptions. They do not exist in the dataset or model. All Step 6 code, JSON schemas, and documentation must strictly use the 5 verified production column names.

---

### 9.6 Item 6: Fault-Attribution Experiment Provenance

#### Provenance Audit:
The initial inspection report cited attribution percentages for benchmark machines M102 (pressure/temp), M104 (vibration), M107 (pressure/current), and M109 (vibration/current).
- **Audit Finding:** These values originated from exploratory in-memory scratch tests using single synthetic prototype vectors ($N=1$ per fault mode). They were **NOT** generated from a systematic execution over actual dataset partitions.
- **Classification:** These exploratory results are formally reclassified as **UNVERIFIED EXPLORATORY TOY TESTS** and are retracted as claims of validated attribution accuracy.
- **Protection of Test Partition:** The untouched test partition (`scaled_sensor_test.csv`, synthetic steps 3400–3999) remains strictly held out. Validated attribution accuracy will only be evaluated during the formal Step 6 evaluation phase.

---

### 9.7 Item 7: Runtime Evidence Classification

The latency numbers presented in the initial inspection report:
- `TreeExplainer`: $< 1.0\text{ ms}$ per sample
- `KernelExplainer`: $\approx 85\text{–}120\text{ ms}$ per sample
- Step 4 LSTM attribution: $\approx 0.4\text{ ms}$ per sample

#### Audit Reclassification:
These figures were preliminary estimates observed during exploratory single-pass executions. They are formally classified as **preliminary exploratory estimates**, not verified benchmarks. Rigorous benchmarking (documenting CPU/GPU hardware, batch sizes, warm-up runs, sample counts, and 95th-percentile latencies) will be conducted upon approved implementation.

---

### 9.8 Item 8: Step 4 Attribution Mathematical Clarification

Inspection of [`backend/app/ml/sensor_attribution/lstm_attribution.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/sensor_attribution/lstm_attribution.py) clarifies the mathematical distinction between error attribution and residuals:
1. **Squared Reconstruction-Error Contribution (strictly non-negative):**
   $$\text{MSE}_c = \frac{1}{T} \sum_{t=1}^T (X_{t, c} - \hat{X}_{t, c})^2 \ge 0, \quad \text{contrib\_pct}_c = \frac{\text{MSE}_c}{\sum_{k=1}^5 \text{MSE}_k} \times 100\% \in [0, 100]\%$$
   Measures the magnitude of reconstruction failure for sensor $c$.
2. **Signed Physical Residuals:**
   $$R_c = \left( \frac{1}{T} \sum_{t=1}^T (X_{t, c} - \hat{X}_{t, c}) \right) \cdot \sigma_c$$
   Measures the directional physical bias in engineering units. A positive residual indicates actual telemetry exceeded nominal model reconstruction; a negative residual indicates actual telemetry dropped below nominal.
3. **Correction:** Squared-error contributions are strictly non-negative and must never be described as "signed".
4. **Preservation:** Step 4 remains untouched as the canonical LSTM sequence explanation method.

---

### 9.9 Item 9: Reassessment of Proposed Architecture & JSON Schema

The proposed `Alert.shap_json` payload is updated to guarantee rigorous interpretation:
```json
{
  "status": "success",
  "machine_id": "M104",
  "step": 3100,
  "timestamp": "2026-11-02 09:00:00",
  "explained_model": "isolation_forest",
  "explained_output": "anomaly_intensity",
  "explainer_method": "kernel_shap",
  "anomaly_score": 0.08656664,
  "base_value": -0.04672914,
  "attribution_units": "dimensionless_anomaly_score_delta",
  "feature_attributions": {
    "vibration": 0.11046788,
    "temperature": 0.05571839,
    "pressure": -0.01067008,
    "current": -0.00713335,
    "rpm": -0.01508705
  },
  "top_contributor": "vibration",
  "share_of_positive_attribution_pct": 66.47,
  "background_samples": 50,
  "computation_time_ms": 78.4,
  "error_message": null
}
```
- **Attribution Units & Directions:** Units are explicitly declared as dimensionless anomaly score delta. For Kernel SHAP on $f(X)$, positive values indicate features that pushed the sample toward anomaly, while negative values indicate features anchoring the sample toward normality.
- **`share_of_positive_attribution_pct` Guard:** Calculated strictly over positive contributions: $\frac{\max(0, \phi_i)}{\sum_k \max(0, \phi_k)} \times 100\%$. If all $\phi_k \le 0$, the percentage is returned as `null` to avoid division by zero or nonsensical percentages.
- **Status & Error Handling:** The `status` field (`"success"`, `"failed"`, `"unavailable"`) distinguishes explainer failures from zero attributions.

---

### 9.10 Item 10: Revised Implementation Recommendation

### Final Recommendation: **CONDITIONAL GO**

#### Supporting Evidence:
1. **TreeExplainer Formally Rejected for Production Score:** Empirical proof confirms TreeExplainer decomposes isolation tree depth ($h(x)$), not continuous anomaly score $f(X) = -\text{decision\_function}(X)$. It cannot provide additive anomaly-score explanations.
2. **KernelExplainer Validated for Production Score:** Kernel SHAP on $f(X)$ satisfies exact mathematical additivity (error $\le 2.78 \times 10^{-17}$) and operates within an acceptable computational budget ($50 \times 32 = 1,600$ evaluations, $\sim 85\text{ ms}$).
3. **Step 4 Sequence Attribution Preserved:** Model-agnostic SHAP on $30 \times 5$ LSTM sequences is technically unjustified; Step 4 Method A is mathematically exact and preserved as canonical.
4. **Data Integrity & Scaler Verified:** The production scaler is confirmed as `StandardScaler` with exact parameters, and feature names are verified as `["vibration", "temperature", "pressure", "current", "rpm"]`.
5. **Zero Data Leakage:** Explainer background selection ($N_{\text{bg}} = 50$ real exemplars) is strictly confined to normal training telemetry (`is_anomaly == 0`), leaving the test partition completely untouched.

---

## 10. Final Pre-Implementation Verification & Reconciliation

This section documents the formal resolution of the final three verification issues and provides reproducible development additivity evidence.

### 10.1 SHAP JSON Additivity Correction & Field Renaming

#### Previous Discrepancy:
The illustrative JSON schema in previous drafts contained an arithmetic inconsistency:
- Documented `base_value` $= -0.0356$
- Documented feature attribution sum $\sum \phi_i = 0.2773$
- Documented `anomaly_score` $= 0.2007$
- Arithmetic check: $\text{base\_value} + \sum \phi_i = -0.0356 + 0.2773 = 0.2417 \ne 0.2007$.

#### Resolution & Ground-Truth Instantiation:
The illustrative placeholder has been replaced with an actual verified development sample from Machine M104 (step 3100, Validation partition):
- `base_value`: $-0.04672914$
- Individual SHAP attributions:
  - `vibration`: $+0.11046788$
  - `temperature`: $+0.05571839$
  - `pressure`: $-0.01067008$
  - `current`: $-0.00713335$
  - `rpm`: $-0.01508705$
- Reconstructed sum: $-0.04672914 + 0.13329578 = 0.08656664$
- Target output $f(X) = -\text{decision\_function}(X) = 0.08656664$
- Absolute additivity error: **$0.0$ ($< 10^{-17}$)**.

#### Field Renaming: `share_of_positive_attribution_pct`:
The field previously labelled `top_contributor_percentage` is formally renamed to:
`share_of_positive_attribution_pct`

**Definition:**
$$\text{share\_of\_positive\_attribution\_pct} = \frac{\max(0, \phi_{\text{top}})}{\sum_{k=1}^5 \max(0, \phi_k)} \times 100\%$$
- Represents the selected dominant feature's positive attribution divided by the sum of all positive attributions, scaled to a percentage.
- **Null Rule:** When all feature attributions are non-positive ($\sum \max(0, \phi_k) = 0$, indicating healthy baseline operation where all sensors push toward normal), this field evaluates strictly to `null`.
- **Database Schema Integrity:** This change affects only the JSON payload contents serialized into the existing `Alert.shap_json` column. The database schema itself remains completely untouched.

---

### 10.2 Isolation Forest Tree Count Reconciliation & Artifact Hash

An exhaustive inspection of the saved model artifact [`ml/models_store/isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib) yields the following verified parameters:

| Parameter | Inspected Value | Description / Verification |
| :--- | :--- | :--- |
| **Model Class** | `<class 'sklearn.ensemble._iforest.IsolationForest'>` | Native scikit-learn Isolation Forest ensemble |
| **`n_estimators`** | `200` | Configured estimator count |
| **`len(model.estimators_)`** | `200` | Actual fitted tree instances in memory |
| **`max_samples_`** | `256` | Subsample size per isolation tree |
| **Input Features** | `5` (`n_features_in_ = 5`) | `vibration`, `temperature`, `pressure`, `current`, `rpm` |
| **File SHA-256 Hash** | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | Cryptographic signature verifying artifact immutability |

#### Reconciliation of the 100-Tree Claim:
- In the initial Step 6 report, the model was casually referred to as containing "100 trees".
- **Source of Error:** 100 is the default parameter value for `n_estimators` in `sklearn.ensemble.IsolationForest`. The author of the initial draft made an unverified assumption based on default scikit-learn settings without inspecting the repository artifacts.
- **Actual Architecture:** During Phase 2 Step 1, the model training pipeline ([`backend/app/ml/isolation_forest/train.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/isolation_forest/train.py)) and configuration ([`backend/app/ml/isolation_forest/config.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/isolation_forest/config.py)) explicitly set `n_estimators = 200` and `max_samples = 256` (documented in `ml/models_store/isolation_forest_metadata.json`).
- **Conclusion:** The model artifact contains exactly 200 trees and has never been modified, retrained, or re-serialized. Its SHA-256 hash confirms complete immutability.

---

### 10.3 Test Suite Count Reconciliation

#### Investigation Findings:
Pytest test discovery behaves differently depending on the targeted directory path:

1. **Targeting `backend/tests/`:**
   ```bash
   python -m pytest backend/tests -q
   ```
   - **Collected:** **51 tests** across 6 test modules:
     - `test_isolation_forest.py`: 10 tests
     - `test_lstm_autoencoder.py`: 10 tests
     - `test_phase1_audit_and_expansion.py`: 9 tests
     - `test_phase1_db_and_generator.py`: 4 tests
     - `test_sensor_attribution.py`: 10 tests
     - `test_sensor_preprocessing.py`: 8 tests
   - **Results:** **51 passed, 0 failed, 0 skipped** (100% pass rate).

2. **Targeting `backend/` or Repository Root (`.`):**
   ```bash
   python -m pytest backend -q
   # or
   python -m pytest . -q
   ```
   - **Collected:** **52 tests**.
   - **Additional Test:** Pytest's default file matching pattern `test_*.py` discovers [`backend/test_connection.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/test_connection.py), which defines `test_database_connection` (a diagnostic utility verifying SQLAlchemy database connectivity).
   - **Results:** **52 passed, 0 failed, 0 skipped** (100% pass rate).

#### Reconciliation Summary:
- Both numbers are accurate reflections of their respective invocation scopes:
  - Scope `backend/tests/`: Exactly 51 unit and integration test functions.
  - Scope `backend/` / Root: Exactly 52 tests ($51 + 1$ connection diagnostic test).
- Zero tests have been deleted, modified, or altered. The full test suite remains 100% green.

---

### 10.4 Reproducible Kernel SHAP Additivity Evidence

Using **strictly permitted development data** (Validation partition: steps 2800–3399; Training partition for background exemplars: steps 0–2799), we executed Kernel SHAP using $N_{\text{bg}} = 50$ normal training exemplars (5 per machine, stratified across M101–M110) and full coalition lattice evaluation ($n_{\text{samples}} = 32$).

The baseline expectation across all 50 background exemplars is:
$$\mathbb{E}[f(X)] = -0.04672914$$

The table below presents the exact empirical results for three normal samples and three anomalous samples:

| Sample Label | Machine ID | Split & Step | Timestamp | Target $f(X)$ | SHAP $\phi_{\text{vib}}$ | SHAP $\phi_{\text{temp}}$ | SHAP $\phi_{\text{press}}$ | SHAP $\phi_{\text{curr}}$ | SHAP $\phi_{\text{rpm}}$ | Reconstructed $f(X)$ | Absolute Error | `share_pos_pct` (Top Feature) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Normal 1** | M101 | Val: 3000 | 2026-11-02 00:40:00 | $-0.07493359$ | $-0.00941131$ | $+0.00414862$ | $-0.00674184$ | $-0.00213151$ | $-0.01406841$ | $-0.07493359$ | **$0.0$** | 100.0% (`temp`) |
| **Normal 2** | M103 | Val: 3100 | 2026-11-02 09:00:00 | $-0.00246802$ | $+0.02460251$ | $-0.01153224$ | $+0.01548147$ | $-0.00811131$ | $+0.02382069$ | $-0.00246802$ | **$6.94 \times 10^{-18}$** | 38.50% (`vib`) |
| **Normal 3** | M105 | Val: 3200 | 2026-11-02 17:20:00 | $-0.08810809$ | $-0.01320929$ | $-0.00034734$ | $-0.00506660$ | $-0.00866008$ | $-0.01409564$ | $-0.08810809$ | **$0.0$** | **`null`** (all $\le 0$) |
| **Anomalous 1** (Overheating) | M102 | Val: 3000 | 2026-11-02 00:40:00 | $+0.01945369$ | $-0.00914026$ | $+0.07105752$ | $+0.00935203$ | $-0.00187398$ | $-0.00321247$ | $+0.01945369$ | **$6.94 \times 10^{-18}$** | 88.37% (`temp`) |
| **Anomalous 2** (Bearing Wear) | M104 | Val: 3100 | 2026-11-02 09:00:00 | $+0.08656664$ | $+0.11046788$ | $+0.05571839$ | $-0.01067008$ | $-0.00713335$ | $-0.01508705$ | $+0.08656664$ | **$0.0$** | 66.47% (`vib`) |
| **Anomalous 3** (Pressure Drop) | M107 | Val: 3200 | 2026-11-02 17:20:00 | $+0.12497569$ | $+0.02816664$ | $-0.00716757$ | $+0.08019389$ | $+0.08479521$ | $-0.01428334$ | $+0.12497569$ | **$2.78 \times 10^{-17}$** | 43.90% (`curr`) |

#### Key Analytical Observations:
1. **Machine Precision Additivity:** In all 6 cases, the reconstructed anomaly score matches $f(X) = -\text{decision\_function}(X)$ with absolute error bounded by $2.78 \times 10^{-17}$ (essentially floating-point zero).
2. **Physical Alignment on Validation Anomalies:**
   - For M102 (overheating), `temperature` receives 88.37% of positive attribution.
   - For M104 (bearing wear), `vibration` receives 66.47% and `temperature` receives 33.53% of positive attribution.
   - For M107 (pressure drop), `current` (43.90%) and `pressure` (41.52%) dominate positive attribution.
3. **Null Handling on Normal 3:** In Normal 3 (M105, step 3200), all five sensors exhibit negative SHAP values, reflecting healthy operation. The `share_of_positive_attribution_pct` evaluates cleanly to `null`, avoiding division by zero or nonsensical percentages.
4. **Test Set Protection:** The entire test partition (`scaled_sensor_test.csv`, synthetic steps 3400–3999) remained completely untouched during these verification runs.

---

### 10.5 Final Pre-Implementation Recommendation & Audit Sign-Off

### Final Recommendation: **CONDITIONAL GO**

#### Summary of Supporting Evidence:
- **Additivity Confirmed:** Kernel SHAP on $f(X) = -\text{decision\_function}(X)$ is mathematically exact to machine precision ($10^{-17}$).
- **Artifacts Verified:** Isolation Forest has 200 fitted estimators with verified SHA-256 hash `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2`.
- **Test Suite Reconciled:** 51 tests inside `backend/tests/` and 52 tests including `backend/test_connection.py` are 100% green.
- **Zero Leakage Preserved:** Calibration uses strictly normal training exemplars; test partition remains completely untouched.

#### Outstanding Condition Awaiting Authorization:
- Explicit user authorization to begin code implementation of Phase 2 Step 6 (`backend/app/ml/shap_explainability/`).

*This concludes the Final Pre-Implementation Verification. Stopped and awaiting explicit approval before implementing Step 6.*
