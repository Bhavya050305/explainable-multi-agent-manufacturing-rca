# ManuMind AI — Independent Audit: Synthetic Fault Separability

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.1 — Audit D: Physical Sensor Feature Separability Analysis
**Auditor:** Independent Senior ML Engineer & Auditor
**Date:** November 2026
**Status:** **AUDITED — PRIMARY DRIVER OF HIGH TEST BENCHMARKS CONFIRMED**

---

## 1. Executive Summary

This audit evaluated why both **Model 1 (Isolation Forest)** and **Model 2 (LSTM Autoencoder)** achieved near-perfect anomaly detection metrics on the held-out test dataset:
- Isolation Forest: Recall = $100.0\%$, ROC-AUC = $0.9979$, PR-AUC = $0.9965$
- LSTM Autoencoder: Recall = $100.0\%$, ROC-AUC = $1.0000$, PR-AUC = $1.0000$

Having confirmed in **Audit B** that zero data leakage or label contamination exists, this audit investigated the underlying physical distributions of the synthetic telemetry dataset generated in `ml/data_generator/generate_sensor_data.py`.

### Primary Finding
> [!IMPORTANT]
> **The extraordinarily high performance of both anomaly detection models is primarily driven by synthetic fault separability.**
> In the held-out test split (timesteps 3,400 to 4,000), the injected progressive faults operate in their **severe degradation phase** ($progression \in [0.57, 1.00]$). The resulting sensor deviations range from **$10\times$ to $40\times$ the baseline standard deviation ($Z$-scores between $+22$ and $+39.5$)**.
>
> Because the lowest reconstruction error among anomalous sequences in the test set ($24.76$) is over **$25\times$ higher** than the highest error among normal sequences ($0.96$), the anomaly detection boundary is wide and unambiguous.

---

## 2. Quantitative Sensor Separability & Effect Sizes

The five physical sensor channels were analyzed across all 40,000 telemetry readings, comparing normal baseline readings ($N=34,400$) against injected fault readings ($N=5,600$).

### Baseline vs. Faulted Feature Contrast Table

| Sensor Channel | Nominal Baseline Mean ($\pm \sigma$) | Injected Fault | Faulted Fleet Mean ($\pm \sigma$) | Z-Score Deviation | Cohen's $d$ Effect Size | Separability Assessment |
|---|:---:|---|:---:|:---:|:---:|:---:|
| **Vibration** (mm/s) | $1.800 \pm 0.220$ | M104 Bearing Spalling | $5.940 \pm 2.450$ | **$+18.82$** | **$+2.38$ (Huge)** | Massive vibration spikes in late spalling phase |
| **Temperature** (°C) | $48.000 \pm 1.200$ | M102 Thermal Runaway | $76.200 \pm 12.800$ | **$+23.50$** | **$+3.09$ (Huge)** | Thermal surge far exceeds diurnal ambient swings ($2.5^\circ\text{C}$) |
| **Pressure** (bar) | $6.200 \pm 0.120$ | M107 Pneumatic Blowout | $3.950 \pm 0.950$ | **$-18.75$** | **$-3.33$ (Huge)** | Pressure drop is completely outside normal operational envelope |
| **Current** (A) | $14.500 \pm 0.700$ | M109 Lubrication Friction | $23.800 \pm 4.200$ | **$+13.29$** | **$+3.08$ (Huge)** | Motor stator draws extreme current to overcome dry friction |
| **RPM** (rev/min) | $1800.0 \pm 7.50$ | M104 Spindle Drag | $1765.0 \pm 18.20$ | **$-4.67$** | **$-2.50$ (Huge)** | Spindle deceleration under bearing seizure |

*Note: In statistical meta-analyses, a Cohen's $d \ge 0.8$ is categorized as a "large" effect size. In this dataset, the effect sizes exceed $2.3$ to $3.3$, indicating non-overlapping physical distributions.*

---

## 3. Timeline Breakdown: Incipient vs. Severe Failure Phases

The synthetic data generator (`ml/data_generator/generate_sensor_data.py`) configured fault injection as follows:
- **Total timesteps per machine:** 4,000 readings at 5-minute sampling intervals ($13.89 \text{ days}$).
- **Nominal Baseline Phase (0% to 65% of timeline):** Steps 0 to 2,599 (100% normal on all 10 machines).
- **Incipient Degradation Phase (65% to 80% of timeline):** Steps 2,600 to 3,199 ($progression \in [0.00, 0.43]$).
- **Severe Degradation Phase (80% to 100% of timeline):** Steps 3,200 to 3,999 ($progression \in [0.43, 1.00]$).

### How the Chronological Dataset Splits Map to Fault Progression

```
Operational Timeline (Steps 0 to 4000)
├─── [0 to 2599] Normal Baseline ───────────────────────┼─── [2600 to 4000] Injected Degradation ───┤
│                                                       │                                           │
├─── [0 to 2799] TRAIN PARTITION (70%) ─────────────────┼─── [2800-3399] VAL (15%) ─┼─ [3400-3999] TEST (15%)
│    - 28,000 rows (27,200 normal, 800 incipient)       │    - 6,000 rows           │    - 6,000 rows
│    - Anomalies strictly excluded from model fitting   │    - Steps 2800 to 3399   │    - Steps 3400 to 3999
│    - Only normal baseline fitted                      │    - Progression:         │    - Progression:
│                                                       │      0.14 to 0.57         │      0.57 to 1.00
└───────────────────────────────────────────────────────┴───────────────────────────┴───────────────────────
```

### Critical Consequence on Test Evaluation
Because the Test Split comprises steps **3,400 to 3,999**, all 600 test readings for the 4 faulted machines (`M102, M104, M107, M109`) occur when:
$$progression \in [0.5714, 1.0000]$$

In this late regime:
1. **M104 (Bearing Spalling):** Progression is $> 0.57$. The quadratic vibration term $(progression^{2.2}) \times 7.5$ contributes $+2.2\text{ mm/s}$ to $+8.7\text{ mm/s}$. Baseline is $1.8 \pm 0.22$. The resulting vibration is $4.0$ to $10.5\text{ mm/s}$—a $10\sigma$ to $39\sigma$ deviation.
2. **M102 (Overheating):** Progression is $> 0.57$. The thermal term $(progression^{1.3}) \times 45.0$ contributes $+21.6^\circ\text{C}$ to $+45.0^\circ\text{C}$. The resulting temperature is $70^\circ\text{C}$ to $95^\circ\text{C}$—an $18\sigma$ to $37\sigma$ deviation.
3. **M107 (Pressure Drop):** Progression is $> 0.57$. Pressure drops by $1.7\text{ bar}$ to $3.8\text{ bar}$. Pressure falls to $2.4\text{ bar}$ against a nominal $6.2 \pm 0.12$ ($31\sigma$ deviation).
4. **M109 (Lubrication Friction):** Progression is $> 0.57$. Motor current surges by $6.7\text{ A}$ to $15.5\text{ A}$. Current reaches $21\text{ A}$ to $30\text{ A}$ against nominal $14.5 \pm 0.7$ ($22\sigma$ deviation).

---

## 4. Impact on Reconstruction Error Separation

The LSTM Autoencoder measures reconstruction error using Mean Squared Error across all 30 timesteps and 5 channels:
$$\text{MSE}(X) = \frac{1}{30 \times 5} \sum_{t=1}^{30} \sum_{c=1}^5 (x_{t,c} - \hat{x}_{t,c})^2$$

Because the encoder-decoder was trained strictly on healthy sequences ($x \sim \mathcal{N}(0, 1)$), it reconstructs healthy test sequences with small residual errors:
- **Normal Test Sequences ($N=348$):**
  - Minimum Error: $0.4412$
  - Mean Error: $0.6938$
  - Maximum Error: $0.9609$
  - Standard Deviation: $0.0714$

When presented with late-stage anomalous sequences ($progression \in [0.57, 1.00]$):
- **Anomalous Test Sequences ($N=232$):**
  - Minimum Error: $24.7624$ (M102 early test window)
  - Mean Error: $99.6920$
  - Maximum Error: $299.9549$ (M104 peak vibration window)
  - Standard Deviation: $48.2105$

### The Separation Gap
$$\min(\text{Error}_{\text{anomaly}}) - \max(\text{Error}_{\text{normal}}) = 24.7624 - 0.9609 = \mathbf{23.8015}$$

The lowest anomalous error is **$25.77\times$ higher** than the highest normal error.
There is **zero overlap** between normal and anomalous reconstruction error distributions in the test set.

This non-overlapping gap is the exact reason why:
1. Every anomaly ranks above every normal sequence, yielding **ROC-AUC = 1.0000** and **PR-AUC = 1.0000**.
2. Both models achieve **Recall = 100.0%** (zero false negatives).
3. The only classification errors are the 4 false positives in the normal fleet ($1.15\%$ FPR), which were intentionally accepted by setting the threshold at the 99th percentile of normal validation errors ($\tau = 0.901464$).

---

## 5. Visual Evidence

The following generated figures in `reports/phase2/model_audit/graphs/` provide visual evidence:
1. **`normal_vs_anomalous_sensor_distributions.png`**: Displays KDE density curves for all 5 sensors, showing the wide separation between the green (normal) and red (faulted) peaks.
2. **`fault_progression.png`**: Displays the 4,000-step trajectory for M102, M104, M107, and M109, clearly delineating the transition from incipient degradation (steps 2600–3400) into severe degradation in the test partition (steps 3400–4000).
3. **`reconstruction_error_distributions.png`**: Log-scale KDE showing the wide bimodal separation between normal errors ($< 1.0$) and anomalous errors ($> 20.0$), with the threshold line ($\tau = 0.901464$) positioned cleanly in the valley.

---

## 6. Audit Conclusion & Synthesis

1. **Not Overfitting:** The models did not memorize training artifacts; they learned the nominal operational manifold ($\mu \approx 0, \sigma \approx 1$).
2. **Not Data Leakage:** The test set was strictly held out and observed only during final metric evaluation.
3. **Synthetic Separability:** The test partition benchmark evaluates the models on **severe late-stage equipment failure**, where physical signals deviate by dozens of standard deviations.
4. **Industrial Implication:** While the models perform properly on this synthetic benchmark, performance on real-world industrial machinery with subtle sensor noise, variable ambient conditions, and gradual incipient wear will exhibit lower precision and recall.
