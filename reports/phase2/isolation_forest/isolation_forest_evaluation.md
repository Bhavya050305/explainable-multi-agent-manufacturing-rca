# ManuMind AI — Model 1: Isolation Forest Anomaly Detection Evaluation Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science
**Component:** Model 1 — Tabular Unsupervised Anomaly Detection (Isolation Forest)
**Date:** November 2026
**Status:** **TRAINED, EVALUATED, AND VALIDATED ON UNTOUCHED TEST SET**

---

## 1. Executive Summary

This report documents the design, training, calibration, and rigorous evaluation of **Model 1: Isolation Forest** for tabular multivariate manufacturing anomaly detection.

The model was trained **strictly on verified healthy baseline operational readings** (N = 27,200) across 5 physical telemetry features: Vibration, Temperature, Pressure, Current, and RPM. It was calibrated on the validation set (N = 6,000) and evaluated on the untouched test partition (N = 6,000).

### Core Benchmark Metrics (Untouched Test Partition)

| Metric | Target Standard | Realized Value | Assessment |
|---|---|---:|:---:|
| **ROC-AUC** | >= 0.900 | **0.9979** | **Outstanding discrimination** |
| **PR-AUC (Average Precision)** | >= 0.850 | **0.9965** | **Robust under class imbalance** |
| **F1-Score** | >= 0.850 | **0.9522** | **High balance of Precision & Recall** |
| **Precision** | >= 0.800 | **0.9087** | **Low false alarm rate** |
| **Recall (Sensitivity)** | >= 0.850 | **1.0000** | **High fault capture rate** |
| **Accuracy** | >= 0.850 | **0.9598** | **Strong overall performance** |
| **Healthy Specificity** | >= 0.900 | **0.9331** | **93.3% specificity on healthy machines** |

---

## 2. Introduction to Isolation Forest

Isolation Forest (Liu, Ting, and Zhou, 2008) is an unsupervised anomaly detection algorithm built on ensemble randomized decision trees (*iTrees*). Unlike profiling or density estimation techniques that construct normal operating envelopes:
1. **Direct Isolation:** Anomalies are 'few and different', meaning anomalous points require fewer random recursive orthogonal feature splits to isolate than normal cluster points.
2. **Path Length Anomaly Scoring:** The average path length $h(x)$ across an ensemble of $t$ isolation trees provides an anomaly score:
$$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
where $c(n) = 2 \ln(n - 1) + 0.5772156649 - \frac{2(n - 1)}{n}$ is the average path length of an unsuccessful search in a binary search tree.
3. **Linear Time Complexity:** Training complexity is $O(t \cdot \psi \log \psi)$, making it fast and scalable for high-cadence industrial telemetry streams.

---

## 3. Suitability for Manufacturing Anomaly Detection

Isolation Forest is suited for modern factory predictive maintenance because:
1. **Absence of Clean Historical Failure Labels:** In manufacturing, catastrophic failures are rare events. Supervised classification suffers from extreme scarcity of true positive failures. Isolation Forest trains entirely on healthy baseline telemetry without requiring pre-labeled breakdowns.
2. **Subtle Multi-Sensor Coupling:** Complex industrial anomalies (such as lubrication failure or bearing wear) manifest as subtle simultaneous shifts across mechanical vibration, winding thermal dissipation, and motor current draw. Orthogonal tree splits detect high-dimensional outliers without assuming unimodal Gaussian distributions.
3. **Computational Efficiency:** Evaluation of a 5-sensor telemetry reading across 200 shallow trees takes under 0.2 milliseconds, enabling sub-second edge inference on plant PLCs and industrial PCs.

---

## 4. Preprocessing & Training Methodology

### 4.1 Strict Standardization Protocol
- Telemetry features were standardized using a `StandardScaler` fitted **exclusively on the 28,000-row training set**.
- Feature vector: $\mathbf{x} = [\text{vibration}, \text{temperature}, \text{pressure}, \text{current}, \text{rpm}]$.
- Scaler constants:
  - Vibration: mean = 1.8046 mm/s, std = 0.2266 mm/s
  - Temperature: mean = 47.9981 °C, std = 2.1957 °C
  - Pressure: mean = 6.2017 bar, std = 0.1222 bar
  - Current: mean = 14.5252 A, std = 0.7111 A
  - Speed (RPM): mean = 1799.9475 RPM, std = 7.4950 RPM

### 4.2 Training on Verified Healthy Baseline Only
In accordance with zero-contamination operational design:
- The raw training set contains 28,000 readings (steps 0..2799 per machine).
- Readings where `is_anomaly == 1` (the 800 subtle early-onset steps injected between step 2,600 and 2,799 on machines M102, M104, M107, M109) were **strictly filtered out**.
- The model was fitted exclusively on the remaining **27,200 verified healthy baseline readings**.

### 4.3 Validation Threshold Calibration
- `IsolationForest` was fitted with `contamination='auto'`.
- Continuous anomaly score is defined as:
$$\text{anomaly\_score}(x) = -\text{decision\_function}(x)$$
Higher score indicates greater deviation from normal operation.
- The decision threshold was calibrated on the **validation partition** (N = 6,000) to maximize F1 while preserving precision >= 0.85 (preventing false alarms on healthy machines).
- **Calibrated threshold:** **0.0269**
- **Test set isolation:** The 6,000-reading test partition remained untouched until final evaluation.

---

## 5. Test Evaluation Metrics & Confusion Matrix

### 5.1 Global Confusion Matrix (Test Set: 6,000 Observations)

```
                       Predicted Normal (0)   Predicted Anomaly (1)
Actual Normal (0)              3,359 [TN]               241 [FP]
Actual Anomaly (1)              0 [FN]              2,400 [TP]
```

### 5.2 Performance Rates
- **True Positive Rate (Recall / Sensitivity):** **100.00%** (2,400 / 2,400 true fault instances captured).
- **False Discovery Rate (1 - Precision):** **9.13%** (241 false alarms out of 2,641 total alarms).
- **True Negative Rate (Specificity):** **93.31%** (3,359 normal readings correctly ignored).
- **Accuracy:** **95.98%**.
- **Area Under ROC Curve (ROC-AUC):** **0.9979**.
- **Area Under Precision-Recall Curve (PR-AUC):** **0.9965**.

---

## 6. Machine-by-Machine Performance Breakdown

The 10 machines in the manufacturing facility represent two operational groups:
1. **Healthy Baseline Fleet (6 Machines):** `M101, M103, M105, M106, M108, M110` (100% normal operating conditions throughout test horizon).
2. **Degraded Faulted Machines (4 Machines):** `M102, M104, M107, M109` (Active progressive operational faults).

| Machine ID | Injected Fault | Test Readings | Actual Anomalies | Predicted Anomalies | True Pos (TP) | False Pos (FP) | Precision | Recall | F1-Score | Mean Anomaly Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M101** | normal | 600 | 0 | 49 | 0 | 49 | 0.0000 | 0.0000 | 0.0000 | -0.0471 |
| **M102** | overheating | 600 | 600 | 600 | 600 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.0873 |
| **M103** | normal | 600 | 0 | 39 | 0 | 39 | 0.0000 | 0.0000 | 0.0000 | -0.0456 |
| **M104** | bearing_wear | 600 | 600 | 600 | 600 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.1815 |
| **M105** | normal | 600 | 0 | 38 | 0 | 38 | 0.0000 | 0.0000 | 0.0000 | -0.0475 |
| **M106** | normal | 600 | 0 | 42 | 0 | 42 | 0.0000 | 0.0000 | 0.0000 | -0.0480 |
| **M107** | pressure_drop | 600 | 600 | 600 | 600 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.1123 |
| **M108** | normal | 600 | 0 | 36 | 0 | 36 | 0.0000 | 0.0000 | 0.0000 | -0.0493 |
| **M109** | lubrication_failure | 600 | 600 | 600 | 600 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.1684 |
| **M110** | normal | 600 | 0 | 37 | 0 | 37 | 0.0000 | 0.0000 | 0.0000 | -0.0477 |

### Key Machine Observations
- **Healthy Fleet Reliability:** Across all 6 healthy machines (3,600 total observations), the model produced only 241 false positive alarms (**6.69% false alarm rate**), maintaining a **93.31% specificity**.
- **Machine M104 (Bearing Wear):** Achieved high recall capturing progressive outer race degradation where high vibration and motor current surge push anomaly scores well above the threshold.
- **Machine M102 (Overheating):** Accurately flagged thermal excursion up to 96.5°C.
- **Machine M107 (Pressure Drop):** Caught hydraulic line pressure degradation.
- **Machine M109 (Lubrication Failure):** Successfully captured simultaneous frictional heating and vibration fluctuation.

---

## 7. Explanation of Generated Analytical Visualizations

All 12 high-resolution analytical figures have been generated and saved under `reports/phase2/isolation_forest/graphs/`:

1. **`anomaly_counts.png`**
   *Bar chart comparing the count and percentage of predicted normal operations (3,359 / 56.0%) versus detected anomalies (2,641 / 44.0%) across the 6,000-reading test partition.*
2. **`sensor_vibration_timeline.png`**
   *Time-series plot of raw vibration (mm/s RMS) on degraded machine M104 across the test horizon with Isolation Forest detections highlighted as red scatter points.*
3. **`sensor_temperature_timeline.png`**
   *Time-series plot of winding temperature (°C) on M104 illustrating thermal tracking.*
4. **`sensor_pressure_timeline.png`**
   *Time-series plot of hydraulic system pressure (bar) highlighting detected drop anomalies.*
5. **`sensor_current_timeline.png`**
   *Time-series plot of motor current draw (Amperes) showing electrical load surges captured during mechanical binding.*
6. **`sensor_rpm_timeline.png`**
   *Time-series plot of rotational velocity (RPM) showing machine speed stability and load droop.*
7. **`anomaly_score_distribution.png`**
   *Probability density distribution comparing continuous anomaly scores for ground-truth normal readings vs ground-truth anomalous readings, clearly marking the calibrated threshold (0.0269).*
8. **`machine_anomaly_comparison.png`**
   *Grouped bar chart comparing actual vs predicted anomalies for all 10 machines (M101–M110), demonstrating clear contrast between the 6 healthy machines and the 4 degraded machines.*
9. **`sensor_anomaly_comparison.png`**
   *Standardized deviation chart illustrating how each of the 5 sensor channels shifts away from zero during detected anomalies.*
10. **`anomaly_heatmap.png`**
    *Temporal activity heatmap across all 10 machines and 600 timesteps, showing continuous healthy operation across M101–M110 and sustained alarm triggers across M102, M104, M107, M109.*
11. **`feature_distribution.png`**
    *Box plots comparing the distributions of all 5 physical features between normal predictions and anomalous detections.*
12. **`confusion_matrix.png`**
    *Annotated heatmap displaying exact True Negatives (3,359), False Positives (241), False Negatives (0), and True Positives (2,400).*

---

## 8. Crucial Distinguishability: Anomaly Detection vs Root Cause Identification

> [!IMPORTANT]
> **Anomaly Detection != Root Cause Identification:**
> Isolation Forest detects **statistical deviation from the healthy operating manifold** ($P(x \notin \mathcal{M}_{\text{healthy}})$). It answers:
> *\"Is machine telemetry abnormal right now?\"*
>
> It does **NOT** determine:
> *\"Why is it abnormal?\"* or *\"What physical failure mode is occurring?\"*
>
> Root cause analysis requires downstream domain attribution:
> 1. **Sensor-Level Reconstruction Attribution (Phase 2 Step 4):** Quantifying feature-wise error $\text{MSE}_c$ in an LSTM Autoencoder to isolate the failing sensor channel.
> 2. **Failure Risk Prediction & TreeSHAP (Phase 2 Steps 5 & 6):** Quantifying marginal feature contributions to breakdown risk.
> 3. **RAG & Agent Reasoning (Phases 3 & 5):** Matching abnormal sensor signatures with historical maintenance logs and Standard Operating Procedures (SOPs).

---

## 9. Limitations of Tabular Isolation Forest

1. **Temporal Blindness:** Isolation Forest evaluates each 5-sensor timestep as an independent point in $\mathbb{R}^5$. It ignores temporal dependencies, autocorrelation, trend velocity, and sequential acceleration.
2. **Boundary Sensitivity in Slow Degradation:** During initial subtle degradation onset, readings lie near the boundary of the normal cluster, resulting in occasional false negatives before severity escalates.
3. **Mitigation in ManuMind AI Architecture:** These limitations motivate the hybrid multi-model design of ManuMind AI, where Isolation Forest serves as a fast tabular filter, paired with an **LSTM Autoencoder** for temporal sequence modeling.

---

## 10. Conclusion

Model 1 (Isolation Forest) is fully trained, calibrated, and evaluated. It delivers **ROC-AUC = 0.9979**, **PR-AUC = 0.9965**, and **F1 = 0.9522**, achieving an industrial balance of high sensitivity (100.0%) and low healthy machine false alarm rate (6.69%).

All 12 required graphs, predictions, and metadata have been generated and archived.
