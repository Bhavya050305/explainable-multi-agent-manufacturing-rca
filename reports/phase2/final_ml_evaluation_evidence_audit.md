# ManuMind AI — Phase 2 Step 10A: Final ML Evaluation Evidence Audit Report

**Role:** Senior ML Evaluation Engineer, Research Auditor, and Technical Documentation Specialist  
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Academic Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Current HEAD:** `13fd0141a24c24e9e9267881e0f37672f0b114ca`  
**Milestone:** Phase 2 Step 10A — Final ML Evaluation Evidence Audit  
**Date of Audit:** November 8, 2026  
**Mode:** Independent Read-Only Evidence Consolidation & Technical Audit  

---

## 1. Executive Evaluation Summary

This evidence audit establishes the forensic empirical foundation for the formal Phase 2 Final Machine Learning Evaluation Report. It consolidates, reconciles, and methodologically evaluates all quantitative performance metrics, architectural benchmarks, diagnostic audits, and feasibility determinations produced across Phase 2 (Steps 1 through 9).

The primary objective of this audit is to enforce scientific integrity by maintaining strict boundaries between:
1. **Empirical test-set measurements** (point-level, sequence-level, and image-level metrics).
2. **Synthetic data demonstrations** (behavioral consistency with programmed equations vs. physical truth).
3. **Engineering benchmarks** (local workstation latency and memory under single-process test harnesses).
4. **Feasibility decisions** (the formal Step 5 NO-GO determination for tree-based supervised failure-risk prediction).
5. **Software regression testing** (Pytest contract validation vs. statistical generalization).
6. **Unresolved technical limitations** (including DEFECT-01 in input schema validation).

```text
========================================================================================
AUDIT STATUS:
EVIDENCE AUDIT COMPLETE — READY FOR FINAL REPORT
========================================================================================
```

---

## 2. Evidence Inventory & Artifact Provenance

Every numerical claim in this audit has been traced directly to existing repository artifacts, evaluation JSON files, or historical reports:

| Source ID | Primary File Path | Primary Component / Scope | Verified Content & Provenance |
| :---: | :--- | :--- | :--- |
| **SRC-01** | [`reports/phase2/isolation_forest/isolation_forest_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/isolation_forest/isolation_forest_results.json) | Isolation Forest Point-Level Anomaly Detection | Global confusion matrix (3359 TN, 241 FP, 0 FN, 2400 TP), ROC-AUC (0.9979), PR-AUC (0.9965), threshold (0.0269), and 10-machine breakdown on 6,000 test points. |
| **SRC-02** | [`reports/phase2/lstm_autoencoder/lstm_autoencoder_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/lstm_autoencoder/lstm_autoencoder_results.json) | LSTM Autoencoder Sequence Anomaly Detection | Sequence-level confusion matrix (344 TN, 4 FP, 0 FN, 232 TP), threshold (0.901464), ROC-AUC (1.0000), PR-AUC (1.0000), and breakdown across 580 sequence windows. |
| **SRC-03** | [`reports/phase2/evaluation_audit/common_granularity_comparison.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/common_granularity_comparison.json) | Granularity Harmonization & Window Aggregation | Direct comparison of IF aggregated over 30-timestep windows (mean, max, fraction) vs. LSTM Autoencoder on identical 580 sequence windows. |
| **SRC-04** | [`reports/phase2/sensor_attribution/fault_mechanism_consistency.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/fault_mechanism_consistency.json) | Sensor-Level Anomaly Attribution | Dominant feature mode matches (100% on M102, M104, M107, M109), contribution percentages, and signed standardized residuals. |
| **SRC-05** | [`reports/phase2/failure_risk_feasibility_assessment.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/failure_risk_feasibility_assessment.md) | Failure-Risk Prediction Feasibility (Step 5) | Technical audit documenting the formal NO-GO decision, mathematical convex hull bounds, input truncation, and pseudoreplication. |
| **SRC-06** | [`reports/phase2/shap_explainability/shap_evaluation_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/shap_explainability/shap_evaluation_results.json) | Kernel SHAP Sensor Explainability | 50 normal validation background samples, additive efficiency metrics ($\max \text{error} = 5.55 \times 10^{-17}$), and latency distribution on 70-sample cohort. |
| **SRC-07** | [`reports/phase2/defect_classifier/defect_classifier_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/defect_classifier/defect_classifier_results.json) | ResNet Vision Defect Classifier | 4-class confusion matrix, 100% test accuracy/F1 across 92 test images, per-class ROC curves, and CPU latency benchmarks. |
| **SRC-08** | [`ml/models_store/resnet_defect_classifier_metadata.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/resnet_defect_classifier_metadata.json) | ResNet Architectural & Training Metadata | 2,804,708 total parameters (Compact ResNet-18), 35-epoch training history, input dimensions (128x128x3), and SHA-256 digest (`aac4b1c2...`). |
| **SRC-09** | [`reports/phase2/inference_service_eval_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/inference_service_eval_results.json) | Unified Multimodal Inference Service Integration | Direct-model vs. service numerical parity ($< 10^{-6}$), latency distributions across 100 iterations, and concurrency lock verification. |
| **SRC-10** | [`reports/phase2/comprehensive_ml_validation_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/comprehensive_ml_validation_results.json) | Comprehensive ML Regression Validation | 118-test regression inventory, multimodal pairwise routing, fuzzing results, tracemalloc telemetry, and frozen partition quarantine. |
| **SRC-11** | [`reports/phase2/resnet_metadata_hash_provenance_audit.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/resnet_metadata_hash_provenance_audit.md) | Protected Artifact Hash Provenance Verification | Read-only audit resolving historical Step 7 clerical hash discrepancy and verifying immutable on-disk SHA-256 digest (`e7e95b80...`). |

---

## 3. Comprehensive Evidence Reconciliation Table

The following structured matrix compares all evaluated models, components, evaluation units, scopes, key metrics, and fundamental limitations across Phase 2:

| Model / Component | Evaluation Unit | Dataset & Scope | Key Performance Metrics | Primary Evidence Source | Critical Methodological Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Isolation Forest** (Model 1) | Individual sensor reading ($1 \times 5$ tabular point) | Frozen test partition (`sensor_test.csv`): 6,000 points (10 machines $\times$ 600 readings) | • **Accuracy:** 0.9598<br>• **Precision:** 0.9087<br>• **Recall:** 1.0000<br>• **F1:** 0.9522<br>• **ROC-AUC:** 0.9979<br>• **PR-AUC:** 0.9965<br>• **Specificity:** 0.9331<br>• **Threshold:** 0.0269 | `reports/phase2/isolation_forest/isolation_forest_results.json` | Evaluated strictly on synthetic data where fault amplitudes exceed 15–39$\sigma$. Point-level evaluation incurs a 6.69% false alarm rate (241 FP) on nominal baseline readings due to transient Gaussian tail excursions. Zero-shot holdout recall drops to 48.86%–76.14% on unseen machines. |
| **LSTM Autoencoder** (Model 2) | Sequence window ($30 \times 5$ tensor, 150 min, stride 10) | Frozen test partition (`sequences_test.npz`): 580 windows (10 machines $\times$ 58 windows) | • **Accuracy:** 0.9931<br>• **Precision:** 0.9831<br>• **Recall:** 1.0000<br>• **F1:** 0.9915<br>• **ROC-AUC:** 1.0000<br>• **PR-AUC:** 1.0000<br>• **Specificity:** 0.9885<br>• **Threshold:** 0.901464 | `reports/phase2/lstm_autoencoder/lstm_autoencoder_results.json` | Sequence windows overlap by 20 timesteps (stride 10, window 30), violating statistical sample independence across consecutive evaluation windows. Sequence-level metrics cannot be directly compared to point-level Isolation Forest metrics without temporal aggregation. |
| **Granularity Harmonization** | Harmonized sequence window ($30 \times 5$ tensor, $N=580$) | Exact same 580 sequence windows evaluated across both models | • **IF (Mean Score):** Acc 1.0, F1 1.0, FP 0<br>• **IF (Max Score):** Acc 0.9845, F1 0.9810, FP 9<br>• **IF (Fraction):** Acc 1.0, F1 1.0, FP 0<br>• **LSTM Autoencoder:** Acc 0.9931, F1 0.9915, FP 4 | `reports/phase2/evaluation_audit/common_granularity_comparison.json` | Proves that the apparent accuracy gap between IF (0.9598) and LSTM (0.9931) was primarily an artifact of evaluation granularity (point vs. sequence). Aggregating IF points over 30-step windows reduces false alarms from 241 to 0–9. |
| **Sensor Attribution** | Feature attribution percentage & signed standardized residual | 58 anomalous windows per faulted machine ($N=232$ anomalous windows) | • **M102 (Overheat):** Temp 61.98% ($+13.35\sigma$)<br>• **M104 (Bearing):** Vib 88.00% ($+23.37\sigma$)<br>• **M107 (Pressure):** Press 91.34% ($-21.50\sigma$)<br>• **M109 (Lubrication):** Curr 44.69% ($+14.15\sigma$)<br>• **Mode Match:** 100% across all 4 | `reports/phase2/sensor_attribution/fault_mechanism_consistency.json` | Proves mathematical alignment with the programmed synthetic equations in `generate_sensor_data.py`; does NOT demonstrate real-world physical root-cause diagnostic capability. Attribution reflects model reconstruction failure rather than direct physical energy dissipation. |
| **Failure-Risk Prediction** (Model 3) | Continuous failure risk $R(t+H)$ at horizon $H=288$ steps | Chronological sensor telemetry (40,000 readings across 10 machines) | **FORMAL VERDICT: NO-GO**<br>Tree-based supervised failure-risk regression rejected; zero Random Forest or XGBoost models trained or deployed. | `reports/phase2/failure_risk_feasibility_assessment.md` | Training input truncation (inputs end at step 2511, 89 steps prior to fault activation at step 2600) leaves 0.0% degradation data in training inputs. Target ratio is 4.31x ($\max R_{\text{test}} = 0.9000$ vs $\max R_{\text{train}} = 0.2090$); Random Forest is mathematically bounded by $[0.0, 0.2090]$. 10 machines create pseudoreplication. |
| **Kernel SHAP Explainability** | Additive Shapley values per feature for negative IF decision score | Selected evaluation cohort: 70 observations from test partition (7/machine) | • **Validation Additivity Error:** $\le 1.39 \times 10^{-17}$<br>• **Test Additivity Error:** $\le 5.55 \times 10^{-17}$<br>• **Mean Latency:** 76.99 ms<br>• **Median Latency:** 70.43 ms<br>• **P95 Latency:** 107.58 ms | `reports/phase2/shap_explainability/shap_evaluation_results.json` | Evaluated on 70 curated samples, NOT the full 6,000 test points. Explains mathematical behavior of the Isolation Forest decision function, not physical root causes. Marginal perturbation assumption ($p(x_{\bar{S}}) \approx p(x_{\bar{S}}\mid x_S)$) can evaluate off-manifold synthetic combinations. |
| **ResNet Defect Classifier** | Single image bitmap ($128 \times 128 \times 3$ RGB) | 600 synthetic images (4 classes $\times$ 150): Train=420, Val=88, Test=92 | • **Test Accuracy:** 1.0 (100%)<br>• **Macro F1:** 1.0<br>• **Per-Class F1:** 1.0 across all 4 classes<br>• **Parameters:** 2,804,708 (Compact ResNet)<br>• **CPU Mean Latency:** 156.57 ms<br>• **Throughput:** 6.4 images/sec | `reports/phase2/defect_classifier/defect_classifier_results.json` | Procedural synthetic images with high-contrast geometric defect overlays and clean textures. Split randomly across splits rather than by machine or batch; does NOT evaluate generalization to unseen machines, lighting variations, or real factory environments. CPU latency != production SLA. |
| **Unified Inference Service** | Multimodal request payload (sensor, sequence, image) | In-memory synthetic requests and direct-model comparison suite | • **Numerical Parity:** $\Delta < 10^{-6}$ for IF, LSTM, ResNet, Attribution, SHAP<br>• **IF Service Median:** 15.50 ms<br>• **ResNet Service Median:** 90.16 ms<br>• **LSTM Service Median:** 108.61 ms | `reports/phase2/inference_service_eval_results.json` | Threading locks (`_tf_lock`, `_shap_lock`) serialize concurrent requests within a single process. Passive timeouts cannot preempt running C-extensions. Process-local singleton registry requires multi-process architecture for scaling. Empirical cold-start latency of ~6.04s. |
| **Regression Validation** | Pytest test execution items across backend codebase | Complete repository test suite: 10 modules, 118 test functions | • **Tests Collected:** 118<br>• **Tests Passed:** 118<br>• **Pass Rate:** 100.0%<br>• **Warnings:** 10 (all non-blocking)<br>• **Quarantine:** 0 reads from frozen test data | `reports/phase2/comprehensive_ml_validation_results.json` | 100% test pass rate validates software interface contracts, error boundaries, concurrency lock integrity, and regression resistance; it does NOT establish statistical generalization or real-world predictive validity. |

---

## 4. Model-by-Model Deep-Dive Audit

### 4.1 Isolation Forest Point-Level Anomaly Detection (Model 1)
- **Mathematical Formulation:** Ensemble of 100 extremely randomized isolation trees trained on nominal sensor readings. Anomaly score $s(x, n) = 2^{-\frac{\mathbb{E}[h(x)]}{c(n)}}$. Decision threshold $\tau = 0.0269$ calibrated on validation data at the 99th percentile ($1.0\%$ nominal contamination rate).
- **Test Partition Evidence (6,000 observations):**
  - **True Negatives:** 3,359
  - **False Positives:** 241 (False Positive Rate = $6.69\%$, Specificity = $93.31\%$)
  - **False Negatives:** 0 (Recall = $100.0\%$, Sensitivity = $100.0\%$)
  - **True Positives:** 2,400 (600 readings $\times$ 4 faulted machines)
  - **Precision:** 0.9087 (90.87%)
  - **F1-Score:** 0.9522
  - **ROC-AUC:** 0.9979; **PR-AUC:** 0.9965
- **Subgroup & Fleet Breakdown:**
  - Faulted machines (M102, M104, M107, M109): 100.0% detection rate (2,400 / 2,400 TP, 0 FN).
  - Healthy machines (M101, M103, M105, M106, M108, M110): Incurred 241 false alarms out of 3,600 readings. False alarm rates per machine: M101: 8.17% (49 FP), M103: 6.50% (39 FP), M105: 6.33% (38 FP), M106: 7.00% (42 FP), M108: 6.00% (36 FP), M110: 6.17% (37 FP).
- **Auditor Evaluation:** The perfect recall ($1.000$) is a consequence of large synthetic fault injections ($+15\sigma$ to $+39\sigma$). The $6.69\%$ false positive rate is consistent with point-level evaluation under Gaussian tail excursions. Point-level Isolation Forest must be smoothed or temporally aggregated in production to avoid operator alarm fatigue.

### 4.2 LSTM Autoencoder Sequence Anomaly Detection (Model 2)
- **Mathematical Formulation:** Sequence-to-sequence autoencoder (Encoder: 64 LSTM $\rightarrow$ 32 LSTM; Latent: 16 dense; Decoder: 32 LSTM $\rightarrow$ 64 LSTM $\rightarrow$ 5 dense linear output). Input shape: $(30, 5)$ representing 150 minutes of sliding telemetry with stride 10 (50 minutes). Reconstruction error: $\text{MSE}(X, \hat{X}) = \frac{1}{30 \times 5} \sum_{t=1}^{30} \sum_{j=1}^5 (x_{tj} - \hat{x}_{tj})^2$.
- **Test Partition Evidence (580 sequence windows):**
  - **Selected Threshold:** 0.901464 (calibrated on validation normal sequences at the 99th percentile).
  - **True Negatives:** 344
  - **False Positives:** 4 (False Positive Rate = $1.15\%$, Specificity = $98.85\%$)
  - **False Negatives:** 0 (Recall = $100.0\%$)
  - **True Positives:** 232 (58 windows $\times$ 4 faulted machines)
  - **Precision:** 0.9831 (98.31%)
  - **F1-Score:** 0.9915
  - **ROC-AUC:** 1.0000; **PR-AUC:** 1.0000
- **Subgroup Breakdown:**
  - Faulted machines: 100.0% detection across all 232 windows. Mean reconstruction error: M102 (overheating) = 60.94; M104 (bearing wear) = 135.40; M107 (pressure drop) = 106.29; M109 (lubrication failure) = 96.14. All anomalous errors are two orders of magnitude above the 0.9015 threshold.
  - Healthy machines: 344 TN, 4 FP. False alarms: 2 in M103, 2 in M110; 0 in M101, M105, M106, M108. Mean reconstruction error across healthy fleet ranged from 0.685 to 0.710.
- **Auditor Evaluation:** The temporal autoencoder demonstrates superior specificity ($98.85\%$ vs. $93.31\%$) compared to point-level Isolation Forest. However, consecutive sequence windows share 20 timesteps ($66.7\%$ overlap), meaning errors are autocorrelated.

### 4.3 Granularity Harmonization & Window Aggregation Analysis
Directly comparing point-level accuracy ($95.98\%$) to sequence-level accuracy ($99.31\%$) is a methodological error because point-level evaluation evaluates individual 5-minute telemetry readings, whereas sequence-level evaluation evaluates 150-minute blocks.

When Isolation Forest point scores are aggregated over the exact same 580 sequence windows:
- **IF Mean Score ($> 0.01344$):** Accuracy = 1.0, Precision = 1.0, Recall = 1.0, F1 = 1.0, **False Positives = 0** ($0.0\%$ FPR).
- **IF Max Score ($> 0.11978$):** Accuracy = 0.9845, Precision = 0.9627, Recall = 1.0, F1 = 0.9810, **False Positives = 9** ($2.59\%$ FPR).
- **IF Fraction Anomalous ($> 36.67\%$):** Accuracy = 1.0, Precision = 1.0, Recall = 1.0, F1 = 1.0, **False Positives = 0** ($0.0\%$ FPR).

**Key Scientific Finding:** Temporal aggregation filters out transient point-level Gaussian excursions. When evaluated on the same 30-step window basis, Isolation Forest performs on par with the LSTM Autoencoder (F1 = 1.0 vs. 0.9915).

### 4.4 Sensor-Level Anomaly Attribution
- **Mathematical Formulation:** 
  - LSTM Feature Attribution: Feature MSE contribution percentage $c_j = \frac{\text{MSE}_j}{\sum_{k=1}^5 \text{MSE}_k} \times 100\%$, where $\text{MSE}_j = \frac{1}{30}\sum_{t=1}^{30}(x_{tj} - \hat{x}_{tj})^2$.
  - Signed Standardized Residuals: $z_{tj} = x_{tj} - \hat{x}_{tj}$ in standardized $z$-score space, preserving directional drift ($+z$ indicates elevation, $-z$ indicates depression).
  - Isolation Forest Feature Ablation: Model-agnostic perturbation $\Delta s_j = s(x) - s(x_{\backslash j})$, replacing feature $j$ with its healthy fleet reference median.
- **Evidence Verification (232 anomalous sequence windows):**
  - **M102 (Overheating):** Primary driver is **Temperature** (61.98% attribution, $+13.35\sigma$ signed residual), followed by Pressure (36.67%, $+10.29\sigma$). 100% mode match across all 58 windows.
  - **M104 (Bearing Wear):** Primary driver is **Vibration** (88.00% attribution, $+23.37\sigma$ signed residual), followed by Temperature (5.90%, $+5.68\sigma$) and Spindle Drag (RPM $-4.56\sigma$). 100% mode match.
  - **M107 (Pressure Drop):** Primary driver is **Pressure** (91.34% attribution, $-21.50\sigma$ signed residual), followed by Motor Current compensation (7.90%, $+6.16\sigma$). 100% mode match.
  - **M109 (Lubrication Failure):** Primary driver is **Current** (44.69% attribution, $+14.15\sigma$), followed by Gear Vibration (31.34%, $+11.90\sigma$) and Thermal Rise (23.17%, $+10.13\sigma$). 100% mode match.
- **Auditor Evaluation:** The attributions exhibit 100% consistency with the designed synthetic fault dynamics. However, attribution measures **model prediction sensitivity and reconstruction residuals**, not physical causal mechanics.

### 4.5 Failure-Risk Prediction Feasibility (Step 5 NO-GO Determination)
Phase 2 Step 5 originally proposed training supervised Random Forest and XGBoost regressors to predict continuous failure risk $R(t + H)$ at horizon $H = 288$ steps (24 hours). 

Following technical investigation, Step 5 was formally closed as a **NO-GO Feasibility Assessment**. Zero models were trained or deployed based on four prohibitive mathematical and data constraints:

1. **Training Input Truncation (0.0% Degradation):** Under the purged chronological split (Train: steps 0 to 2799), input samples for horizon $H = 288$ terminate at step 2511 ($2799 - 288 = 2511$). Synthetic fault dynamics activate at step 2600. Consequently, the training input partition contains **zero timesteps of physical fault progression**.
2. **Convex Hull Target Boundary Ceiling (4.31x Target Expansion):** In the training partition, the maximum ground-truth target risk across all machines is $0.2090$. In the test partition, target risk reaches $0.9000$. Because standard Random Forest predictions are convex combinations of training target values ($\min y_{\text{train}} \le \hat{y}_{\text{RF}} \le \max y_{\text{train}}$), Random Forest cannot mathematically output any value above $0.2090$. XGBoost can extrapolate outside training targets via gradient boosting, but axis-aligned tree splits route extreme degradation inputs into saturated boundary leaves.
3. **Absence of Pre-Onset Physical Indicators:** Statistical analysis of baseline telemetry prior to step 2600 confirmed that sensor readings consist of stationary i.i.d. Gaussian noise ($|r| < 0.06$ against future risk targets). There is zero progressive trend to forecast.
4. **Pseudoreplication & Machine Confounding:** The 40,000 observations originate from only 10 machines (4 faulted, 6 healthy). In experimental statistics, repeated measurements from 10 units constitute pseudoreplication, where machine ID and fault type are 100% confounded.

**Auditor Evaluation:** The NO-GO decision is scientifically sound. Attempting to train tree regressors under these conditions would have produced an overfitted model learning spurious baseline machine offsets rather than real degradation physics.

### 4.6 Kernel SHAP Sensor Explainability
- **Mathematical Formulation:** Local feature explanation for the continuous Isolation Forest anomaly intensity: $f(x) = -\text{decision\_function}(x)$. Kernel SHAP solves the weighted linear regression formulation of Shapley values with $M = 5$ features and $n_{\text{samples}} = 32$.
- **Background Summary:** 50 normal training observations (5 per machine across 10 machines, base seed 42) sampled from `ml/models_store/val_features.npy`. Base expected value: $\mathbb{E}[f(X)] = -0.04778$.
- **Evidence Verification:**
  - **Additive Efficiency:** Strict mathematical additivity ($\sum_{j=1}^5 \phi_j = f(x) - \mathbb{E}[f(X)]$) verified across all samples. Maximum additivity error: $1.39 \times 10^{-17}$ (validation cohort) and $5.55 \times 10^{-17}$ (frozen test cohort).
  - **Test Cohort Scope:** Evaluated on a curated cohort of **70 observations** (7 per machine), NOT the full 6,000-point test partition.
  - **Local Latency Distribution (25 timed runs):** Mean = 76.99 ms, Median = 70.43 ms, P90 = 101.43 ms, P95 = 107.58 ms, Min = 62.14 ms, Max = 109.45 ms.
- **Auditor Evaluation:** SHAP explains the internal decision boundaries of the Isolation Forest. Because Kernel SHAP samples features along marginal distributions, it assumes feature independence. Correlated features (e.g. temperature and pressure during press overheating) can be evaluated in off-manifold combinations.

### 4.7 ResNet Vision Defect Classifier
- **Architecture & Complexity:** Compact ResNet-18 trained from scratch. 4 residual stages (channels: 32, 64, 128, 256), each with 2 basic residual blocks. Input size: $128 \times 128 \times 3$. Total parameter count: **2,804,708** (2,799,908 trainable, 4,800 non-trainable batch normalization parameters). Standard torchvision ResNet-18 comparator: 11,188,164 parameters ($74.93\%$ reduction).
- **Dataset Partitioning (600 procedural synthetic images):**
  - Classes (4): `surface_crack`, `spalling`, `dent`, `normal_surface` (150 images/class).
  - Training Partition: 420 images (105/class).
  - Validation Partition: 88 images (22/class).
  - Frozen Test Partition: 92 images (23/class).
- **Test Partition Evidence (92 images):**
  - **Accuracy:** 1.0 (100.0%)
  - **Macro Precision:** 1.0; **Macro Recall:** 1.0; **Macro F1:** 1.0
  - **Per-Class F1:** `surface_crack` = 1.0, `spalling` = 1.0, `dent` = 1.0, `normal_surface` = 1.0
  - **Macro ROC-AUC:** 1.0 across all 4 classes.
- **Local Latency Benchmark (100 iterations on CPU):**
  - Mean Forward Latency: 156.57 ms
  - Median: 159.39 ms; P95: 214.09 ms; Min: 101.89 ms; Max: 259.64 ms
  - Throughput: 6.4 images/second.
- **Auditor Evaluation:** The 100% test accuracy reflects high contrast between synthetic procedural defect overlays and synthetic base metal textures. Images were split randomly across splits rather than by machine or generation batch. This benchmark does not demonstrate generalization to real industrial defects, variable lighting, oil sheen, or unseen manufacturing lines.

### 4.8 Unified Multimodal Inference Service Integration
- **Architecture:** Unified service wrapper (`UnifiedInferenceService`) orchestrating sensor preprocessing, Isolation Forest scoring, LSTM Autoencoder reconstruction, sensor attribution, Kernel SHAP explanation, and ResNet defect inspection.
- **Numerical Parity Verification:**
  - Isolation Forest Anomaly Score Difference: $1.54 \times 10^{-7}$ ($\le 10^{-6}$)
  - LSTM Reconstruction Error Difference: $3.71 \times 10^{-7}$ ($\le 10^{-6}$)
  - ResNet Prediction Confidence Difference: $0.00$ ($\le 10^{-6}$)
  - Sensor Attribution Dominant Feature Match: 100% identical
  - SHAP Additivity Verification: $5.55 \times 10^{-17}$ ($\le 10^{-14}$)
- **Latency Benchmarks (100 iterations):**
  - Tabular Sensor Inference (IF): Mean = 15.07 ms, Median = 15.50 ms, P95 = 19.09 ms.
  - Image Defect Inspection (ResNet): Mean = 95.83 ms, Median = 90.16 ms, P95 = 135.46 ms.
  - Sequence Inference (LSTM): Median = 108.61 ms, P95 = 375.39 ms, Mean = 871.29 ms.
  - *LSTM Latency Outlier Note:* The elevated mean (871.29 ms) was caused by a single 72.56-second pause during iteration 68, attributable to operating system background garbage collection and memory paging under Windows rather than algorithmic execution.
- **Architectural Constraints:**
  - Concurrency is protected via in-process locks (`_tf_lock` and `_shap_lock`). While preventing C-extension memory faults on CPU architectures, it serializes concurrent inference within a single process.
  - Configured timeouts are passive evaluation deadlines rather than preemptive thread cancellations.
  - Initial composite inference invocation exhibits empirical cold-start latency of ~6.04s.

### 4.9 Comprehensive ML Regression Validation
- **Suite Composition:** 118 automated test functions across 10 modules executed via Pytest.
- **Execution Outcome:** 118 collected, 118 passed, 0 failures, 0 errors (100.0% pass rate in 108.65s).
- **Frozen Test-Partition Quarantine:** Strict quarantine enforced. Zero reads from `sequences_test.npz` or `sensor_test.csv` during test execution. Tests evaluate deterministic synthetic fixtures (seed 42).
- **Warnings Classification (10 warnings):** 3 `PendingDeprecationWarning` from upstream `shap` package's Matplotlib colormaps; 7 `PydanticDeprecatedSince20` warnings from existing Phase 1 schema `Field(..., example=...)` usage. All 10 warnings are non-blocking upstream/schema metadata deprecations.
- **Auditor Evaluation:** Software regression tests confirm that code contracts, exception boundaries, Pydantic schemas, and concurrency locks function as designed. They do NOT establish real-world statistical generalization.

---

## 5. Critical Scientific Integrity Disclosures

To prevent misleading claims in subsequent research papers, academic presentations, and Phase 3 documentation, the following ten scientific boundaries are formally established:

1. **Synthetic Sensor Telemetry:** The entire sensor dataset (40,000 readings across 10 machines) is synthetic, generated via scripted mathematical formulas and random distributions in `ml/data_generator/generate_sensor_data.py`.
2. **Fleet Size & Pseudoreplication:** Only 10 machines are represented (M101 through M110). In experimental statistics, repeated longitudinal measurements across 10 experimental units constitute pseudoreplication (Hurlbert, 1984).
3. **Machine-to-Fault Confounding:** Four fault types are strictly coupled 1-to-1 with four specific machine IDs (M102=overheating, M104=bearing wear, M107=pressure drop, M109=lubrication failure). Machine identity and fault type are 100% confounded.
4. **Programmed Deterministic Fault Dynamics:** Fault progressions are programmed linear and polynomial trends added to Gaussian noise, not natural physical stochastic degradation.
5. **Fixed Synthetic Onset Timestep:** Fault dynamics activate at the exact fixed timestep 2600 (65% of the 4,000-step timeline) for all faulted machines.
6. **Autocorrelated Evaluation Windows:** Sequence evaluation uses 30-step windows with stride 10, meaning consecutive windows share 20 timesteps (66.7% overlap) and violate statistical sample independence.
7. **Random Image Partitioning:** The 600 synthetic images were split randomly (70/15/15) across train/val/test rather than by machine or generation batch, precluding claims of generalization to unseen machines or real factories.
8. **Failure-Risk Prediction Formally Closed (NO-GO):** Failure-risk prediction was formally closed as a NO-GO feasibility assessment; zero Random Forest or XGBoost models were trained or deployed.
9. **Attribution is Not Causal:** Sensor attribution and Kernel SHAP measure model mathematical decision boundaries and residual reconstruction errors, not real-world physical causal mechanisms.
10. **DEFECT-01 Remains Unresolved:** DEFECT-01 remains open in `backend/app/ml/inference/schemas.py:86-94`, where partial timestamp arrays bypass chronological monotonicity validation.

### Explicit Negative Declarations:
The ManuMind AI Phase 2 machine learning system does **NOT** claim:
- Production-ready predictive accuracy in operational factories.
- Proven real-world fault generalization across unseen machinery.
- Real-world causal root-cause identification.
- Validated failure probabilities or remaining useful life (RUL) estimation.
- Formal zero-leak memory stability or SLA compliance.

---

## 6. Outstanding Technical Issues Register

| ID | Type | Severity | Component | Summary & Impact | Remediation Plan |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **DEFECT-01** | Defect | Low | `backend/app/ml/inference/schemas.py:86-94` | **Partial Timestamp Monotonicity Bypass:** Chronological monotonicity is only checked when `len(timestamps) == len(self.readings)`. If a sequence has 29 valid timestamps and 1 `None`, the loop is bypassed without raising an error. | Phase 3 Schema Hardening: Require all timestamps present or all `None`. |
| **LIM-01** | Limitation | Info | `backend/app/ml/inference/service.py` | **In-Process Lock Serialization:** `_tf_lock` and `_shap_lock` serialize concurrent inference within a single process. | Phase 3 Deployment: Deploy multi-process worker pool (Uvicorn/Gunicorn). |
| **LIM-02** | Limitation | Info | `backend/app/ml/inference/service.py` | **Cold-Start Latency:** Initial composite inference cycle exhibits latency of ~6.04s due to graph compilation and library setup. | Phase 3 Deployment: Implement container pre-warming and model warmup on startup. |
| **LIM-03** | Limitation | Info | `backend/app/ml/inference/service.py` | **LSTM Latency GC Sensitivity:** A single 72.56s outlier occurred during 100-cycle benchmark due to OS garbage collection/paging. | Production Tuning: Optimize Python GC thresholds and container memory limits. |
| **LIM-04** | Limitation | Medium | `Isolation Forest & LSTM Zero-Shot` | **Zero-Shot Holdout Degradation:** Testing on completely unseen machine assets drops recall to 48.86%–76.14% due to machine-specific baseline differences. | Phase 3 Agent Architecture: Implement an asset-specific baseline calibration window before activating anomaly scoring. |

---

## 7. Recommendations for Phase 3 Multi-Agent Architecture

Based on the empirical evidence reconciled in this audit, the following design recommendations are provided for Phase 3 (LangGraph, MCP Tools, and RAG Integration):

1. **Dual-Model Anomaly Confirmation Gate:** Because point-level Isolation Forest has a 6.69% false alarm rate while sequence-level LSTM Autoencoder has a 1.15% false alarm rate, the Phase 3 Anomaly Detection Agent should implement a dual-confirmation policy: trigger supervisory investigation only when both models flag an anomaly, or when Isolation Forest maintains elevated anomaly scores across consecutive readings.
2. **Root Cause Attribution as Hypotheses, Not Facts:** The Root Cause Analysis Agent must treat sensor attributions and SHAP rankings as statistical feature contributions rather than ground-truth physical root causes. The agent should cross-reference attributed sensors against machine maintenance history and technical manuals via RAG before finalizing root-cause hypotheses.
3. **Multi-Process Agent Serving:** Because the inference service utilizes in-process threading locks for TensorFlow and SHAP, multi-agent orchestrations invoking concurrent tool calls should serve models across multiple worker processes (or via an asynchronous queuing layer) to avoid thread serialization bottlenecks.
4. **Asset-Specific Baseline Profiling:** In line with LIM-04, the multi-agent system should establish machine-specific normal operating baselines for newly introduced machine assets before enabling autonomous alerting.

---

## 8. Final Audit Sign-Off

```text
========================================================================================
FINAL AUDIT DECISION:
EVIDENCE AUDIT COMPLETE — READY FOR FINAL REPORT
========================================================================================
```

- **Repository Baseline:** Verified at commit `13fd0141a24c24e9e9267881e0f37672f0b114ca` on branch `main`.
- **Deliverables Generated:**
  1. [`reports/phase2/final_ml_evaluation_evidence_audit.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/final_ml_evaluation_evidence_audit.md)
  2. [`reports/phase2/final_ml_evaluation_evidence.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/final_ml_evaluation_evidence.json)
- **Protected Assets Integrity:** Confirmed 100% bit-identical match across all 7 production model artifacts.
- **Git Restrictions Respected:** Zero models retrained, zero frozen partitions evaluated, zero code modified, zero files staged, committed, or pushed.
