# ManuMind AI — Independent Audit: Fault Progression & Early-Warning Analysis

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.2 — Audit C: Early-Warning Detection & Prognostic Horizon
**Auditor:** Senior ML Evaluation Engineer & Independent Auditor
**Date:** November 2026 (Updated & Corrected)
**Status:** **AUDITED — TERMINOLOGY CLARIFIED & DETECTION DELAYS RIGOROUSLY QUANTIFIED**

---

## 1. Executive Summary

This audit evaluated whether **Model 1 (Isolation Forest)** and **Model 2 (LSTM Autoencoder)** can detect physical machine degradation in its early incipient stages, and whether the system provides actionable advance notice before equipment reaches severe degradation stages.

The investigation analyzed all 4 faulted machines (`M102, M104, M107, M109`) across their entire 4,000-timestep lifecycle ($20,000 \text{ minutes} \approx 333.3 \text{ hours} \approx 13.9 \text{ days}$).

---

## 2. Rigorous Terminology & Evaluation Metrics

To maintain scientific integrity, three distinct temporal intervals must be strictly distinguished:

1. **Fault Detection Delay ($D_{\text{detect}}$):**
   The elapsed time between the defined physical fault-onset timestamp ($T_{\text{onset}} = \text{Step } 2,600$) and the earliest detected anomaly timestamp ($T_{\text{det}}$):
   $$D_{\text{detect}} = (T_{\text{det}} - T_{\text{onset}}) \times 5\text{ minutes}$$

2. **Time to Synthetic Severe-Degradation Boundary ($T_{\text{severe\_margin}}$):**
   The time between the earliest detected anomaly timestamp ($T_{\text{det}}$) and the synthetic severe-degradation boundary ($T_{\text{severe}} = \text{Step } 3,600$, where $progression = 0.714$):
   $$T_{\text{severe\_margin}} = (T_{\text{severe}} - T_{\text{det}}) \times 5\text{ minutes}$$

3. **Actual Catastrophic Failure Lead Time:**
   > [!IMPORTANT]
   > **Clarification on Catastrophic Breakdown vs. Stage Boundary:**
   > In the synthetic data generator (`ml/data_generator/generate_sensor_data.py`), step 3,600 marks the **start of Stage 3 (severe degradation)** where $progression \ge 0.714$. The generator does **not** simulate an unhandled catastrophic seizure or emergency shutdown timestamp. Therefore, we do not claim actual equipment breakdown lead time. We state the metric as:
   > **"Time between the first detected anomaly and the synthetic severe-degradation boundary."**

---

## 3. Earliest Threshold Crossing vs. Sustained Detection

### Evaluation Protocol Clarification:
- The earliest detection timestamp reported below represents **the first individual threshold-crossing event** (a single reading exceeding $\tau_{\text{IF}} = 0.0269$ for Isolation Forest, or a single 30-step window exceeding $\tau_{\text{LSTM}} = 0.9015$ for the Autoencoder).
- **No persistence rule** (such as requiring $k$-of-$m$ consecutive alerts) was applied in this calculation.
- Consequently, this earliest alert may represent an **isolated early-onset transient alert** rather than a fully confirmed, sustained alarm state.
- **Reconciliation with Stage 1 Recall:** In Stage 1 (Incipient Degradation, steps 2600–3199), detection is intermittent because subtle physical deviations periodically dip below thresholds ($51.67\%\text{--}64.83\%$ recall for Isolation Forest, and $56.67\%\text{--}98.33\%$ recall for LSTM Autoencoder). Sustained, continuous detection ($100.0\%$ recall) begins once equipment reaches Stage 2 ($progression > 0.43$, step 3200).

---

## 4. Detection Delay & Time to Severe-Stage Boundary Verification

The timestamps and delay calculations were audited across all four machines:

- **Fault Onset:** Step 2,600 (`2026-10-31 15:20:00`)
- **Severe Stage Boundary:** Step 3,600 (`2026-11-04 02:40:00`)
- **Elapsed Steps Between Onset and Severe Boundary:** $3600 - 2600 = 1000\text{ steps} = 5,000\text{ minutes} = \mathbf{83.33\text{ hours}}$.

### Verified Temporal Summary Table

| Machine ID | Failure Mechanism | Model | Earliest Detection Step | Earliest Detection Timestamp | Detection Delay (Minutes) | Detection Delay (Hours) | Time to Severe-Stage Boundary (Hours) | Evaluation Nature |
|---|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **M104** | Bearing Spalling | Isolation Forest | Step 2600 | 2026-10-31 15:20:00 | **0 min** | 0.00 h | **83.33 h (3.47 Days)** | First point threshold crossing |
| | | LSTM Autoencoder | Step 2609 | 2026-10-31 16:05:00 | **45 min** | 0.75 h | **82.58 h (3.44 Days)** | First window threshold crossing |
| **M107** | Pressure Seal Drop | Isolation Forest | Step 2602 | 2026-10-31 15:30:00 | **10 min** | 0.17 h | **83.17 h (3.47 Days)** | First point threshold crossing |
| | | LSTM Autoencoder | Step 2629 | 2026-10-31 17:45:00 | **145 min** | 2.42 h | **80.92 h (3.37 Days)** | First window threshold crossing |
| **M109** | Lubrication Friction | Isolation Forest | Step 2605 | 2026-10-31 15:45:00 | **25 min** | 0.42 h | **82.92 h (3.45 Days)** | First point threshold crossing |
| | | LSTM Autoencoder | Step 2619 | 2026-10-31 16:55:00 | **95 min** | 1.58 h | **81.75 h (3.41 Days)** | First window threshold crossing |
| **M102** | Hydraulic Overheating | Isolation Forest | Step 2611 | 2026-10-31 16:15:00 | **55 min** | 0.92 h | **82.42 h (3.43 Days)** | First point threshold crossing |
| | | LSTM Autoencoder | Step 2869 | 2026-11-01 13:45:00 | **1345 min** | 22.42 h | **60.92 h (2.54 Days)** | First window threshold crossing |

### Verification of M102 LSTM Delay (22.4 Hours):
- Fault onset at step 2,600: `2026-10-31 15:20:00`.
- Earliest LSTM window ending at step 2,869: `2026-11-01 13:45:00`.
- Step difference: $2,869 - 2,600 = \mathbf{269\text{ steps}}$.
- Time difference: $269 \times 5\text{ minutes} = \mathbf{1,345\text{ minutes}} = \mathbf{22.4167\text{ hours}}$ (verified accurate).
- Time from step 2,869 to step 3,600: $(3,600 - 2,869) \times 5 = 731 \times 5 = 3,655\text{ minutes} = \mathbf{60.9167\text{ hours}}$ (verified accurate).
- **Physical Reason for Delay:** The nominal ambient temperature cycle modulates oil temperature by $\pm 2.5^\circ\text{C}$ on a 24-hour diurnal period. During early radiator clogging, temperature rose by only $+1.5^\circ\text{C}$ to $+2.0^\circ\text{C}$, which remained within the learned normal diurnal envelope until the cumulative rise exceeded the threshold. Even with this delay, **$60.92\text{ hours}$ ($2.54\text{ days}$)** of advance warning remained before the severe stage.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/fault_progression_detection_lead_time.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/fault_progression_detection_lead_time.png)

---

## 5. Stage-by-Stage Performance Comparison

### Table: Model Detection Performance Across the 4 Lifecycle Stages

| Machine & Model | Stage 0 (Normal Baseline) | Stage 1 (Incipient Degradation) | Stage 2 (Moderate Degradation) | Stage 3 (Severe Failure) |
|---|:---:|:---:|:---:|:---:|
| **M102 (Overheating)** | | | | |
| *Isolation Forest (Point)* | FPR = 6.81% | **Recall = 51.67%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Anomaly Score = -0.0469 | Mean Score = +0.0231 | Mean Score = +0.0876 | Mean Score = +0.0878 |
| *LSTM Autoencoder (Seq)* | FPR = 1.16% | **Recall = 56.67%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Reconstruction MSE = 0.7004 | Mean MSE = 1.8361 | Mean MSE = 20.7264 | Mean MSE = 73.9964 |
| **M104 (Bearing Wear)** | | | | |
| *Isolation Forest (Point)* | FPR = 7.08% | **Recall = 63.83%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Anomaly Score = -0.0473 | Mean Score = +0.0446 | Mean Score = +0.1498 | Mean Score = +0.1888 |
| *LSTM Autoencoder (Seq)* | FPR = 1.55% | **Recall = 98.33%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Reconstruction MSE = 0.6962 | Mean MSE = 2.7612 | Mean MSE = 35.4464 | Mean MSE = 171.7973 |
| **M107 (Pressure Drop)** | | | | |
| *Isolation Forest (Point)* | FPR = 6.73% | **Recall = 62.50%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Anomaly Score = -0.0446 | Mean Score = +0.0419 | Mean Score = +0.1109 | Mean Score = +0.1114 |
| *LSTM Autoencoder (Seq)* | FPR = 6.20% | **Recall = 61.67%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Reconstruction MSE = 0.7237 | Mean MSE = 3.3465 | Mean MSE = 41.3504 | Mean MSE = 128.3309 |
| **M109 (Lubrication)** | | | | |
| *Isolation Forest (Point)* | FPR = 6.58% | **Recall = 64.83%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Anomaly Score = -0.0474 | Mean Score = +0.0652 | Mean Score = +0.1661 | Mean Score = +0.1899 |
| *LSTM Autoencoder (Seq)* | FPR = 0.78% | **Recall = 91.67%** | **Recall = 100.0%** | **Recall = 100.0%** |
| | Mean Reconstruction MSE = 0.6837 | Mean MSE = 2.8413 | Mean MSE = 36.1956 | Mean MSE = 134.4074 |

---

## 6. Audit Conclusion
1. **Early Incipient Sensitivity:** Both models trigger their first individual alerts during Stage 1. However, detection in Stage 1 is intermittent ($51.7\%\text{--}77.1\%$ recall) due to early fault fluctuations near the decision threshold.
2. **Prognostic Margin:** The models provide **$60.9$ to $83.3\text{ hours}$ ($2.5$ to $3.5$ days)** between the first alert and the synthetic severe-degradation boundary, offering ample time for maintenance intervention before severe damage occurs.
