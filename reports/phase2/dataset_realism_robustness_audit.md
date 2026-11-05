# ManuMind AI — Phase 2: Dataset Realism & Model Robustness Audit

**Document Reference:** `reports/phase2/dataset_realism_robustness_audit.md`
**Evaluation Role:** Senior AI/ML Engineer & Independent Model Auditor
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Academic Institution:** Department of Artificial Intelligence and Data Science, RMK Engineering College
**Date:** November 5, 2026 (Version 1.1.0 — Reconciled & Approved Calibration Protocol)
**Status:** COMPLETE (Read-Only Independent Audit & Experimental Design)

---

## 1. Executive Summary

This audit assesses the physical realism, statistical properties, and potential biases of the synthetic industrial telemetry dataset powering **ManuMind AI**. Building upon the findings of the Phase 2 Step 0 Dataset Audit, Step 3.1 Data Leakage Audit, and Step 3.2 Evaluation Fairness Audit, this investigation evaluates whether the extraordinarily high empirical performance reported by the models (**Isolation Forest F1: 95.22%**, **LSTM Autoencoder F1: 99.15%**) is driven by genuine model capability or inflated by synthetic dataset artifacts.

### Key Audit Findings:
1. **Existing Generator Noise is Present but Oversimplified:** The telemetry generator (`generate_sensor_data.py`) does incorporate independent Gaussian measurement noise, 3-shift operational offsets, circadian diurnal sinusoidal thermal variation, and sporadic healthy vibration spikes. However, it completely lacks autoregressive temporal correlation ($\rho = 0$), mechanical drift, non-linear thermal coupling, packet drops, or communication telemetry jitter.
2. **Healthy Data Exhibits Synthetic Smoothness:** While empirical distributions appear Gaussian and variance scales are physiologically plausible, four out of five sensors (Vibration, Pressure, Current, RPM) display near-zero temporal autocorrelation ($\text{ACF}_{\text{lag-1}} < 0.007$), indicating memoryless white noise rather than physical inertial systems.
3. **Severe Machine-Identity and Fault-Type Confounding:** The dataset allocates exactly one fault type to each of four specific machines (**M102: Overheating**, **M104: Bearing wear**, **M107: Pressure drop**, **M109: Lubrication failure**). While healthy machine baseline means are statistically similar across the fleet (reducing evidence that models identify assets by normal operating baselines), each failure mode is confounded 100% with a single machine identity. Consequently, cross-machine fault-type generalization cannot be established.
4. **Extreme Late-Stage Fault Separability:** Faults develop according to deterministic power functions ($\text{progression}^{p}$). In late-stage degradation (steps 3600–3999), deviations reach **$+15\sigma$ to $+39\sigma$**, producing astronomical Mahalanobis distances ($D_M > 20$) and single-feature ROC-AUCs of **1.0000**. However, under the approved Phase 2 Step 3.2 fault-stage boundaries, incipient-stage faults (steps 2600–3199) exhibit realistic distributional overlap ($D_M \approx 4.2 - 4.6$, AUC $\approx 0.77 - 0.87$), confirming that early-stage detection is challenging.
5. **Reconciliation of Sequence Counts:** The approved test partition contains exactly **580 overlapping sequences** (stride = 10, window size = 30, 58 windows per machine across 10 machines). The previous draft's mention of "571" was an arithmetic slip ($570 + 1$) that omitted dividing $(N_{\text{test}} - W) = 570$ by stride 10. The true sequence count of 580 is corroborated by `sequences_test.npz` and `clean_sensor_windows.csv`.
6. **Robustness Experiment Design:** A structured, frozen-model robustness evaluation framework (**E0–E7**) has been formalized in `reports/phase2/dataset_realism_experiment_plan.json`. This protocol enables evaluating the frozen models against controlled Gaussian noise, AR(1) colored noise with exact stationary/innovation variance separation, calibration drift, and transient spikes without retraining models, recalibrating thresholds, or modifying original databases.

---

## 2. Task A — Actual Telemetry Generator Inspection

A complete line-by-line inspection of `ml/data_generator/generate_sensor_data.py` (290 lines) was performed. Below is the detailed inventory of telemetry characteristics.

| # | Characteristic | Status | Source Lines | Actual Implementation & Parameters | Scope | Realism Assessment |
|---|---|---|---|---|---|---|
| **1** | **Gaussian Measurement Noise** | **PRESENT** | Lines 56–60 | Vib: $0.22 \cdot \mathcal{N}(0, 1)$<br>Temp: $1.20 \cdot \mathcal{N}(0, 1)$<br>Press: $0.12 \cdot \mathcal{N}(0, 1)$<br>Curr: $0.70 \cdot \mathcal{N}(0, 1)$<br>RPM: $7.50 \cdot \mathcal{N}(0, 1)$ | Healthy & Faulty | **Partially Realistic.** Standard Gaussian white noise is present, but lacks non-Gaussian tails and state-dependent variance. |
| **2** | **Correlated / AR(1) Noise** | **ABSENT** | — | No autoregressive terms ($\epsilon_t = \rho \epsilon_{t-1} + \eta_t$). Each time step is drawn independently via `rng.randn(steps)`. | None | **Unrealistic.** Physical industrial processes possess mechanical inertia and thermal mass that induce high serial correlation. |
| **3** | **Random Sensor Fluctuations** | **PARTIALLY PRESENT** | Lines 48–60 | Represented solely by independent Gaussian noise added to step-wise shift factors. No Brownian motion, pink noise, or random walk. | Healthy & Faulty | **Oversimplified.** Fluctuations lack multi-scale spectral power typical of rotating machinery. |
| **4** | **Temporal Drift** | **ABSENT (Healthy)** | Lines 45–65 | Healthy machines have zero sensor degradation drift, zero fouling drift, and zero seasonal calibration drift. | Faulty Only | **Unrealistic.** Real manufacturing sensors experience calibration degradation and transducer aging over weeks of operation. |
| **5** | **Sudden Spikes** | **PARTIALLY PRESENT** | Lines 122–126 | `pulse_indices = rng.choice(steps, size=max(2, steps // 800), replace=False)`<br>`vibration[p_idx:p_idx+2] += rng.uniform(0.6, 1.1)` | Healthy Only | **Partially Realistic.** Implemented only on healthy machines for vibration (2-step pulse); completely absent on temperature, pressure, current, and RPM. |
| **6** | **Environmental Temperature Variations** | **PRESENT** | Line 53 | `ambient_thermal = 2.5 * np.sin((hours - 8.0) * (2 * np.pi / 24.0))` | Healthy & Faulty | **Oversimplified.** Pure deterministic 24-hour sinusoid ($A = \pm 2.5^\circ\text{C}$, peak at 14:00). Lacks weather fronts, seasonal variance, or HVAC cycling. |
| **7** | **Machine Operating-Load Variations** | **PARTIALLY PRESENT** | Lines 49–51 | Direct linear coupling to 3 factory shift factors (`shift_factors = [0.08, 0.02, -0.06]`). | Healthy & Faulty | **Oversimplified.** Factory schedule operates as discrete square waves rather than dynamic job-shop load variations. |
| **8** | **Shift-Based Operating Conditions** | **PRESENT** | Lines 49–51, 62–66 | Morning shift (+8% load), Afternoon (+2%), Night (-6%). Modulates Vib ($+0.15 \times s$), Temp ($+1.5 \times s$), Press ($+0.1 \times s$), Curr ($+1.2 \times s$). | Healthy & Faulty | **Realistic.** Accurately models lower factory ambient load and activity during nocturnal shifts. |
| **9** | **Missing Readings** | **ABSENT** | — | Dataset contains exactly 4,000 equidistant 5-minute telemetry rows per machine. Zero null values or dropped packets. | None | **Unrealistic.** Industrial IoT gateways frequently experience packet drops (typically 0.1%–1.0%). |
| **10** | **Communication Telemetry Jitter** | **ABSENT** | Line 23 | Equidistant timestamps generated via `pd.date_range(freq="5min")`. Zero clock jitter or out-of-order records. | None | **Unrealistic.** Industrial edge networks encounter timestamp drift and buffer queue delays. |
| **11** | **Sensor-Specific Noise Profiles** | **PRESENT** | Lines 56–60 | Discrete noise variances scaled to engineering units: $\sigma_v=0.22$, $\sigma_T=1.2$, $\sigma_P=0.12$, $\sigma_I=0.7$, $\sigma_R=7.5$. | Healthy & Faulty | **Realistic.** Appropriately differentiates measurement resolutions across physical sensor channels. |

---

## 3. Task B — Healthy Sensor Realism Analysis

To establish the empirical normal operating reference, all healthy training observations were analyzed. Filtering for `is_anomaly == 0` within `data/processed/sensor_train.csv` yields exactly **27,200 observations** across all 10 machines (2,800 steps for healthy machines M101, M103, M105, M106, M108, M110; 2,600 pre-fault steps for machines M102, M104, M107, M109).

### Empirical Normal Operating Reference Metrics

| Metric | Vibration (mm/s) | Temperature (°C) | Pressure (bar) | Current (A) | RPM |
|---|---|---|---|---|---|
| **Mean ($\mu$)** | 1.8034 | 47.9984 | 6.2023 | 14.5230 | 1799.9556 |
| **Standard Deviation ($\sigma_c$)** | **0.2235** | **2.2030** | **0.1211** | **0.7094** | **7.4553** |
| **Median** | 1.8020 | 47.9800 | 6.2000 | 14.5300 | 1800.0000 |
| **Min — Max** | 0.8970 — 3.1810 | 41.0300 — 55.0600 | 5.7100 — 6.6700 | 11.6900 — 17.5700 | 1767.1000 — 1828.6000 |
| **Interquartile Range (IQR)** | 0.2970 | 3.4600 | 0.1600 | 0.9500 | 10.1000 |
| **Median Absolute Deviation (MAD)** | 0.1480 | 1.7300 | 0.0800 | 0.4800 | 5.0000 |
| **First-Diff Mean ($\Delta x$)** | -0.00002 | -0.00042 | +0.00001 | 0.00000 | -0.00210 |
| **First-Diff Std ($\sigma_{\Delta x}$)** | 0.3153 | 1.6960 | 0.1708 | 0.9996 | 10.5189 |
| **First-Diff Skewness / Kurtosis** | +0.0026 / +0.1964 | +0.0224 / +0.0272 | -0.0121 / +0.0216 | +0.0142 / +0.0555 | -0.0063 / +0.0087 |
| **Autocorrelation Lag-1 ($\text{ACF}_1$)** | **0.0034** | **0.7035** | **0.0060** | **0.0070** | **0.0043** |
| **Autocorrelation Lag-5 ($\text{ACF}_5$)** | **0.0113** | **0.6968** | **-0.0016** | **0.0079** | **0.0049** |
| **Autocorrelation Lag-10 ($\text{ACF}_{10}$)**| **-0.0058**| **0.6897** | **0.0122** | **0.0176** | **-0.0086** |
| **Repeated Consecutive Values (%)** | 0.14% | 0.19% | 2.15% | 0.37% | 0.43% |
| **Outlier Frequency ($>3\sigma_c$)** | 0.43% | 0.01% | 0.23% | 0.25% | 0.28% |
| **Linear Trend Slope (units/step)** | $-5.0 \times 10^{-7}$ | $-4.69 \times 10^{-5}$ | $-0.0$ | $+1.3 \times 10^{-6}$ | $-1.51 \times 10^{-5}$ |
| **Machine-to-Machine ANOVA F (p)** | 0.46 (p = 0.900) | 0.64 (p = 0.764) | 0.93 (p = 0.498) | 0.71 (p = 0.696) | 0.76 (p = 0.653) |
| **Machine-Mean CV across 10 Assets** | **0.15%** | **0.07%** | **0.03%** | **0.08%** | **0.01%** |

### Statistical Interpretations:
1. **Autocorrelation Dichotomy:** Temperature exhibits strong serial persistence ($\text{ACF}_1 = 0.7035$) driven by the 24-hour sinusoidal ambient temperature cycle ($T = 288$ steps). In contrast, Vibration, Pressure, Current, and RPM display near-zero autocorrelation ($\text{ACF}_1 \le 0.0070$). In physical machinery, current draw and hydraulic pressure possess damping and inertia; their memoryless white-noise behavior in this dataset is an oversimplification.
2. **First-Difference Volatility:** For white-noise signals, the standard deviation of first differences theoretically equals $\sqrt{2} \cdot \sigma \approx 1.414 \cdot \sigma$. For vibration, $\frac{\sigma_{\Delta}}{\sigma} = \frac{0.3153}{0.2235} = 1.411$, matching theoretical uncorrelated Gaussian white noise with near-perfect fidelity.
3. **Repeated Values in Pressure:** Pressure shows a 2.15% consecutive repeat rate because raw pressure is generated with small standard deviation ($0.12\text{ bar}$) and rounded to 2 decimal places in the CSV export, creating artificial quantization steps.
4. **Machine Homogeneity:** ANOVA tests across all 10 machines yield $p$-values between $0.498$ and $0.900$ (all $p \gg 0.05$), with cross-machine coefficients of variation under $0.15\%$. All 10 machines possess statistically identical healthy baselines.

---

## 4. Visual Evidence of Telemetry Behavior

The analytical figures below were generated using high-resolution vector-quality rendering from the underlying data:

### Figure 1: Healthy Sensor Time-Series Behavior
![Healthy Sensor Time Series](graphs/healthy_sensor_time_series.png)
*Figure 1 demonstrates the multi-day telemetry profiles for Machine M101. Note the smooth 24-hour sinusoidal wave in temperature, the stepped shifts in current and pressure, and the uncorrelated high-frequency Gaussian jitter in vibration and RPM.*

### Figure 2: Empirical Density Distributions vs. Theoretical Gaussian Fit
![Healthy Sensor Distributions](graphs/healthy_sensor_distributions.png)
*Figure 2 compares empirical telemetry density histograms against fitted normal Gaussian distributions (black dashed lines). All sensors conform strictly to Gaussian envelopes without skewness or heavy industrial tails.*

### Figure 3: First-Difference (Step-to-Step Volatility) Distributions
![First Difference Distributions](graphs/first_difference_distributions.png)
*Figure 3 displays step-to-step variations ($\Delta x_t = x_t - x_{t-1}$). The distributions are centered exactly at zero with symmetric Gaussian spreads, confirming the absence of abrupt jumps or non-linear surges.*

### Figure 4: Autocorrelation Structure (ACF Lags 1–30)
![Healthy Sensor Autocorrelations](graphs/healthy_sensor_autocorrelations.png)
*Figure 4 highlights the stark structural contrast in serial correlation: Temperature maintains persistent autocorrelation across all 30 lags due to circadian thermal cycling, while Vibration, Pressure, Current, and RPM drop immediately to within the 95% white-noise confidence bounds.*

### Figure 5: Machine-to-Machine Operational Baseline Variations
![Machine to Machine Variation](graphs/machine_to_machine_variation.png)
*Figure 5 illustrates boxplots of healthy telemetry across all 10 assets (M101–M110). Median baselines and interquartile spreads are identical across the fleet, visually confirming the absence of asset-specific operational baselines.*

---

## 5. Task C — Fault Progression & Separability Analysis

Fault injection begins at **step 2,600** ($65\%$ of the timeline) across four specific machines. Fault progression follows a deterministic power-law trajectory:
$$\text{progression} = \left(\frac{t - 2600}{1400}\right)^p$$

### Primary Comparison: Approved Phase 2 Step 3.2 Fault-Stage Boundaries
In strict alignment with the approved Step 3.2 evaluation framework, the primary stage definitions are:
- **Healthy Baseline:** Steps 0–2599 ($N = 2600$ readings; progression = $0.0$)
- **Incipient Stage:** Steps 2600–3199 ($N = 600$ readings; progression: $0.00 \to 0.4286$)
- **Moderate Stage:** Steps 3200–3599 ($N = 400$ readings; progression: $0.4286 \to 0.7143$)
- **Severe Stage:** Steps 3600–3999 ($N = 400$ readings; progression: $0.7143 \to 1.0000$)

### Authoritative Multi-Stage Fault Progression & Separability Table

| Machine & Fault Type | Operational Stage (Step 3.2 Approved) | Mean Mahalanobis Dist ($D_M$) | Max $D_M$ | Primary Sensor Mean $\pm$ Std | Primary Sensor Cohen's $d$ | Primary Sensor Separability AUC | Secondary Sensor Effects |
|---|---|---|---|---|---|---|---|
| **M102**<br>*(Overheating)* | **Baseline (0–2599)**<br>**Incipient (2600–3199)**<br>**Moderate (3200–3599)**<br>**Severe (3600–3999)** | 2.130<br>**4.259**<br>**11.719**<br>**20.616** | 4.466<br>**10.328**<br>**16.731**<br>**27.547** | $48.04 \pm 2.17^\circ\text{C}$<br>$54.63 \pm 5.43^\circ\text{C}$<br>$69.52 \pm 4.88^\circ\text{C}$<br>$84.80 \pm 5.12^\circ\text{C}$ | 0.000<br>**1.614**<br>**5.814**<br>**9.513** | 0.5000<br>**0.8656**<br>**1.0000**<br>**1.0000** | Secondary Pressure rise:<br>Incipient: $d = 1.15$, AUC = 0.78<br>Moderate: $d = 4.02$, AUC = 1.00<br>Severe: $d = 7.40$, AUC = 1.00 |
| **M104**<br>*(Bearing Wear)* | **Baseline (0–2599)**<br>**Incipient (2600–3199)**<br>**Moderate (3200–3599)**<br>**Severe (3600–3999)** | 2.119<br>**4.335**<br>**14.162**<br>**27.596** | 4.700<br>**11.058**<br>**23.962**<br>**39.117** | $1.80 \pm 0.22\text{ mm/s}$<br>$2.43 \pm 0.67\text{ mm/s}$<br>$4.77 \pm 0.98\text{ mm/s}$<br>$8.26 \pm 1.34\text{ mm/s}$ | 0.000<br>**1.311**<br>**4.238**<br>**6.737** | 0.5000<br>**0.8167**<br>**1.0000**<br>**1.0000** | Secondary Temp & RPM:<br>Incipient: $d = 0.78 / -0.29$<br>Moderate: $d = 2.47 / -1.68$<br>Severe: $d = 4.70 / -3.95$ |
| **M107**<br>*(Pressure Drop)* | **Baseline (0–2599)**<br>**Incipient (2600–3199)**<br>**Moderate (3200–3599)**<br>**Severe (3600–3999)** | 2.133<br>**4.483**<br>**15.450**<br>**26.738** | 4.412<br>**11.233**<br>**22.529**<br>**34.460** | $6.20 \pm 0.12\text{ bar}$<br>$5.75 \pm 0.38\text{ bar}$<br>$4.45 \pm 0.38\text{ bar}$<br>$3.12 \pm 0.44\text{ bar}$ | 0.000<br>**-1.637**<br>**-6.315**<br>**-9.548** | 0.5000<br>**0.8679**<br>**1.0000**<br>**1.0000** | Secondary Current spike:<br>Incipient: $d = 1.20$, AUC = 0.79<br>Moderate: $d = 3.87$, AUC = 0.998<br>Severe: $d = 6.23$, AUC = 1.00 |
| **M109**<br>*(Lubrication Failure)* | **Baseline (0–2599)**<br>**Incipient (2600–3199)**<br>**Moderate (3200–3599)**<br>**Severe (3600–3999)** | 2.117<br>**4.594**<br>**13.552**<br>**25.007** | 5.088<br>**11.862**<br>**20.680**<br>**33.773** | $14.54 \pm 0.72\text{ A}$<br>$16.25 \pm 1.63\text{ A}$<br>$21.31 \pm 1.76\text{ A}$<br>$26.88 \pm 2.00\text{ A}$ | 0.000<br>**1.393**<br>**5.258**<br>**8.297** | 0.5000<br>**0.8248**<br>**1.0000**<br>**1.0000** | Secondary Vib & Temp:<br>Incipient: $d = 1.07 / 1.32$<br>Moderate: $d = 4.11 / 4.75$<br>Severe: $d = 6.66 / 8.06$ |

### Explanation of Stage-Specific Statistical Differences:
In the earlier exploratory audit draft, an alternative subdivision was computed (Incipient: 2600–2999 [400 steps], Moderate: 3000–3499 [500 steps], Severe: 3500–3999 [500 steps]).
- In the **approved Step 3.2 boundaries**, the Incipient stage extends to step 3199 (600 steps total, where progression reaches $0.4286$ vs. $0.2857$). Because fault growth is non-linear, incorporating steps 3000–3199 increases the average incipient Mahalanobis distance from $\approx 2.4 - 3.4$ up to $\approx 4.2 - 4.6$ and raises primary sensor AUC from $\approx 0.79 - 0.85$ to $\approx 0.81 - 0.87$.
- Similarly, the approved Severe stage (3600–3999; 400 steps) isolates the final peak progression ($0.7143 \to 1.0000$), where Mahalanobis distances average $20.6 - 27.6$ (peak single-step $D_M$ reaches $39.1$). Both boundary definitions confirm the same physical reality: incipient faults exhibit realistic overlap, whereas late-stage faults are overwhelmingly separable.

### Figure 6: Multi-Stage Fault Trajectories & Separability Margins
![Fault Progression and Separability](graphs/fault_progression_and_separability.png)
*Figure 6 displays normalized trajectories (Z-scores vs. fleet baseline) across all four faulted assets, demarcated by the approved Phase 2 Step 3.2 operational boundaries (Baseline: 0–2599; Incipient: 2600–3199; Moderate: 3200–3599; Severe: 3600–3999).*

---

## 6. Machine Identity and Fault Identity Interpretation

A rigorous scientific distinction must be drawn between two orthogonal phenomena:

### A. Healthy Baseline Similarity (Absence of Normal Machine Fingerprinting)
- Normal, healthy telemetry across all 10 machines exhibits statistically indistinguishable baseline means (ANOVA $F \in [0.46, 0.93]$, all $p > 0.49$; cross-machine CV $< 0.15\%$).
- This empirical homogeneity eliminates the concern that models are inadvertently memorizing unique machine baseline offsets (e.g. M101 running at $45^\circ\text{C}$ vs M102 at $52^\circ\text{C}$) to flag anomalies during normal operation.

### B. Fault-Type and Machine-Identity Confounding (100% Collinearity)
- In contrast to baseline homogeneity, **fault types and machine identities are 100% confounded**:
  - Machine **M102** exclusively represents **Overheating**.
  - Machine **M104** exclusively represents **Bearing wear**.
  - Machine **M107** exclusively represents **Pressure drop**.
  - Machine **M109** exclusively represents **Lubrication failure**.
  - Machines **M101, M103, M105, M106, M108, M110** remain **100% healthy**.
- **Crucial Generalization Limitation:** Because each failure mode occurs on exactly one machine and is never replicated on any other asset, **cross-machine fault-type generalization cannot be established**. The system demonstrates **within-machine temporal anomaly detection**, but cannot prove that a model trained on M104 bearing wear will generalize to an unobserved asset experiencing bearing wear.

---

## 7. Reconciled Test Window Counts

### Discrepancy Investigation & Resolution:
The preliminary draft of the audit text inadvertently cited "571 overlapping test windows". A complete audit of the sequence generation codebase and stored artifacts resolves this discrepancy:

1. **Mathematical Derivation:**
   - Test partition length per machine: $N_{\text{test}} = 600$ readings.
   - Sequence window length: $W = 30$ timesteps.
   - Sequence stride: $S = 10$ timesteps.
   - Number of windows per machine:
     $$\left\lfloor \frac{N_{\text{test}} - W}{S} \right\rfloor + 1 = \left\lfloor \frac{600 - 30}{10} \right\rfloor + 1 = \frac{570}{10} + 1 = 57 + 1 = 58 \text{ windows per machine}$$
   - Across 10 machines:
     $$10 \text{ machines} \times 58 \text{ windows} = \mathbf{580} \text{ overlapping test sequences}$$
2. **Source of the "571" Typo:** The number 571 arose from an accidental arithmetic error where an analyst evaluated $(600 - 30) = 570$ and added $1$ ($570 + 1 = 571$), mistakenly omitting the division by stride $S = 10$.
3. **Artifact Corroboration:**
   - In `data/processed/sequences_test.npz`, array `X.shape` is exactly `(580, 30, 5)`.
   - In `data/processed/clean_sensor_windows.csv`, `partition == "test"` contains exactly `580` records (58 rows each for M101–M110).
   - In non-overlapping evaluation ($W=30, S=30$), each machine produces $600 / 30 = 20$ windows, totaling **200 independent test windows**.
4. **Conclusion:** The authoritative overlapping test sequence count is confirmed to be **580**. No sequences or partitions were altered.

---

## 8. Controlled Noise Experiment Specifications (E0–E7)

All experiment parameters are formalized in [`reports/phase2/dataset_realism_experiment_plan.json`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/dataset_realism_experiment_plan.json).

### Crucial Methodological Labeling:
The noise scales $\alpha \in \{0.05, 0.10, 0.20\}$ for experiments E1–E3 are **experimental synthetic perturbation levels** chosen to explore model degradation margins. They are **not** standardized industrial vendor tolerances.

Reference healthy training standard deviations ($\sigma_c$):
- $\sigma_{\text{vib}} = 0.2235\text{ mm/s}$
- $\sigma_{\text{temp}} = 2.2030^\circ\text{C}$
- $\sigma_{\text{press}} = 0.1211\text{ bar}$
- $\sigma_{\text{curr}} = 0.7094\text{ A}$
- $\sigma_{\text{rpm}} = 7.4553\text{ RPM}$

```
+---------------------------------------------------------------------------------------------------------+
| EXPERIMENTAL MATRIX (reports/phase2/dataset_realism_experiment_plan.json)                               |
+------+--------------------------+-----------------------------------+-----------------------------------+
| ID   | Experiment               | Mathematical Formulation          | Engineering Nature / Purpose      |
+------+--------------------------+-----------------------------------+-----------------------------------+
| E0   | Baseline Benchmark       | x' = x                            | Unaltered test partition ground-  |
|      |                          |                                   | truth reference (F1: 95.2%/99.1%) |
| E1   | Low Gaussian Noise       | x' = x + N(0, (0.05 * sigma_c)^2) | Synthetic perturbation level: 5%  |
| E2   | Moderate Gaussian Noise  | x' = x + N(0, (0.10 * sigma_c)^2) | Synthetic perturbation level: 10% |
| E3   | High Gaussian Noise      | x' = x + N(0, (0.20 * sigma_c)^2) | Synthetic perturbation level: 20% |
| E4   | AR(1) Colored Noise      | e_t = 0.65*e_{t-1} + eta_t        | Stationary sigma = 10%;           |
|      |                          | (sigma_eta = 0.07599 * sigma_c)   | Correlated thermal/inertial lag   |
| E5   | Linear Sensor Drift      | x' = x + beta_c * (t/600)         | Drift scale: 1.0 * sigma_c;       |
|      |                          |                                   | Simulates sensor aging & fouling  |
| E6   | Transient Spikes         | x' = x + Bernoulli(p=0.002) * A_t | Pulse amplitude: 3.0–5.0*sigma_c; |
|      |                          |                                   | Simulates switching surges & EMI  |
| E7   | Composite Disturbance    | E4 (AR1) + E5 (Drift) + E6 (Spike)| Multi-modal industrial stress     |
+------+--------------------------+-----------------------------------+-----------------------------------+
```

### Rigorous Parameterization of AR(1) Correlated Noise (Experiment E4):
The AR(1) autoregressive noise process is formulated as:
$$\epsilon_{t,c} = \rho \cdot \epsilon_{t-1,c} + \eta_{t,c}, \quad \eta_{t,c} \sim \mathcal{N}(0, \sigma_{\eta,c}^2)$$

1. **Theoretical Relationship & Derivation:**
   For a weakly stationary AR(1) process with $|\rho| < 1$, the marginal stationary variance is:
   $$\text{Var}(\epsilon_t) = \sigma_{\text{stat}}^2 = \frac{\sigma_\eta^2}{1 - \rho^2} \implies \sigma_{\text{stat}} = \frac{\sigma_\eta}{\sqrt{1 - \rho^2}}$$
   To achieve the desired target **stationary marginal standard deviation** of $\sigma_{\text{stat},c} = 0.10 \cdot \sigma_c$ with $\rho = 0.65$:
   $$\sigma_{\eta,c} = \sigma_{\text{stat},c} \cdot \sqrt{1 - \rho^2} = 0.10 \cdot \sigma_c \cdot \sqrt{1 - 0.65^2} = 0.10 \cdot \sigma_c \cdot \sqrt{0.5775} \approx \mathbf{0.0759934} \cdot \sigma_c$$

2. **Explicit Distinction between Stationary and Innovation Standard Deviation:**
   - **Stationary Noise Standard Deviation ($\sigma_{\text{stat},c} = 0.10 \sigma_c$):** The long-run marginal dispersion of the noise across time, governing total perturbation energy.
   - **Innovation Noise Standard Deviation ($\sigma_{\eta,c} \approx 0.07599 \sigma_c$):** The standard deviation of the independent Gaussian driving shock injected at each discrete timestep $t$.

3. **Sensor-Specific AR(1) Numerical Scales:**
   - Vibration: $\sigma_{\text{stat}} = 0.02235\text{ mm/s} \implies \sigma_\eta = \mathbf{0.01698\text{ mm/s}}$
   - Temperature: $\sigma_{\text{stat}} = 0.22030^\circ\text{C} \implies \sigma_\eta = \mathbf{0.16741^\circ\text{C}}$
   - Pressure: $\sigma_{\text{stat}} = 0.01211\text{ bar} \implies \sigma_\eta = \mathbf{0.00920\text{ bar}}$
   - Current: $\sigma_{\text{stat}} = 0.07094\text{ A} \implies \sigma_\eta = \mathbf{0.05391\text{ A}}$
   - RPM: $\sigma_{\text{stat}} = 0.74553\text{ RPM} \implies \sigma_\eta = \mathbf{0.56655\text{ RPM}}$

4. **Initialization & Burn-In Protocol:**
   To prevent transient under-dispersion during early steps, the initial state $\epsilon_0$ must be sampled directly from the stationary distribution $\epsilon_0 \sim \mathcal{N}(0, \sigma_{\text{stat}}^2)$, or generated with $B = 100$ preliminary burn-in iterations discarded prior to sequence injection.

---

## 9. Frozen-Model Robustness Evaluation Protocol (Task E)

The designed evaluation protocol enforces strict scientific boundaries:
1. **Frozen Artifacts:**
   - Pre-fitted scaler: `ml/models_store/sensor_scaler.joblib` (NEVER refitted; applies existing $\mu$ and $\sigma$).
   - Trained Isolation Forest: `ml/models_store/isolation_forest.joblib` (frozen weights).
   - Trained LSTM Autoencoder: `ml/models_store/lstm_autoencoder.keras` (frozen weights).
   - Calibrated thresholds: $\tau_{\text{IF}} = 0.0269$, $\tau_{\text{LSTM}} = 0.901464$.
2. **Multi-Faceted Evaluation Criteria:**
   - **Tabular & Sequential Detection:** Accuracy, Precision, Recall, F1-Score, ROC-AUC, PR-AUC, False Positive Rate (FPR), False Discovery Rate (FDR).
   - **Resolution Differentiation:** Explicit separation between overlapping test sequences (stride = 10, $N = 580$) and independent test sequences (stride = 30, $N = 200$).
   - **Explainability Robustness:** Preservation of top-1 root cause feature ranking, attribution entropy across features, and signed residual concordance in standardized space.
   - **Early Warning Integrity:** Detection delay (timesteps after $t=2600$ to first alarm), incipient-stage recall ($t \in [2600, 3200)$), and false alarm count on the 6 healthy machines.

---

## 10. Critical Experimental Separation

To preserve methodological integrity, two distinct research tracks are maintained:

```
+---------------------------------------------------------------------------------------------------------+
| RESEARCH TRACK SEPARATION                                                                               |
+----------------------------------------------------+----------------------------------------------------+
| EXPERIMENT A: Frozen-Model Robustness (Audited)    | EXPERIMENT B: Noise-Augmented Retraining (Future)  |
+----------------------------------------------------+----------------------------------------------------+
| * Evaluates existing production models on noisy     | * Explores whether retraining models on noisy data |
|   validation/test copies.                          |   improves domain generalization.                  |
| * Scaler, model weights, and thresholds are FROZEN.| * Requires retraining models and recalibrating     |
| * Measures how well current models survive real-   |   decision boundaries.                             |
|   world telemetry imperfections.                   | * SEPARATELY APPROVED FUTURE TASK.                 |
| * Strictly executed in-memory.                     | * PROHIBITED during Phase 2 Step 4 / Realism Audit.|
+----------------------------------------------------+----------------------------------------------------+
```
These two tracks address fundamentally different questions and **must never be combined or confused**.

---

## 11. Overall Realism Verdict

### Overall Verdict: **CONDITIONALLY REALISTIC WITH IDENTIFIED SIMPLIFICATIONS**

1. **Physically Sound Macro-Dynamics:** The inclusion of 24-hour diurnal ambient cycling, factory shift load adjustments, and multi-sensor fault couplings provides a solid foundation for industrial demonstration.
2. **Realistic Incipient Stage:** Incipient fault detection under the approved Phase 2 Step 3.2 boundaries ($t=2600–3199$) provides a legitimate, non-trivial ML challenge characterized by subtle signal-to-noise ratios and genuine overlap ($D_M \approx 4.2 - 4.6$, AUC $\approx 0.77 - 0.87$).
3. **Identified Simplifications:** The lack of temporal noise autocorrelation ($\rho = 0$), absence of healthy machine baseline variation, 100% machine-to-fault confounding, and extreme late-stage fault separability explain why the models achieve near-perfect overall F1-scores.
4. **Final Recommendation:** The experimental plan (**E0–E7**) is fully specified and ready for frozen-model evaluation when explicitly approved by the user.

---
*Audit completed independently in compliance with all Phase 2 preservation and read-only constraints.*
