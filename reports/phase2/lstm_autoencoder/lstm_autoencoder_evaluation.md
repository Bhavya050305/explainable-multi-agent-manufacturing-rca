# ManuMind AI — Model 2: LSTM Autoencoder Anomaly Detection Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science
**Component:** Model 2 — Temporal Sequence Anomaly Detection (LSTM Autoencoder)
**Date:** November 2026
**Status:** **TRAINED, CALIBRATED, AND EVALUATED ON UNTOUCHED TEST SEQUENCES**

---

## 1. Executive Summary

This report documents the design, training, calibration, and benchmark evaluation of **Model 2: LSTM Autoencoder** for multivariate time-series anomaly detection in industrial manufacturing telemetry.

The autoencoder was trained **exclusively on verified normal training sequence windows** (N = 2,700 sequences, 80 anomalous sequences strictly excluded) across 5 standardized physical channels: Vibration, Temperature, Pressure, Current, and RPM. It was calibrated on the validation partition (N = 580 sequences) and evaluated on the untouched test partition (N = 580 sequences).

### Core Test Benchmark Metrics

| Metric | Target Standard | Realized Value | Operational Assessment |
|---|---|---:|:---:|
| **ROC-AUC** | >= 0.900 | **1.0000** | **Outstanding temporal discrimination** |
| **PR-AUC (Average Precision)** | >= 0.850 | **1.0000** | **High precision-recall curve dominance** |
| **F1-Score** | >= 0.850 | **0.9915** | **Strong harmonic balance** |
| **Precision** | >= 0.800 | **0.9831** | **Reliable fault alarms** |
| **Recall (Sensitivity)** | >= 0.850 | **1.0000** | **High temporal fault capture** |
| **Accuracy** | >= 0.850 | **0.9931** | **High overall sequence fidelity** |
| **Healthy Specificity** | >= 0.900 | **0.9885** | **98.9% specificity on healthy fleet** |
| **Healthy False Positive Rate** | <= 0.100 | **0.0115** | **Only 1.1% false alarms** |

---

## 2. Model Architecture & Training Configuration

The LSTM Autoencoder utilizes an Encoder-Decoder structure with temporal bottleneck compression:

```
Input Sequence (30 timesteps, 5 features)
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ Encoder:                                               │
│ - LSTM(64 units, activation='tanh', return_seq=True)   │
│ - Dropout(0.1)                                         │
│ - LSTM(32 units, activation='tanh', return_seq=False)  │
└────────────────────────────────────────────────────────┘
       │
       ▼ [Latent Bottleneck Representation: R^32]
┌────────────────────────────────────────────────────────┐
│ Decoder:                                               │
│ - RepeatVector(30 timesteps)                           │
│ - LSTM(32 units, activation='tanh', return_seq=True)   │
│ - Dropout(0.1)                                         │
│ - LSTM(64 units, activation='tanh', return_seq=True)   │
│ - TimeDistributed(Dense(5 features))                   │
└────────────────────────────────────────────────────────┘
       │
       ▼
Reconstructed Sequence (30 timesteps, 5 features)
```

### Training Hyperparameters & Convergence
- **Normal Training Sequences Used:** 2700 (100% normal)
- **Anomalous Training Sequences Excluded:** 80
- **Batch Size:** 32
- **Learning Rate:** 0.001 (Adam optimizer)
- **Epochs Trained:** 50
- **Final Training Loss (MSE):** 0.706363
- **Best Validation Loss (MSE):** 0.688796
- **Random Seed:** 42

---

## 3. Threshold Calibration Methodology

Reconstruction error is calculated per sequence using Mean Squared Error (MSE):
$$\text{MSE}(X) = \frac{1}{W \cdot C} \sum_{t=1}^W \sum_{c=1}^C (x_{t,c} - \hat{x}_{t,c})^2$$
where $W=30$ is window size and $C=5$ is the number of sensor channels.

### Calibration on Validation Partition (N = 580)
- Errors were first evaluated exclusively on **normal validation sequences** (N = 348).
- **99th Percentile Threshold:** **0.901464** (Selected industrial threshold)
- **Validation Performance at Selected Threshold:**
  - Accuracy: 0.9828
  - Precision: 0.9826
  - Recall: 0.9741
  - F1-Score: 0.9784
  - Specificity: 0.9885
  - False Positive Rate: 0.0115

---

## 4. Test Set Evaluation & Confusion Matrix

### Confusion Matrix (Test Set: 580 Sequence Windows)
```
                       Predicted Normal (0)   Predicted Anomaly (1)
Actual Normal (0)                344 [TN]                  4 [FP]
Actual Anomaly (1)                 0 [FN]                 232 [TP]
```

### Detailed Performance Rates
- **True Positive Rate (Recall):** **100.00%** (232 / 232 true anomaly windows caught).
- **False Discovery Rate (1 - Precision):** **1.69%** (4 false alarms out of 236 total alarms).
- **True Negative Rate (Specificity):** **98.85%** (344 / 348 normal windows correctly passed).
- **False Positive Rate:** **1.15%**.
- **Accuracy:** **99.31%**.
- **ROC-AUC:** **1.0000**.
- **PR-AUC:** **1.0000**.

---

## 5. Machine-by-Machine Sequence Breakdown

| Machine ID | Operating Health | Injected Fault | Test Windows | Actual Anomalies | Predicted Anomalies | TP | FP | Precision | Recall | F1-Score | Mean MSE Error |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M101** | Healthy Fleet | normal | 58 | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.685150 |
| **M102** | Degraded Fleet | overheating | 58 | 58 | 58 | 58 | 0 | 1.0000 | 1.0000 | 1.0000 | 60.941930 |
| **M103** | Healthy Fleet | normal | 58 | 0 | 2 | 0 | 2 | 0.0000 | 0.0000 | 0.0000 | 0.697629 |
| **M104** | Degraded Fleet | bearing_wear | 58 | 58 | 58 | 58 | 0 | 1.0000 | 1.0000 | 1.0000 | 135.398430 |
| **M105** | Healthy Fleet | normal | 58 | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.703476 |
| **M106** | Healthy Fleet | normal | 58 | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.687882 |
| **M107** | Degraded Fleet | pressure_drop | 58 | 58 | 58 | 58 | 0 | 1.0000 | 1.0000 | 1.0000 | 106.291510 |
| **M108** | Healthy Fleet | normal | 58 | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.688620 |
| **M109** | Degraded Fleet | lubrication_failure | 58 | 58 | 58 | 58 | 0 | 1.0000 | 1.0000 | 1.0000 | 96.136206 |
| **M110** | Healthy Fleet | normal | 58 | 0 | 2 | 0 | 2 | 0.0000 | 0.0000 | 0.0000 | 0.710244 |

### Key Machine Observations
- **Healthy Fleet Reliability:** Across all 6 healthy machines (348 total test sequences), only 4 false positive alarms occurred (**1.15% FPR**), achieving **98.85% Specificity**.
- **M104 (Bearing Wear):** Progressive bearing vibration and current surges produced high reconstruction error exceeding the threshold across all anomalous test windows.
- **M102 (Overheating):** High thermal residuals drive strong reconstruction penalties.
- **M107 (Pressure Drop) & M109 (Lubrication):** Accurately identified across the progressive test horizon.

---

## 6. Model Comparison: Isolation Forest vs LSTM Autoencoder

| Performance Characteristic | Model 1: Isolation Forest | Model 2: LSTM Autoencoder | Architectural Advantage |
|---|:---:|:---:|---|
| **Evaluation Granularity** | Tabular (Single Timestep) | Sequence (30-step Window) | Sequence modeling captures 2.5h dynamic history |
| **Accuracy** | 0.9598 | 0.9931 | Comparable high classification accuracy |
| **Precision** | 0.9087 | 0.9831 | High alarm credibility across both |
| **Recall (Sensitivity)** | 1.0000 | 1.0000 | High fault capture rate |
| **F1-Score** | 0.9522 | 0.9915 | High harmonic operational score |
| **ROC-AUC** | 0.9979 | 1.0000 | Near-perfect separation under both paradigms |
| **PR-AUC** | 0.9965 | 1.0000 | High area under precision-recall curve |
| **False Positive Rate** | 6.69% | 1.15% | Both control false alarms under 10% |

### Complementary Roles in ManuMind AI
1. **Isolation Forest (Fast Edge Filter):** Operates on instantaneous tabular readings ($O(1)$ memory, $< 0.2\text{ ms}$ latency). Useful for instantaneous threshold violation screening.
2. **LSTM Autoencoder (Temporal Context & Root Attribution):** Slices 30 timesteps ($2.5\text{ hours}$), capturing multi-sensor trend drift and rate of change. Crucially, the autoencoder provides **channel-wise reconstruction error** ($(\mathbf{x}_c - \hat{\mathbf{x}}_c)^2$) enabling direct sensor-level attribution in Step 4.

---

## 7. Crucial Conceptual Distinctions & Industrial Nuances

### 7.1 Anomaly Detection vs Root Cause Identification
> [!IMPORTANT]
> **Anomaly Detection != Root Cause Identification:**
> The LSTM Autoencoder reconstruction error indicates **that** the recent 30-step temporal pattern deviates from the learned normal operational dynamics. It flags an anomaly.
>
> It does **not** identify the failure mechanism (e.g. inner race fatigue vs lubrication breakdown).
> In ManuMind AI:
> 1. **Sensor Attribution (Step 4)** determines *which sensor* contributed most to the error.
> 2. **Failure Risk Prediction & TreeSHAP (Steps 5 & 6)** quantifies *how soon* failure will occur and *which factors* drive risk.
> 3. **RAG & LangGraph Agents (Phases 3 & 5)** synthesizes maintenance logs and SOPs to determine *the actionable corrective action*.

### 7.2 Operational Impact of False Positives and False Negatives
- **False Positives (Type I Error):** Cause nuisance alarms, operator alert fatigue, unnecessary maintenance inspections, and potential unwarranted production pauses.
- **False Negatives (Type II Error):** Critical equipment breakdown escapes detection, resulting in catastrophic unmanaged machine seizure, tool wreckage, safety hazards, and unplanned plant downtime costing thousands of dollars per hour.
- **Industrial Tuning:** The 99th percentile threshold prioritizes high sensitivity while bounding false alarms to $\le 1.0\%$ on normal baseline sequences.

### 7.3 Synthetic Data vs Real-World Generalization
- While the synthetic industrial dataset rigorously models 3-shift factory cycles, thermal diurnal drifts, and progressive mechanical faults, real-world manufacturing plants exhibit unmodeled non-stationary noise, seasonal ambient swings, raw material variance, and sensor drift.
- In production deployment, transfer learning and continual baseline calibration are required.

---

## 8. Analytical Visualizations Gallery

All 8 high-resolution analytical PNG plots are saved in `reports/phase2/lstm_autoencoder/graphs/`:
1. **`training_vs_validation_loss.png`** — Training and validation MSE loss curves across training epochs.
2. **`original_vs_reconstructed_sensor_sequences.png`** — Side-by-side comparison of original vs reconstructed 5-channel signals for normal vs anomalous sequence.
3. **`reconstruction_error_distribution.png`** — Histogram and KDE of sequence reconstruction errors across the test partition.
4. **`normal_vs_anomalous_reconstruction_errors.png`** — KDE comparison of reconstruction error density for normal vs anomalous ground truth.
5. **`threshold_visualization.png`** — Scatter plot of test sequence errors highlighting the calibrated threshold and anomaly detection zone.
6. **`anomaly_timeline.png`** — Trajectory of sequence reconstruction errors on machine M104.
7. **`per_machine_anomaly_comparison.png`** — Grouped bar chart of actual vs detected anomalies for machines M101–M110.
8. **`confusion_matrix.png`** — Annotated confusion matrix heatmap on the test partition.

---

## 9. Conclusion

Model 2 (LSTM Autoencoder) is fully trained, calibrated, and evaluated. It delivers **ROC-AUC = 1.0000**, **PR-AUC = 1.0000**, and **F1 = 0.9915**, confirming high sequence anomaly detection capability.
