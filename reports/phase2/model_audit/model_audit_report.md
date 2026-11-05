# ManuMind AI — Independent Machine Learning Model & Pipeline Audit Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.1 — Comprehensive Independent Audit (Audits A through G)
**Auditor:** Independent Senior ML Engineer & Auditor
**Date:** November 2026
**Status:** **AUDIT COMPLETE — VERDICT: APPROVED WITH LIMITATIONS**

---

## 1. Executive Summary & Audit Mandate

An independent, rigorous machine learning audit was conducted across all completed Phase 2 artifacts of ManuMind AI:
- **Phase 2, Step 0:** Dataset Quality & Temporal Partition Audit
- **Phase 2, Step 1:** Telemetry Preprocessing, Scaling & Sequence Window Generation
- **Phase 2, Step 2:** Model 1 — Tabular Anomaly Detection via Isolation Forest
- **Phase 2, Step 3:** Model 2 — Temporal Sequence Anomaly Detection via LSTM Autoencoder

### Reason for Audit
Both models reported unusually high benchmark metrics on the untouched test partition:
- **Isolation Forest:** Accuracy = $95.98\%$, F1 = $95.22\%$, ROC-AUC = $0.9979$, Recall = $100.0\%$, False Positive Rate = $6.69\%$
- **LSTM Autoencoder:** Accuracy = $99.31\%$, F1 = $99.15\%$, ROC-AUC = $1.0000$, Recall = $100.0\%$, False Positive Rate = $1.15\%$
- **Reconstruction Errors:** Normal sequence error $\approx 0.69$, Faulted sequence errors $\approx 60\text{--}135$, Calibrated Threshold $= 0.901464$

The mandate was to determine objectively whether these results represent genuine model competence, model overfitting, data leakage, or synthetic fault separability.

### Primary Audit Findings Matrix

| Audit Area | Scope | Independent Audit Finding | Detailed Status | Supporting Evidence |
|---|---|---|:---:|---|
| **Audit A** | Training Dynamics & Overfitting | No overfitting. Normal training and validation loss converge stably from $0.86$ to $0.69$ MSE. | **PASS** | Train-val loss gap remains slightly negative due to Dropout(0.1) during training. Best epoch: 49. |
| **Audit B** | Data Leakage Verification | All 10 leakage criteria verified. Zero test data or label contamination. | **PASS (10/10)** | Scaler fitted on 28k rows; 80 anomalies excluded; test set completely unobserved until final eval. |
| **Audit C** | Sequence Overlap & Splits | Zero timestamp overlap, zero identical sequences. 40 straddling windows completely eliminated. | **PASS** | $3,980 \to 3,940$ sequences. Chronological partition independence confirmed across all 10 machines. |
| **Audit D** | Synthetic Fault Separability | Injected faults in test split represent late-stage severe degradation ($Z = +22$ to $+39.5\sigma$). | **PRIMARY DRIVER** | Massive separation ($25.8\times$) between max normal error ($0.96$) and min anomaly error ($24.76$). |
| **Audit E** | Threshold Calibration | LSTM threshold ($0.901464$) verified to $10^{-7}$ precision on normal validation sequences. | **PASS** | Exactly 99th percentile of 348 normal validation sequences. Zero test data used. |
| **Audit F** | Independent Test Recalculation | Recalculated metrics match reported values with 100% parity. | **PASS** | Mathematical proof: ROC-AUC = 1.0 is consistent with 4 False Positives at $\tau = 0.901464$. |
| **Audit G** | Machine Generalization | Diagnostic holdout experiment demonstrated 98.6% specificity on unseen healthy machine M110. | **DOCUMENTED** | Chronological asset monitoring confirmed; fleet holdout limitations documented. |

---

## 2. Audit A — Training & Validation Dynamics (LSTM Autoencoder)

The training trajectory was audited using the recorded epoch histories in `ml/models_store/lstm_autoencoder_metadata.json`:

### Quantitative Loss Progression
- **Initial Epoch 1:** Training Loss = $0.8606$, Validation Loss = $0.8174$
- **Midpoint Epoch 25:** Training Loss = $0.7468$, Validation Loss = $0.7297$
- **Epoch 49 (Best Epoch):** Training Loss = $0.7051$, **Validation Loss = $0.688796$** (Weights restored)
- **Final Epoch 50:** Training Loss = $0.7064$, Validation Loss = $0.6893$

### Train-Validation Gap Analysis
- Mean Training Loss: $0.7570$ MSE
- Mean Validation Loss: $0.7381$ MSE
- Mean Loss Gap ($\text{Train} - \text{Val}$): $+0.0189$ MSE
- Maximum Loss Gap: $+0.0432$ MSE (Epoch 1)
- Minimum Loss Gap: $+0.0163$ MSE (Epoch 49)

### Overfitting Assessment: No Evidence of Overfitting
1. **Parallel Monotonic Decrease:** Both training loss and validation loss decrease smoothly and monotonically over 50 epochs, flattening into an asymptotic plateau near $0.69$ MSE.
2. **Absence of Divergence:** In typical neural network overfitting, training loss continues driving towards zero while validation loss reverses and climbs sharply. In this model, validation loss strictly tracks training loss with zero upward divergence.
3. **Why Validation Loss is Lower than Training Loss:**
   - **Dropout Inactivation:** `Dropout(0.1)` layers are active during training batches (randomly zeroing 10% of hidden activations and adding regularization noise), but are switched off during validation evaluation.
   - **Evaluation Timing:** Training loss is the cumulative moving average across all 85 mini-batches of an epoch, whereas validation loss is evaluated once at the very end of the epoch when model weights have received all updates.
4. **Appropriate Reconstruction Residual:** An MSE of $\approx 0.69$ on standardized variables ($\mu=0, \sigma=1$) confirms the bottleneck (latent dimension 32 representing $30 \times 5 = 150$ features) is effectively compressing normal patterns rather than trivially memorizing individual sequences.

*Supporting Figures:* [`reports/phase2/model_audit/graphs/training_vs_validation_loss.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/training_vs_validation_loss.png) and [`reports/phase2/model_audit/graphs/train_validation_gap.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/train_validation_gap.png).

---

## 3. Audit B — Complete Data Leakage Verification

All 10 pipeline checkpoints were independently verified. Detailed line-by-line code inspections are documented in [`reports/phase2/model_audit/data_leakage_checklist.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/data_leakage_checklist.md).

### Summary of Leakage Verification:
1. **StandardScaler Fit:** `scaler.n_samples_seen_ == 28,000`, matching `sensor_train.csv` exclusively (**PASS**).
2. **Scaler Isolation:** Scaler parameters ($\mu, \sigma$) were never updated with validation or test data (**PASS**).
3. **Normal Sequence Filter:** Training dataset strictly contained 2,700 normal sequences (**PASS**).
4. **Anomalies Excluded:** All 80 anomalous training sequences were filtered out prior to fitting (**PASS**).
5. **Early Stopping Isolation:** `val_loss` monitored strictly on 348 normal validation sequences (**PASS**).
6. **Threshold Calibration Isolation:** Evaluated strictly on validation sequences; test set unobserved (**PASS**).
7. **Hyperparameter Selection:** Static configuration from domain best practices; no test optimization (**PASS**).
8. **Unsupervised Objective:** Optimization objective is purely $X \to X$ reconstruction (**PASS**).
9. **Causal Temporal Slicing:** Sliding windows strictly slice $[t-29 : t]$ backward in time (**PASS**).
10. **Metadata Integrity:** Full preservation of timestamps, machine IDs, and labels across all splits (**PASS**).

**Verdict:** **ZERO DATA LEAKAGE DETECTED**.

---

## 4. Audit C — Sequence Overlap & Partition Independence

The chronological partitioning and window extraction were audited in [`reports/phase2/model_audit/sequence_overlap_analysis.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/sequence_overlap_analysis.json):

1. **Timestamp Separation:**
   - Train: Timesteps 0 to 2,799 ($28,000$ readings across 10 machines).
   - Validation: Timesteps 2,800 to 3,399 ($6,000$ readings across 10 machines).
   - Test: Timesteps 3,400 to 3,999 ($6,000$ readings across 10 machines).
   - Timestamp overlap: **0 readings**.
2. **Straddling Windows:**
   - In raw slicing, 40 windows straddled the boundaries (20 at step 2,800, 20 at step 3,400).
   - In Step 1 Preprocessing, sequence extraction was executed independently within each partition.
   - Result: All 40 straddling windows were **completely eliminated** ($3,980 \to 3,940$ clean windows).
3. **Sequence Collisions:**
   - Byte-level hash verification confirmed **0 identical sequence windows** across splits.

---

## 5. Audit D — Synthetic Fault Separability (Primary Explanation of High Scores)

The investigation into the synthetic data generation dynamics revealed the primary explanation for the unusually high metrics. Complete statistical analyses are documented in [`reports/phase2/model_audit/synthetic_fault_separability.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/synthetic_fault_separability.md).

### The Late-Stage Failure Regime in the Test Split
In `ml/data_generator/generate_sensor_data.py`, progressive fault degradation starts at timestep 2,600 and ramps quadratically to step 4,000:
- Because the Test Split contains timesteps **3,400 to 3,999**, all anomalous test samples occur when:
  $$progression \in [0.5714, 1.0000]$$
- In this severe failure regime, physical sensor deviations are extreme:
  - **M104 (Bearing Spalling):** Vibration reaches $10.5\text{ mm/s}$ ($Z = +39.5\sigma$ above nominal).
  - **M102 (Overheating):** Temperature reaches $95^\circ\text{C}$ ($Z = +37.5\sigma$ above nominal).
  - **M107 (Pressure Drop):** Pressure falls to $2.4\text{ bar}$ ($Z = -31.6\sigma$ below nominal).
  - **M109 (Lubrication Friction):** Current draws $30\text{ A}$ ($Z = +22.1\sigma$ above nominal).

### Non-Overlapping Reconstruction Error Gap
- Maximum reconstruction error among normal test sequences: **$0.9609$ MSE**
- Minimum reconstruction error among anomalous test sequences: **$24.7624$ MSE**
- **Separation Margin:** **$23.8015$ MSE** ($25.77\times$ higher than max normal error)

**Conclusion:** The models achieve near-perfect scores because the synthetic benchmark tests them on **late-stage, highly severe equipment degradation** where the fault signature is starkly separated from baseline operation.

*Supporting Figures:* [`reports/phase2/model_audit/graphs/normal_vs_anomalous_sensor_distributions.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/normal_vs_anomalous_sensor_distributions.png), [`reports/phase2/model_audit/graphs/fault_progression.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/fault_progression.png), and [`reports/phase2/model_audit/graphs/reconstruction_error_distributions.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/reconstruction_error_distributions.png).

---

## 6. Audit E — Threshold Calibration Verification

The reconstruction threshold calibration was audited in [`reports/phase2/model_audit/threshold_calibration_audit.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/threshold_calibration_audit.json):

1. **Calculation Verification:**
   - The threshold was recalculated independently from the 348 normal validation sequences:
     $$\tau_{\text{recalculated}} = \text{percentile}(\text{val\_errors\_normal}, 99.0) = \mathbf{0.901463687}$$
   - Saved threshold in metadata: $\mathbf{0.901464}$
   - Delta: $3.12 \times 10^{-7}$ (exact float precision match).
2. **Zero Test Data Influence:**
   - Confirmed that zero test sequence errors were included in the percentile calculation.
3. **Threshold Calibration vs. Training vs. Evaluation:**
   - **Model Training:** Learns normal representation weights $\theta$ on $X_{\text{train\_normal}}$ without labels.
   - **Threshold Calibration:** Selects operational cutoff $\tau$ on $X_{\text{val\_normal}}$ to enforce an industrial false alarm ceiling ($\le 1.0\%$).
   - **Final Test Evaluation:** Applies fixed $\tau$ to unobserved $X_{\text{test}}$ to compute unbiased performance metrics.

*Supporting Figure:* [`reports/phase2/model_audit/graphs/threshold_comparison.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/model_audit/graphs/threshold_comparison.png).

---

## 7. Audit F — Independent Test Recalculation & ROC-AUC Analysis

All metrics were re-derived directly from saved prediction CSVs:

### Recalculation Verification Table

| Model | Metric | Reported in JSON | Independently Recomputed | Parity Status |
|---|---|:---:|:---:|:---:|
| **Isolation Forest** | Accuracy | 0.9598 | 0.9598 | **100% Match** |
| | Precision | 0.9087 | 0.9087 | **100% Match** |
| | Recall | 1.0000 | 1.0000 | **100% Match** |
| | F1-Score | 0.9522 | 0.9522 | **100% Match** |
| | ROC-AUC | 0.9979 | 0.9979 | **100% Match** |
| | PR-AUC | 0.9965 | 0.9965 | **100% Match** |
| | Confusion Matrix | TN=3359, FP=241, FN=0, TP=2400 | TN=3359, FP=241, FN=0, TP=2400 | **100% Match** |
| **LSTM Autoencoder** | Accuracy | 0.9931 | 0.9931 | **100% Match** |
| | Precision | 0.9831 | 0.9831 | **100% Match** |
| | Recall | 1.0000 | 1.0000 | **100% Match** |
| | F1-Score | 0.9915 | 0.9915 | **100% Match** |
| | ROC-AUC | 1.0000 | 1.0000 | **100% Match** |
| | PR-AUC | 1.0000 | 1.0000 | **100% Match** |
| | Confusion Matrix | TN=344, FP=4, FN=0, TP=232 | TN=344, FP=4, FN=0, TP=232 | **100% Match** |

### Mathematical Analysis: Why ROC-AUC is 1.0 Despite 4 False Positives
A key question addressed by the audit is why the LSTM Autoencoder achieved an **ROC-AUC of 1.0000** even though threshold classification produced **4 False Positives** ($\text{FPR} = 1.15\%$).

- **Continuous Ranking vs. Fixed Operating Point:**
  - ROC-AUC measures the probability that a randomly chosen anomalous sequence is scored higher than a randomly chosen normal sequence across **all possible classification thresholds**:
    $$\text{ROC-AUC} = P(\text{Error}(\text{Anomaly}) > \text{Error}(\text{Normal}))$$
  - In our test set:
    $$\min(\text{Error}_{\text{anomaly}}) = 24.7624 > \max(\text{Error}_{\text{normal}}) = 0.9609$$
  - Because **every single anomaly has an error strictly higher than every single normal sample**, the relative ranking is mathematically perfect, resulting in $\text{ROC-AUC} = \mathbf{1.0000}$.
- **Why the 4 False Positives Occur:**
  - The operational threshold ($\tau = 0.901464$) was calibrated on the **99th percentile of normal validation errors**.
  - In the test set of 348 normal sequences, exactly 4 normal sequences exhibited subtle diurnal thermal variance producing reconstruction errors between $0.9015$ and $0.9609$.
  - Because their errors exceeded $\tau = 0.901464$, they were classified positive (4 false alarms out of 348 normal samples $= 1.15\%$ false alarm rate).
  - An alternative operating threshold of $\tau = 2.0$ would produce $\text{FP} = 0$ and $\text{FN} = 0$.
  - Therefore, $\text{ROC-AUC} = 1.0$ alongside 4 False Positives is **mathematically sound, expected, and fully consistent**.

---

## 8. Audit G — Machine Generalization & Diagnostic Holdout

Audit G investigated whether models learned machine-specific characteristics by conducting a separate, isolated diagnostic experiment:
- **Setup:** Trained on 5 healthy machines (`M101, M103, M105, M106, M108`), evaluated on unseen healthy machine `M110` and unseen faulted machines (`M102, M104, M107, M109`).
- **Results:**
  - Specificity on unseen healthy machine `M110`: **$98.60\%$** (False positive rate = $1.40\%$).
  - Precision on unseen faulted machines: **$96.2\%$ to $97.5\%$**.
  - Incipient phase recall (steps 2600–3400): $49\%$ to $76\%$.
  - Late failure recall (steps 3400–4000): $100.0\%$.

### Industrial Framing
The project implements **Asset-Level Chronological Monitoring**, which is the standard paradigm for fixed factory machine monitoring. Zero-shot transfer to unseen machines is feasible for nominal baselines, but true cross-fleet fault diagnosis is constrained by the current 10-machine dataset (each fault type exists on only one machine).

---

## 9. Final Audit Verdict

Based on empirical evidence across Audits A through G, the independent auditor delivers the following verdicts:

### Model 1: Isolation Forest
> **VERDICT:** **Conclusion 4 (High performance primarily explained by synthetic fault separability)**
> *Secondary Finding:* **Conclusion 1 (No significant evidence of overfitting or leakage)**
> *Evidence:* Standard scaler was fit exclusively on train data; 800 training anomalies were excluded; test metrics were verified; high test recall is driven by large physical feature deviations ($13\sigma\text{--}39\sigma$) in the test split.

### Model 2: LSTM Autoencoder
> **VERDICT:** **Conclusion 4 (High performance primarily explained by synthetic fault separability)**
> *Secondary Finding:* **Conclusion 1 (No significant evidence of overfitting or leakage)**
> *Evidence:* Normal training and validation loss converged stably without divergence; all 10 leakage criteria passed; threshold calibration was verified to $10^{-7}$; 4 false positives alongside 1.0 ROC-AUC is mathematically consistent; high recall is driven by the $25.8\times$ error separation margin in the late degradation test regime.

---

## 10. Project-Readiness Decision

### Decision: **APPROVED WITH LIMITATIONS**

The project is **approved to proceed immediately to Phase 2, Step 4 (Sensor-Level Anomaly Attribution)** under the following documented engineering boundaries:

1. **Documented Benchmark Nature:** The near-perfect metrics ($99.3\%$ accuracy, $1.0$ ROC-AUC) must be clearly documented in final academic and project reports as reflecting **severe late-stage degradation on synthetic industrial benchmarks**, not real-world industrial ease.
2. **Asset Monitoring Scope:** The models are recognized as operating under **chronological asset monitoring** rather than cross-fleet transfer.
3. **Synergy with Step 4:** The high reconstruction error separation between normal and faulted channels provides an optimal foundation for **channel-wise sensor attribution** $(\mathbf{x}_c - \hat{\mathbf{x}}_c)^2$ in Step 4 to isolate root causes.
