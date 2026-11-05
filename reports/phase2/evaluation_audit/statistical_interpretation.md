# ManuMind AI — Independent Audit: Statistical Interpretation & Uncertainty Analysis

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.2 — Audit F: Statistical Interpretation & Uncertainty Bounds
**Auditor:** Senior ML Evaluation Engineer & Independent Auditor
**Date:** November 2026 (Updated & Corrected)
**Status:** **AUDITED — STATISTICAL DEPENDENCE, EVENT GROUPING & BOUNDS FORMALIZED**

---

## 1. Executive Summary

In machine learning evaluations for industrial telemetry, standard performance metrics (Accuracy, Precision, Recall, F1) often rely on the assumption of **independent and identically distributed (i.i.d.) observations**.

In sequential time-series monitoring, this assumption is frequently violated by three distinct dependencies:
1. **Sliding-Window Overlap:** With window size 30 and stride 10, adjacent sequence windows share $66.67\%$ of their raw observations.
2. **Serial Temporal Autocorrelation:** Sensor readings from the same machine at timestep $t$ are physically dependent on preceding timesteps.
3. **Clustered Machine Allocation:** All 40,000 readings and 3,940 windows originate from a fixed set of only 10 physical machines.

This document formalizes the statistical interpretation of the reported metrics, establishes uncertainty bounds for non-overlapping windows, and contrasts **point-level**, **window-level**, and **event-level** evaluation.

---

## 2. Statistical Analysis of Sliding-Window Dependence

### 2.1 The Overlap Mechanism
- **Window Size ($W$):** 30 timesteps ($150\text{ minutes}$).
- **Stride ($S$):** 10 timesteps ($50\text{ minutes}$).
- **Shared Timesteps:** $W - S = 20\text{ timesteps}$ ($100\text{ minutes}$).
- **Fraction Shared:** $\frac{20}{30} = \mathbf{66.67\%}$.

### 2.2 Autocorrelation & Data Reuse
Because adjacent windows share 20 physical readings:
- **Prediction Autocorrelation:** Pearson $r = \mathbf{0.950}$ between $\hat{y}_k$ and $\hat{y}_{k+1}$.
- **Reconstruction Error Autocorrelation:** Pearson $r = \mathbf{0.957}$ between $\text{MSE}_k$ and $\text{MSE}_{k+1}$.
- **Reading Reuse Factor:** Across the 58 test windows per machine, $58 \times 30 = 1,740$ window-point evaluations occur over 600 unique physical observations (a **$2.9\times$ reuse factor**).

Treating nominal overlapping windows as independent observations artificially deflates standard errors by approximately $\sqrt{2.9} \approx 1.7\times$, producing artificially narrow confidence intervals.

---

## 3. Evaluation on Non-Overlapping Windows (Stride 30)

To eliminate the artificial inflation caused by shared sensor readings, an additional evaluation was conducted using non-overlapping sequence windows:
- **Sampling Scheme:** Stride = 30 timesteps ($150\text{ minutes}$, zero shared readings between consecutive windows).
- **Sample Count:** Exactly 20 non-overlapping windows per machine $\times$ 10 machines = **$200$ non-overlapping evaluation windows**.
- **Distribution:** 120 normal baseline windows (from 6 healthy machines), 80 anomalous windows (from 4 faulted machines `M102, M104, M107, M109`).

### Statistical Independence Clarification:
> [!IMPORTANT]
> **Clarification on "Non-Overlapping Windows" vs. "Statistical Independence":**
> - While these 200 windows **do not share sensor readings**, they **cannot automatically be assumed to represent 200 statistically independent observations**.
> - The 200 windows still originate from only **10 physical machines** (20 longitudinal windows per machine).
> - Temporal autocorrelation within each machine and asset-level clustering remain present.
> - Therefore, the true effective sample size for fleet-level hypothesis testing is bounded between $N=10$ (independent physical machines) and $N=200$ (disjoint temporal windows).
> - We adopt the term **"non-overlapping evaluation windows"** rather than "completely independent samples."

### 95% Wilson Score Confidence Intervals Table

| Performance Metric | Nominal Overlapping ($N=580$) | Non-Overlapping Windows ($N=200$) | 95% Wilson Confidence Interval | Statistical Assessment |
|---|:---:|:---:|:---:|---|
| **Accuracy** | $99.31\%$ | **$100.00\%$** | **$[98.12\%, 100.00\%]$** | High sequence classification accuracy confirmed |
| **Precision** | $98.31\%$ | **$100.00\%$** | **$[95.42\%, 100.00\%]$** | Zero false alarms in non-overlapping sample |
| **Recall** | $100.00\%$ | **$100.00\%$** | **$[95.42\%, 100.00\%]$** | All 80 non-overlapping anomaly windows caught |
| **F1-Score** | $0.9915$ | **$1.0000$** | $[0.9542, 1.0000]$ | High harmonic operational balance |
| **Specificity** | $98.85\%$ | **$100.00\%$** | **$[96.90\%, 100.00\%]$** | All 120 non-overlapping normal windows passed |
| **False Positive Rate** | $1.15\%$ | **$0.00\%$** | $[0.00\%, 3.10\%]$ | False alarm ceiling bounded under $3.1\%$ |
| **ROC-AUC** | $1.0000$ | **$1.0000$** | $[1.0000, 1.0000]$ | Complete separation between normal and faulted windows |

### Key Finding:
The non-overlapping evaluation confirms that **high test metrics are not an artifact of window overlap**. When window overlap is removed ($N=200$ non-overlapping windows), precision and recall remain $100.0\%$.

---

## 4. Multi-Granularity Framework: Point, Window, and Event

Industrial anomaly detection operates across three hierarchical granularities:

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: Point-Level Evaluation (Raw Timesteps, N = 6,000 Readings)    │
├────────────────────────────────────────────────────────────────────────┤
│ • Unit of Evaluation: Single 5-minute telemetry row.                   │
│ • Isolation Forest Metrics: Acc = 95.98%, Prec = 90.87%, Rec = 100.0%  │
│ • False Positive Rate: 6.69% (241 false alarms out of 3,600 normal).   │
│ • Operational Reality: High false alarm frequency causes alert fatigue.│
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: Window-Level Evaluation (30-Step Sequences, N = 580 / 200)    │
├────────────────────────────────────────────────────────────────────────┤
│ • Unit of Evaluation: 150-minute non-overlapping or sliding window.    │
│ • LSTM Autoencoder Metrics: Acc = 99.31%, Prec = 98.31%, Rec = 100.0%  │
│ • False Positive Rate: 1.15% (4/348 overlapping) or 0.00% (0/120 non-ov│
│ • Operational Reality: Temporal persistence eliminates spurious noise. │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3: Event-Level Evaluation (Machine Fault Incidents, N = 10 Assets│
├────────────────────────────────────────────────────────────────────────┤
│ • Unit of Evaluation: Entire physical asset degradation incident.      │
│ • Fault Incidents Evaluated: 4 faulted machines (M102, M104, M107, M109│
│ • Healthy Fleet Evaluated: 6 normal machines (M101, M103, M105, etc.)  │
│ • Event Detection Recall: 4 / 4 = 100.00%                              │
│ • False Event Alarms: 0 / 6 = 0.00% (No healthy machine flagged)       │
│ • Statistical Context: Evaluated on exactly 10 machines in synthetic   │
│   data; repeated readings are NOT independent machine-level events.    │
└────────────────────────────────────────────────────────────────────────┘
```

### Event-Level Clarification:
- The event-level evaluation is based on **exactly 10 physical machine assets** (4 faulted, 6 healthy).
- While 100% of the 4 failure incidents were detected and 0% of the 6 healthy machines were falsely condemned, this represents a benchmark result on this synthetic 10-machine dataset.
- It **does not constitute statistical proof of generalization across broad industrial fleets**, where machine variance, environmental noise, and failure mode diversity are significantly higher.
- Multiple readings or sequence windows from one machine are repeated longitudinal measures of a single physical asset, not independent machine-level events.

---

## 5. Early-Warning Claims: Valid vs. Invalid Interpretations

### What CAN Be Rigorously Claimed:
1. **Time to Synthetic Severe-Degradation Boundary:** Both models provide **$60.9$ to $83.3\text{ hours}$ ($2.5\text{ to }3.5\text{ days}$)** of advance warning between the first detected anomaly and the synthetic severe-degradation boundary (step 3,600).
2. **Within-Machine Progressive Sensitivity:** Continuous anomaly scores scale progressively with physical fault degradation within each machine ($R > 0.94$).
3. **Noise Filtering via Temporal Aggregation:** Slicing 30-timestep windows reduces false alarms from $6.69\%$ (point-level) down to $1.15\%$ (overlapping windows) and $0.00\%$ (non-overlapping windows).
4. **Plant-Level Machine Triage:** All 4 faulted machines triggered persistent alerts prior to the severe-degradation stage.

### What CANNOT Be Claimed:
1. **Catastrophic Breakdown Lead Time:** Step 3,600 marks the beginning of the synthetic severe degradation stage ($progression = 0.714$), not an explicit mechanical breakdown or equipment seizure timestamp. Therefore, warning time must be stated as **"time to the synthetic severe-degradation boundary"**, not "time to catastrophic failure."
2. **Sustained Alert at Earliest Detection:** The reported earliest detection timestamps represent **the first individual threshold-crossing event** (single point or single window). In Stage 1 (Incipient Degradation), alerts are intermittent ($51.7\%\text{--}77.1\%$ recall) until Stage 2 ($progression > 0.43$) when alerts become 100% sustained.
3. **i.i.d. Window Independence:** One cannot treat 200 non-overlapping windows as 200 independent fleet samples; machine clustering remains present.
4. **Generalization to Unseen Industrial Fleets:** Zero-shot cross-asset diagnostic transfer cannot be established from a 10-machine dataset where each fault mode is present on only one asset.
