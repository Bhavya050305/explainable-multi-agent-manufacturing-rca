# ManuMind AI — Phase 2, Step 3.2: Comprehensive Evaluation Fairness, Fault Progression & Early-Warning Audit Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.2 — Evaluation Fairness, Fault Progression, and Early Warning Audit
**Auditor:** Senior ML Evaluation Engineer & Independent Auditor
**Date:** November 2026
**Status:** **AUDIT COMPLETE — FINAL VERDICT: APPROVED WITH DOCUMENTED EVALUATION PROTOCOLS**

---

## 1. Executive Summary & Audit Context

Following the completion of **Phase 2, Step 3.1** (which proved zero data leakage and identified synthetic fault separability as the primary driver of near-perfect test scores), this follow-up audit addressed four specific evaluation fairness questions:

1. **Sliding-Window Dependence:** Did the $66.7\%$ overlap between adjacent sliding windows artificially inflate the reported test metrics?
2. **Evaluation Granularity Fairness:** How does Model 1 (Isolation Forest) perform when aggregated to the exact same 30-timestep sequence level as Model 2 (LSTM Autoencoder)?
3. **Incipient Fault Progression & Early Warning:** Can the models detect faults in their early stages (steps 2,600 to 3,199), and what is the actionable warning lead time before catastrophic failure?
4. **Within-Machine Detection vs. Machine Identity:** Do the models detect the temporal transition from health to fault *within the same machine*, or do they merely recognize static machine identities?

---

## 2. Key Audit Findings & Summary Table

### 2.1 Master Findings Matrix

| Audit Area | Scope | Key Finding | Status |
|---|---|---|:---:|
| **Audit A: Window Dependence** | Stride 10 ($N=580$) vs. Stride 30 ($N=200$) | Overlapping windows share $66.7\%$ data ($r = 0.96$ error autocorrelation). When evaluated on **200 non-overlapping evaluation windows** (zero shared readings, though clustered by 10 machines), accuracy and recall remain **$100.00\%$** (Precision $95.4\%\text{--}100\%$). Window overlap did **not** inflate test partition performance. | **PASS** |
| **Audit B: Common Granularity** | IF vs. LSTM on identical 580 sequence windows | Aggregating IF point scores to sequence level (Mean Score or Fraction $\ge 37\%$) eliminates isolated false alarms, raising IF sequence F1 from $0.952$ to **$1.000$** (matching LSTM at $0.9915$). Both LSTM and IF aggregation thresholds were calibrated strictly on validation data with test data completely unobserved. | **PASS** |
| **Audit C: Early Warning** | 4-Stage lifecycle across 4,000 steps | Fault onset occurs at Step 2,600. Earliest detection occurs with **0 to 55 minutes delay** on 3 machines (and 22.4h on M102 due to diurnal thermal masking). Time between the first detected anomaly and the synthetic severe-degradation boundary (Step 3600) is **60.9 to 83.3 hours**. Note: Synthetic generator simulates continuous degradation, not mechanical catastrophic destruction. | **PASS** |
| **Audit D: Within-Machine Sensitivity** | In-machine baseline vs. fault transition | During normal periods (steps 0–2599), anomaly scores are low (IF = $-0.047$, LSTM MSE = $0.69$). Scores track synthetic degradation after step 2,600 ($R > 0.94$ with synthetic severity parameter). Provides evidence that models respond to temporal fault progression; reduces concern about machine-identity confounding without completely eliminating it. | **PASS** |
| **Audit E: Holdout Diagnostic** | Unseen fleet holdout verification | Verified that the $48.86\%\text{--}76.14\%$ recall in the holdout diagnostic reflects lifetime evaluation across subtle incipient steps ($progression < 0.25$). Late-stage recall on unseen machines is $100.0\%$. | **VERIFIED** |
| **Audit F: Statistical Hierarchy** | Point vs. Window vs. Event levels | Point level: $6.69\%$ FPR. Window level: $1.15\%$ FPR. Event level: Benchmark on 10 machines (4 faulted, 6 healthy) shows 100% detection with 0% false event alarms; longitudinal windows are repeated measures, not independent fleet events. | **FORMALIZED** |

---

## 3. Audit A — Sliding-Window Dependence Analysis

### 3.1 Overlapping vs. Non-Overlapping Benchmark Comparison

The test partition ($600$ readings per machine $\times$ 10 machines $= 6,000$ readings) was evaluated under two configurations:
- **Original Overlapping Windows:** Window size 30, Stride 10 $\to$ **$580$ windows** (Adjacent windows share $20 / 30 = 66.67\%$ of data).
- **Non-Overlapping Evaluation Windows:** Window size 30, Stride 30 $\to$ **$200$ windows** (Zero shared readings between windows).

### Results Table

| Evaluation Configuration | Sample Count | Normal Windows | Anomaly Windows | Accuracy | Precision | Recall | F1-Score | Specificity | False Alarm Rate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Overlapping (Stride 10)** | 580 | 348 | 232 | $99.31\%$ | $98.31\%$ | $100.00\%$ | $0.9915$ | $98.85\%$ | $1.15\%$ (4 FP) |
| **Non-Overlapping (Stride 30)** | **200** | **120** | **80** | **$100.00\%$** | **$100.00\%$** | **$100.00\%$** | **$1.0000$** | **$100.00\%$** | **$0.00\%$ (0 FP)** |
| *95% Wilson Confidence Interval* | — | — | — | $[98.1\%, 100\%]$ | $[95.4\%, 100\%]$ | $[95.4\%, 100\%]$ | — | $[96.9\%, 100\%]$ | $[0.0\%, 3.1\%]$ |

### Independent Auditor Finding & Statistical Nuance:
The non-overlapping evaluation confirms that **high test metrics are not an artifact of window overlap**. When every window is strictly non-overlapping (stride 30), all 80 anomalous sequence windows across `M102, M104, M107, M109` are detected with $100.0\%$ recall, and all 120 normal windows pass with $100.0\%$ specificity.

> [!NOTE]
> **Clarification on Statistical Independence vs. Asset Clustering:**
> While stride-30 completely eliminates shared sensor readings between evaluation windows (zero point overlap), these 200 windows still originate from only 10 physical machines (20 windows per machine). Consequently, temporal auto-correlation within each machine trajectory and asset-level clustering remain present. The effective sample size for statistical generalization cannot automatically be assumed to equal 200 independent fleet events. However, this benchmark confirms that sliding window overlap was not the driver of the near-perfect test split performance.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/overlapping_vs_non_overlapping_comparison.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/overlapping_vs_non_overlapping_comparison.png)

---

## 4. Audit B — Common Granularity Comparison (IF vs. LSTM)

### 4.1 Sequence-Level Aggregation Benchmark

To enable a fair, head-to-head comparison, Isolation Forest point predictions were aggregated to the exact same **580 sequence windows** ($30$ readings) as the LSTM Autoencoder. Aggregation thresholds were calibrated on **validation sequence windows** ($N=580$) before being applied to the test windows:

### Sequence-Level Benchmark Table ($N = 580$ Windows)

| Model & Aggregation Strategy | Aggregation Formula | Calibrated Threshold ($\tau$) | Accuracy | Precision | Recall | F1-Score | Specificity | False Positive Rate |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LSTM Autoencoder** | Sequence MSE | $\tau = 0.9015$ | **$99.31\%$** | **$98.31\%$** | **$100.00\%$** | **$0.9915$** | **$98.85\%$** | **$1.15\%$ (4 FP)** |
| **IF: Mean Score Aggregation** | $\frac{1}{30}\sum s_t$ | $\tau = 0.0134$ | **$100.00\%$** | **$100.00\%$** | **$100.00\%$** | **$1.0000$** | **$100.00\%$** | **$0.00\%$ (0 FP)** |
| **IF: Fraction Anomalous** | $\frac{1}{30}\sum \mathbb{I}(s_t > \tau)$ | $\tau = 0.3667$ | **$100.00\%$** | **$100.00\%$** | **$100.00\%$** | **$1.0000$** | **$100.00\%$** | **$0.00\%$ (0 FP)** |
| **IF: Max Score Aggregation** | $\max(s_t)$ | $\tau = 0.1198$ | $98.45\%$ | $96.27\%$ | $100.00\%$ | $0.9810$ | $97.41\%$ | $2.59\%$ (9 FP) |
| **IF: Naive Any-Point Flagged** | $\mathbb{I}(\max(s_t) > \tau)$ | $\tau = 0.0269$ | $48.79\%$ | $43.86\%$ | $100.00\%$ | $0.6097$ | $14.66\%$ | $85.34\%$ (297 FP) |
| *Reference: IF Point-Level (Raw)* | Single point score | $\tau = 0.0269$ | $95.98\%$ | $90.87\%$ | $100.00\%$ | $0.9522$ | $93.31\%$ | $6.69\%$ (241 FP) |

### Key Architectural Lesson:
- **Naive Point-Level Thresholding (`any_point_flagged`):** If a single point triggers an alert, the window-level false alarm rate explodes to **$85.34\%$**. With an isolated error rate of $6.7\%$, the probability of at least one false alarm in 30 points is $1 - (1 - 0.0669)^{30} \approx 87.5\%$.
- **Temporal Persistence Benefit:** Aggregating point predictions over 30 timesteps using **Mean Score** or requiring **$\ge 37\%$ anomalous points** reduces false positives from $241$ down to **$0$**, demonstrating that temporal persistence filtering is critical in industrial deployment.

### 4.2 Confirmation of Validation-Only Threshold Calibration

To guarantee strict evaluation fairness and prevent data leakage:
1. **LSTM Autoencoder Threshold ($\tau = 0.901464$):** Calibrated exclusively on normal validation sequences ($X_{\text{val, normal}}$, $N=348$ sequences) at the 99th percentile of reconstruction error. Test data was never observed during threshold calibration.
2. **Isolation Forest Aggregation Thresholds:** Calibrated on the 580 validation sequence windows:
   - **Mean Score Threshold ($\tau = 0.0134$):** Selected by optimizing F1 on validation sequence windows.
   - **Fraction Anomalous Threshold ($\tau = 0.3667$):** Selected by precision-recall optimization on validation sequence windows.
   - **Max Score Threshold ($\tau = 0.1198$):** Calibrated on validation sequence windows.
3. Test sequences and labels were completely unobserved during all parameter and threshold tuning.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/common_granularity_if_vs_lstm.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/common_granularity_if_vs_lstm.png)

---

## 5. Audit C & D — Fault Progression, Early Warning & Within-Machine Detection

The lifecycle of each faulted machine was evaluated across all 4,000 timesteps ($333.3\text{ hours}$):
- **Stage 0: Normal Baseline** (Steps 0–2599, $216.7\text{ h}$)
- **Stage 1: Incipient Degradation** (Steps 2600–3199, $50.0\text{ h}$, $progression \in [0.0, 0.43]$)
- **Stage 2: Moderate Degradation** (Steps 3200–3599, $33.3\text{ h}$, $progression \in [0.43, 0.71]$)
- **Stage 3: Severe Progressive Failure** (Steps 3600–3999, $33.3\text{ h}$, $progression \in [0.71, 1.00]$)

### 5.1 Early Warning Terminology & Calculations

To prevent ambiguity, early warning metrics are strictly distinguished across three operational concepts:
1. **Fault Detection Delay:** The elapsed time between synthetic fault onset (Step 2,600, 2026-10-31 15:20:00) and the first threshold-exceeding anomaly alert.
2. **Time to Synthetic Severe-Degradation Boundary:** The time between the first detected anomaly and the synthetic severe-degradation boundary (Step 3,600, 2026-11-04 02:40:00).
3. **Catastrophic Failure Lead Time (Physical Reality):** In industrial plants, early warning lead time measures the horizon before physical machine seizure, catastrophic trip, or irreversible mechanical destruction. The synthetic data generator here simulates smooth continuous degradation functions up to Step 4,000 without simulating hardware tripping or mechanical destruction. Therefore, Step 3,600 serves as the formal **synthetic severe-degradation boundary** ($progression = 0.71$).

### Early Warning Lead Time Summary Table

| Machine ID | Failure Mechanism | Model | Earliest Detection Step | Earliest Detection Timestamp | Detection Delay | Time to Synthetic Severe-Degradation Boundary (Step 3600) |
|---|---|---|:---:|:---:|:---:|:---:|
| **M104** | Bearing Spalling | Isolation Forest | Step 2600 | 2026-10-31 15:20:00 | **0 min** | **83.33 Hours (3.47 Days)** |
| | | LSTM Autoencoder | Step 2609 | 2026-10-31 16:05:00 | **45 min** | **82.58 Hours (3.44 Days)** |
| **M107** | Pressure Seal Drop | Isolation Forest | Step 2602 | 2026-10-31 15:30:00 | **10 min** | **83.17 Hours (3.47 Days)** |
| | | LSTM Autoencoder | Step 2629 | 2026-10-31 17:45:00 | **145 min (2.4 h)** | **80.92 Hours (3.37 Days)** |
| **M109** | Lubrication Friction | Isolation Forest | Step 2605 | 2026-10-31 15:45:00 | **25 min** | **82.92 Hours (3.45 Days)** |
| | | LSTM Autoencoder | Step 2619 | 2026-10-31 16:55:00 | **95 min (1.6 h)** | **81.75 Hours (3.41 Days)** |
| **M102** | Hydraulic Overheating | Isolation Forest | Step 2611 | 2026-10-31 16:15:00 | **55 min** | **82.42 Hours (3.43 Days)** |
| | | LSTM Autoencoder | Step 2869 | 2026-11-01 13:45:00 | **1345 min (22.4 h)** | **60.92 Hours (2.54 Days)** |

> [!NOTE]
> **Verification of M102 Calculations:**
> - Fault onset: Step 2,600. Earliest LSTM alert: Step 2,869 (due to diurnal thermal masking).
> - Detection delay: $(2869 - 2600) \times 5\text{ min} = 1,345\text{ min} = 22.4167\text{ hours}$.
> - Time to severe boundary: $(3600 - 2869) \times 5\text{ min} = 3,655\text{ min} = 60.9167\text{ hours}$.

### 5.2 Stage-by-Stage Recall Comparison

```
Detection Recall by Progression Stage:
Stage 0 (Normal):     FPR = 6.7% (IF Point)  vs  1.1% (LSTM Sequence)
Stage 1 (Incipient):  Recall = 60.7% (IF Point)  vs  77.1% (LSTM Sequence)
Stage 2 (Moderate):   Recall = 100.0% (Both Models)
Stage 3 (Severe):     Recall = 100.0% (Both Models)
```

### 5.3 Earliest Detection vs. Sustained Detection

- **Earliest Alert Definition:** The earliest detection steps in Section 5.1 represent the very first individual threshold crossing (a single point for IF, or a single window for LSTM) without applying a consecutive-alert persistence rule.
- **Intermittency in Incipient Phase (Stage 1):** In Stage 1 ($progression \in [0.00, 0.43]$), anomalous deviations are subtle ($+0.5\sigma$ to $+2.5\sigma$). Because random sensor noise and diurnal cycles oscillate around the decision boundary, detection in this phase is intermittent (point IF recall is $51.7\%\text{--}62.5\%$, LSTM recall is $56.7\%\text{--}98.3\%$). An unpersisted single alert during this stage could potentially be dismissed as an operational spike.
- **Sustained Continuous Detection (Stage 2+):** Once fault progression surpasses $0.43$ (Step 3,200), anomalous deviations exceed $+4.0\sigma$. At this stage, both Isolation Forest and LSTM Autoencoder transition to **$100.0\%$ continuous sustained alerting**, providing unequivocal, persistent failure alarms.

### 5.4 Within-Machine Progression Sensitivity

> [!IMPORTANT]
> **Audit Finding on Within-Machine Sensitivity:**
> The within-machine analysis provides evidence that the models respond to temporal changes associated with fault progression. It reduces concern about machine-identity confounding but does not completely eliminate it.
>
> Across all 4,000 timesteps of `M102, M104, M107, M109`:
> 1. In the normal stage (steps 0–2599), anomaly scores remain at healthy baseline levels (mean IF score $-0.046$, mean LSTM MSE $0.697$), matching the healthy fleet.
> 2. Model outputs correlate strongly with the synthetic generator's linear `fault_severity` ramp ($R \in [0.94, 0.98]$). Pearson $r$ was computed between model continuous scores and the synthetic `fault_severity` parameter (0.0 for steps 0–2599, scaling linearly from 0.0 at step 2600 to 1.0 at step 4000). While this demonstrates proportional sensitivity to escalating synthetic deviations, correlation does not prove causation.
> 3. Asset-level confounding cannot be completely ruled out because each failure mode is present on only a single physical machine in this dataset.

*Supporting Graphs:*
- [`reports/phase2/evaluation_audit/graphs/m102_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m102_within_machine_timeline.png)
- [`reports/phase2/evaluation_audit/graphs/m104_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m104_within_machine_timeline.png)
- [`reports/phase2/evaluation_audit/graphs/m107_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m107_within_machine_timeline.png)
- [`reports/phase2/evaluation_audit/graphs/m109_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m109_within_machine_timeline.png)
- [`reports/phase2/evaluation_audit/graphs/fault_progression_detection_lead_time.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/fault_progression_detection_lead_time.png)

---

## 6. Audit E — Verification of Machine Holdout Diagnostic

The audit verified the arithmetic and methodology of the zero-shot holdout diagnostic experiment:
- **Training Fleet:** 5 Healthy Machines (`M101, M103, M105, M106, M108` — $20,000$ readings).
- **Unseen Healthy Machine M110:** $98.60\%$ Specificity ($1.40\%$ FPR across 4,000 readings).
- **Unseen Faulted Machines (M102, M104, M107, M109):** Evaluated across all 1,400 anomalous readings (from step 2600 to 4000).
- **Reported Recalls:** M102 ($48.86\%$), M104 ($69.21\%$), M107 ($74.00\%$), M109 ($76.14\%$).
- **Reconciliation:** The lower holdout recall is due to evaluating the **full lifetime** including early incipient steps ($progression < 0.25$). When evaluated strictly on late-stage failure (steps 3400–4000), recall on these unseen machines reaches **$100.0\%$**.

*Supporting Report:* [`reports/phase2/evaluation_audit/machine_holdout_verification.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/machine_holdout_verification.md)

---

## 7. Audit F — Statistical Hierarchy (Point vs. Window vs. Event)

The audit formalized the multi-level statistical hierarchy:
1. **Point Level ($N=6,000$):** High temporal granularity ($5\text{ min}$), but suffers from $6.69\%$ false alarm rate ($241\text{ alarms}$ across $3,600$ normal readings).
2. **Window Level ($N=580$ or $200$):** Slices $150\text{-minute}$ temporal sequences. Suppresses isolated noise ($1.15\%$ FPR in overlapping, $0.00\%$ FPR in non-overlapping).
3. **Event Level ($N=10$ Machines):** Plant asset-level triage. Evaluated across exactly 10 machines (4 faulted, 6 healthy). Benchmark result shows **$100\%$ detection of all 4 machine failures with $0\%$ false machine alarms** on this 10-machine dataset. Repeated sequence windows along each machine's timeline are repeated longitudinal measures, not independent machine events.

*Supporting Report:* [`reports/phase2/evaluation_audit/statistical_interpretation.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/statistical_interpretation.md)

---

## 8. Final Audit Verdict & Project-Readiness Decision

### Final Verdict: **APPROVED WITH DOCUMENTED EVALUATION PROTOCOLS**

The independent audit confirms that the anomaly detection models are sound, robust, and methodologically validated:
1. **No Overfitting:** Smooth convergence curves without divergence.
2. **No Data Leakage:** All 10 leakage criteria passed.
3. **No Window Overlap Inflation:** Evaluating $200$ non-overlapping evaluation windows confirmed $100.0\%$ accuracy and recall on the test partition.
4. **Early-Warning Capability:** The models provide **$60.9$ to $83.3\text{ hours}$ of advance warning** between earliest detected anomaly and the synthetic severe-degradation boundary (Step 3600).
5. **Within-Machine Temporal Sensitivity:** Anomaly scores track synthetic fault progression ($R > 0.94$), providing evidence that the models respond to temporal degradation rather than static machine identities, though asset-level confounding remains an inherent dataset limitation.
6. **Validation-Only Calibration:** All decision thresholds (LSTM $\tau = 0.9015$, IF aggregation thresholds) were calibrated exclusively on validation data.

### Ready for Step 4:
The evaluation audit is formally completed and closed. The project is fully approved to proceed immediately to **Phase 2, Step 4: Sensor-Level Anomaly Attribution** ($(\mathbf{x}_c - \hat{\mathbf{x}}_c)^2$ reconstruction error attribution across vibration, temperature, pressure, current, and RPM to isolate physical root causes).

---

## 9. Generated Audit Artifacts Directory

All audit outputs are preserved in [`reports/phase2/evaluation_audit/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/):

### Markdown Reports
1. [`reports/phase2/evaluation_audit/evaluation_fairness_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/evaluation_fairness_report.md) — Master Comprehensive Audit Report
2. [`reports/phase2/evaluation_audit/early_warning_analysis.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/early_warning_analysis.md) — 4-Stage Lifecycle Progression & Lead Time Analysis
3. [`reports/phase2/evaluation_audit/within_machine_detection_analysis.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/within_machine_detection_analysis.md) — Within-Machine Anomaly Trajectory Analysis
4. [`reports/phase2/evaluation_audit/machine_holdout_verification.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/machine_holdout_verification.md) — Zero-Shot Fleet Holdout Reconciliation
5. [`reports/phase2/evaluation_audit/statistical_interpretation.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/statistical_interpretation.md) — Independence, Wilson CIs & Granularity Framework

### JSON Verification Files
1. [`reports/phase2/evaluation_audit/non_overlapping_window_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/non_overlapping_window_results.json)
2. [`reports/phase2/evaluation_audit/common_granularity_comparison.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/common_granularity_comparison.json)
3. [`reports/phase2/evaluation_audit/fault_progression_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/fault_progression_results.json)

### Visualizations Gallery (7 PNG Graphs)
Located in [`reports/phase2/evaluation_audit/graphs/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/):
1. **`overlapping_vs_non_overlapping_comparison.png`** — Stride 10 ($N=580$) vs Stride 30 ($N=200$) metric and confusion matrix comparison.
2. **`common_granularity_if_vs_lstm.png`** — Sequence-level ROC curves and metric comparisons for IF vs LSTM.
3. **`fault_progression_detection_lead_time.png`** — Warning lead time bar chart for M102, M104, M107, and M109.
4. **`m102_within_machine_timeline.png`** — 4-panel within-machine degradation trajectory for M102.
5. **`m104_within_machine_timeline.png`** — 4-panel within-machine degradation trajectory for M104.
6. **`m107_within_machine_timeline.png`** — 4-panel within-machine degradation trajectory for M107.
7. **`m109_within_machine_timeline.png`** — 4-panel within-machine degradation trajectory for M109.
