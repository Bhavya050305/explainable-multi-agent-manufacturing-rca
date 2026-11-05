# ManuMind AI — Independent Audit: Within-Machine Anomaly Detection Analysis

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.2 — Audit D: Within-Machine Temporal Anomaly Detection & Progression Tracking
**Auditor:** Senior ML Evaluation Engineer & Independent Auditor
**Date:** November 2026
**Status:** **AUDITED — EVIDENCE OF TEMPORAL SENSITIVITY TO FAULT PROGRESSION**

---

## 1. Executive Summary

A critical question raised in the independent evaluation is whether the anomaly detection models genuinely detect **developing faults within a machine**, or whether they merely memorize static **machine identities** (e.g., recognizing that "M104 is a faulted machine" regardless of operational state).

This audit analyzed the full 4,000-timestep lifecycle for all four faulted machines (`M102, M104, M107, M109`), directly comparing model behavior during:
1. **The Healthy Baseline Period:** Timesteps 0 to 2,599 ($2,600$ readings, $216.7\text{ hours}$ of healthy operation).
2. **The Incipient Degradation Phase:** Timesteps 2,600 to 3,199 ($600$ readings, $50.0\text{ hours}$ of early fault onset).
3. **The Moderate Degradation Phase:** Timesteps 3,200 to 3,599 ($400$ readings, $33.3\text{ hours}$ of developing damage).
4. **The Severe Failure Phase:** Timesteps 3,600 to 3,999 ($400$ readings, $33.3\text{ hours}$ of terminal failure).

### Core Audit Finding
> [!IMPORTANT]
> **Key Finding: Evidence of Temporal Sensitivity to Fault Progression**
> The within-machine analysis provides evidence that the models respond to temporal changes associated with fault progression. It reduces concern about machine-identity confounding but does not completely eliminate it.
> During the first 2,600 timesteps of `M102, M104, M107, M109`, when the assets were healthy:
> - **Isolation Forest Anomaly Scores:** Average $\mathbf{-0.046}$, consistent with healthy baseline behavior across the fleet.
> - **LSTM Reconstruction MSE:** Average $\mathbf{0.697}$, consistent with the healthy fleet baseline.
> - **Window False Alarm Rates:** $0.78\%$ to $1.55\%$ on sequence windows, matching the clean baseline design.
>
> Following fault initiation at timestep 2,600, both models exhibit continuous anomaly scores that track the synthetic generator's linear degradation parameter `fault_severity` (Pearson $r \in [0.94, 0.98]$ across all 4,000 timesteps). However, while high correlation demonstrates proportional sensitivity to increasing deviations, correlation does not prove causation, and this relationship is evaluated within synthetic generation dynamics.

---

## 2. Machine-by-Machine Deep Dive

### 2.1 Machine M104: High-Speed Spindle Center (Bearing Spalling)
- **Physical Failure Mechanism:** Inner race fatigue spalling leading to escalating high-frequency vibration, cage chatter, motor current surges, and minor spindle speed drag.
- **Normal Period (Steps 0–2599):**
  - Baseline Vibration: $1.81 \pm 0.22\text{ mm/s}$
  - Isolation Forest Score: Mean = $-0.0473$ (well below threshold $\tau = 0.0269$)
  - LSTM Reconstruction MSE: Mean = $0.6962$ (well below threshold $\tau = 0.9015$)
  - Window False Alarms: Only 4 windows flagged out of 258 ($1.55\%$ FPR).
- **Incipient Phase (Steps 2600–3199):**
  - Earliest Point Alert: Step 2,600 (**Instantaneous alert, 0 min delay**).
  - Earliest Sequence Alert: Step 2,609 (**45 min delay**).
  - Mean Vibration: Climbs from $1.8\text{ mm/s}$ to $3.6\text{ mm/s}$.
  - LSTM Reconstruction MSE jumps from $0.696$ to **$2.761$** ($3.96\times$ baseline).
  - LSTM Recall: **$98.33\%$** (59 out of 60 windows detected).
- **Moderate Phase (Steps 3200–3599):**
  - Mean Vibration: $5.8\text{ mm/s}$.
  - LSTM Reconstruction MSE reaches **$35.45$** ($50.9\times$ baseline).
  - Recall: **$100.0\%$**.
- **Severe Phase (Steps 3600–3999):**
  - Peak Vibration: Exceeds $10.5\text{ mm/s}$.
  - LSTM Reconstruction MSE surges to **$171.80$** ($246.8\times$ baseline).
  - Recall: **$100.0\%$**.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/m104_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m104_within_machine_timeline.png)

---

### 2.2 Machine M102: Hydraulic Stamping Press (Overheating)
- **Physical Failure Mechanism:** Hydraulic oil radiator clogging and cooling fan failure causing thermal runaway and minor hydraulic pressure rise.
- **Normal Period (Steps 0–2599):**
  - Baseline Temperature: $48.05 \pm 1.20^\circ\text{C}$ (modulated by $\pm 2.5^\circ\text{C}$ diurnal cycle).
  - Isolation Forest Score: Mean = $-0.0469$.
  - LSTM Reconstruction MSE: Mean = $0.7004$.
  - Window False Alarms: 3 windows flagged out of 258 ($1.16\%$ FPR).
- **Incipient Phase (Steps 2600–3199):**
  - Earliest Point Alert: Step 2,611 (**55 min delay**).
  - Earliest Sequence Alert: Step 2,869 (**22.4 hours delay** due to diurnal wave overlap).
  - Mean Temperature: Climbs from $48^\circ\text{C}$ to $58^\circ\text{C}$.
  - LSTM Reconstruction MSE increases to **$1.836$** ($2.62\times$ baseline).
  - Point IF Recall: **$51.67\%$**; LSTM Recall: **$56.67\%$**.
- **Moderate Phase (Steps 3200–3599):**
  - Mean Temperature: $72.5^\circ\text{C}$.
  - LSTM Reconstruction MSE reaches **$20.73$** ($29.6\times$ baseline).
  - Recall: **$100.0\%$**.
- **Severe Phase (Steps 3600–3999):**
  - Peak Temperature: Exceeds $94.5^\circ\text{C}$.
  - LSTM Reconstruction MSE reaches **$74.00$** ($105.6\times$ baseline).
  - Recall: **$100.0\%$**.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/m102_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m102_within_machine_timeline.png)

---

### 2.3 Machine M107: Centrifugal Compressor (Pneumatic Seal Drop)
- **Physical Failure Mechanism:** Pneumatic manifold seal rupture resulting in continuous delivery pressure loss while the motor stator current increases to maintain head pressure.
- **Normal Period (Steps 0–2599):**
  - Baseline Pressure: $6.20 \pm 0.12\text{ bar}$.
  - Isolation Forest Score: Mean = $-0.0446$.
  - LSTM Reconstruction MSE: Mean = $0.7237$.
- **Incipient Phase (Steps 2600–3199):**
  - Earliest Point Alert: Step 2,602 (**10 min delay**).
  - Earliest Sequence Alert: Step 2,629 (**145 min delay**).
  - Mean Pressure: Drops from $6.2\text{ bar}$ to $5.2\text{ bar}$.
  - LSTM Reconstruction MSE rises to **$3.346$** ($4.62\times$ baseline).
  - Point IF Recall: **$62.50\%$**; LSTM Recall: **$61.67\%$**.
- **Moderate Phase (Steps 3200–3599):**
  - Mean Pressure: Drops to $4.1\text{ bar}$.
  - LSTM Reconstruction MSE reaches **$41.35$** ($57.1\times$ baseline).
  - Recall: **$100.0\%$**.
- **Severe Phase (Steps 3600–3999):**
  - Minimum Pressure: Falls to $2.4\text{ bar}$.
  - LSTM Reconstruction MSE surges to **$128.33$** ($177.3\times$ baseline).
  - Recall: **$100.0\%$**.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/m107_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m107_within_machine_timeline.png)

---

### 2.4 Machine M109: Industrial Gearbox (Lubrication Friction)
- **Physical Failure Mechanism:** Lubricant boundary breakdown resulting in dry gear tooth friction, accompanied by motor current surges and rapid housing heating.
- **Normal Period (Steps 0–2599):**
  - Baseline Current: $14.51 \pm 0.70\text{ A}$.
  - Isolation Forest Score: Mean = $-0.0474$.
  - LSTM Reconstruction MSE: Mean = $0.6837$.
  - Window False Alarms: Only 2 windows flagged out of 258 ($0.78\%$ FPR).
- **Incipient Phase (Steps 2600–3199):**
  - Earliest Point Alert: Step 2,605 (**25 min delay**).
  - Earliest Sequence Alert: Step 2,619 (**95 min delay**).
  - Mean Current: Rises from $14.5\text{ A}$ to $18.2\text{ A}$.
  - LSTM Reconstruction MSE climbs to **$2.841$** ($4.16\times$ baseline).
  - LSTM Recall: **$91.67\%$** (55 out of 60 windows detected).
- **Moderate Phase (Steps 3200–3599):**
  - Mean Current: Reaches $24.5\text{ A}$.
  - LSTM Reconstruction MSE reaches **$36.20$** ($52.9\times$ baseline).
  - Recall: **$100.0\%$**.
- **Severe Phase (Steps 3600–3999):**
  - Peak Current: Exceeds $30.0\text{ A}$.
  - LSTM Reconstruction MSE surges to **$134.41$** ($196.6\times$ baseline).
  - Recall: **$100.0\%$**.

*Supporting Graph:* [`reports/phase2/evaluation_audit/graphs/m109_within_machine_timeline.png`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/evaluation_audit/graphs/m109_within_machine_timeline.png)

---

## 3. Addressing the Machine Identity Confounding Hypothesis

The hypothesis that the models merely recognize static machine identities is evaluated against three empirical observations:

1. **Sharp In-Machine Step Change:** For all four faulted machines, anomaly scores remain low and flat throughout steps 0–2599, and begin climbing only after step 2,600. If the models acted purely as static machine-identity classifiers (flagging any reading from M102, M104, M107, or M109 simply because of asset ID), steps 0–2599 would have been flagged as anomalous at rates comparable to the faulted stage.
2. **Proportional Error Growth vs. Synthetic Severity Parameter:** Continuous reconstruction error and anomaly scores correlate strongly with the synthetic generator's ground-truth `fault_severity` parameter (Pearson $r \in [0.94, 0.98]$ across all 4,000 steps). Specifically, $r$ was calculated between model outputs (point IF anomaly score or LSTM reconstruction MSE) and the synthetic `fault_severity` ramp (0.0 for steps 0–2599, increasing linearly from 0.0 at step 2600 to 1.0 at step 4000). While this demonstrates proportional sensitivity to escalating synthetic deviations, correlation does not prove physical causation.
3. **Cross-Machine Transfer on M110:** In Audit G, an Isolation Forest trained on healthy machines (`M101, M103, M105, M106, M108`) achieved **$98.6\%$ specificity on unseen machine `M110`**, confirming that the models learn universal normal operating bounds rather than machine-specific identifiers.
4. **Remaining Confounders and Fleet Limitations:**
   - *Single Asset per Fault Mode:* Each failure mode in this dataset is represented by exactly one machine (`M102` for overheat, `M104` for bearing wear, `M107` for pressure drop, `M109` for lubrication friction). Machine-specific baseline nuances and fault signatures cannot be fully disentangled at the fleet level without multi-asset replication.
   - *Synthetic Progression Artifacts:* Synthetic degradation functions follow smooth deterministic trajectories (linear/exponential ramps with additive Gaussian noise). Real industrial machines experience complex non-linear degradation, intermittent operational pauses, load shifts, and variable environmental noise that may alter progression dynamics.
