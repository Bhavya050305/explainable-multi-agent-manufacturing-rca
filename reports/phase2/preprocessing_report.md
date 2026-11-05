# ManuMind AI — Phase 2: Telemetry Preprocessing & Sequence Generation Report (Step 1)

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science
**Report Type:** Phase 2 Step 1 Implementation & Technical Verification Report
**Date:** November 2026
**Status:** **STEP 1 COMPLETED & VALIDATED (8/8 UNIT TESTS PASSED)**

---

## 1. Executive Summary

In accordance with Phase 2 requirements, **Step 1 (Preprocessing & Sequence Generation)** has been implemented in [`backend/app/ml/preprocessing/sensor_preprocessing.py`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/preprocessing/sensor_preprocessing.py).

This pipeline enforces strict data leakage prevention, standardizes 5-channel multivariate industrial telemetry using a `StandardScaler` fitted **exclusively** on the training partition, and extracts clean, non-leaking sequence windows for temporal deep learning (LSTM Autoencoder).

### Core Achievements

| Metric / Requirement | Target / Constraint | Realized Output | Status |
|---|---|---|:---:|
| **StandardScaler Fitting** | Fit on Train ONLY (28,000 rows) | $\mu \approx 0, \sigma = 1.0$ on Train; Val/Test untouched | **PASSED** |
| **Straddling Windows** | Eliminate 40 boundary-crossing windows | Exactly 40 windows removed ($3,980 \to 3,940$) | **PASSED** |
| **Sequence Dimensions** | Length $W=30$, Features $C=5$, Stride $S=10$ | Train: `(2780, 30, 5)`, Val: `(580, 30, 5)`, Test: `(580, 30, 5)` | **PASSED** |
| **Temporal Boundary Leakage** | 0 boundary-crossing sequences | Exactly 0 sequences cross temporal boundaries | **PASSED** |
| **Machine Mixing** | 0 cross-machine sequences | Exactly 0 sequences cross machine boundaries | **PASSED** |
| **Missing Values / NaNs** | 0 missing values | 0 NaNs across all scaled arrays and sequence tensors | **PASSED** |
| **Duplicates** | 0 duplicate timestamps | 0 duplicate records across all partitions | **PASSED** |
| **Database Immutability** | Supabase & SQLite untouched | Supabase (40,416 rows) & SQLite (7.5 MB) 100% intact | **PASSED** |
| **Unit Test Suite** | 100% pass rate | 8 passed in 18.54s (`backend/tests/test_sensor_preprocessing.py`) | **PASSED** |

---

## 2. Rigorous Preprocessing Validation Audit

The preprocessing pipeline was verified against 8 strict automated acceptance criteria:

```
[CHECK 1/8] Zero Missing Values:
  - Scaled tabular partitions (Train, Val, Test):  0 NaNs -> [PASS]
  - Sequence tensors (X_train, X_val, X_test):     0 NaNs -> [PASS]

[CHECK 2/8] Zero Duplicate Machine/Timestamp Records:
  - Scaled Train duplicates:                       0 -> [PASS]
  - Scaled Val duplicates:                         0 -> [PASS]
  - Scaled Test duplicates:                        0 -> [PASS]

[CHECK 3/8] Zero Temporal Boundary-Crossing Windows:
  - Max timestamp in Train windows < Min timestamp in Val partition -> [PASS]
  - Max timestamp in Val windows < Min timestamp in Test partition   -> [PASS]
  - Temporal leakage between partitions:          0.00% -> [PASS]

[CHECK 4/8] Straddling Windows Elimination:
  - Raw unconstrained windows:                     3,980
  - Clean partition-bounded windows:               3,940
  - Exactly eliminated straddling windows:         40 -> [PASS]

[CHECK 5/8] Zero Cross-Machine Window Mixing:
  - Group-by machine isolation verified:           10/10 machines -> [PASS]
  - Machine IDs strictly homogeneous within each 30-step window   -> [PASS]

[CHECK 6/8] Correct Sequence Dimensions & Dtype:
  - Train tensor shape:                            (2780, 30, 5) -> [PASS]
  - Validation tensor shape:                       (580, 30, 5)  -> [PASS]
  - Testing tensor shape:                          (580, 30, 5)  -> [PASS]
  - Data type:                                     np.float32    -> [PASS]

[CHECK 7/8] Strict Train-Only Scaler Fitting:
  - Scaler sample count seen:                      28,000 (100% Train) -> [PASS]
  - Scaled Train mean:                             [-3.8e-17, -2.5e-16, 2.7e-16, 1.4e-16, -1.9e-15] ≈ 0.0 -> [PASS]
  - Scaled Train standard deviation:               [1.000, 1.000, 1.000, 1.000, 1.000] -> [PASS]

[CHECK 8/8] Database & History Immutability:
  - SQLite database (`manumind.db`):               7,495,680 bytes (Unchanged) -> [PASS]
  - Supabase PostgreSQL (40,416 rows):             Verified 100% parity (Unchanged) -> [PASS]
```

---

## 3. Detailed Technical Analysis

### 3.1 StandardScaler Parameters (Fitted Strictly on Train)
The `StandardScaler` was fitted exclusively on the 28,000 training observations ($70\%$ of the dataset, representing steps 0 to 2,799 across all 10 machines).

$$\mu_c = \frac{1}{N_{\text{train}}} \sum_{i=1}^{N_{\text{train}}} x_{i,c}, \quad \sigma_c = \sqrt{\frac{1}{N_{\text{train}}} \sum_{i=1}^{N_{\text{train}}} (x_{i,c} - \mu_c)^2}$$

| Sensor Channel | Units | Training Mean ($\mu$) | Training Std ($\sigma$) | Training Variance ($\sigma^2$) | Samples Seen ($N$) |
|---|---|---:|---:|---:|---:|
| **Vibration** | mm/s | 1.8046 | 0.2266 | 0.0514 | 28,000 |
| **Temperature** | °C | 47.9981 | 2.1957 | 4.8213 | 28,000 |
| **Pressure** | bar | 6.2017 | 0.1222 | 0.0149 | 28,000 |
| **Current** | A | 14.5252 | 0.7111 | 0.5057 | 28,000 |
| **Speed (RPM)** | RPM | 1799.9475 | 7.4950 | 56.1757 | 28,000 |

*Validation and Test partitions were transformed using these exact constants with zero fitting or parameter recalculation.*

---

### 3.2 Sequence Window Extraction & Leakage Elimination

Industrial multivariate anomaly detection requires slicing time series into contiguous temporal windows:
- **Window Length ($W$):** 30 timesteps ($30 \times 5\text{ min} = 150\text{ minutes} = 2.5\text{ hours}$).
- **Stride ($S$):** 10 timesteps ($10 \times 5\text{ min} = 50\text{ minutes}$).
- **Features ($C$):** 5 channels (`vibration`, `temperature`, `pressure`, `current`, `rpm`).

#### Mathematical Derivation of Partition Windows
For a machine sequence of length $L$:
$$N_{\text{windows}} = \left\lfloor \frac{L - W}{S} \right\rfloor + 1$$

1. **Training Partition ($L = 2,800$ steps per machine):**
   $$N_{\text{train\_mach}} = \left\lfloor \frac{2800 - 30}{10} \right\rfloor + 1 = 277 + 1 = 278\text{ windows}$$
   Across 10 machines: $10 \times 278 = \mathbf{2,780\text{ windows}}$.
   *Indices span $[0, 2799]$. Window starts at step 2,770 and terminates at step 2,799. Zero overlap with step 2,800.*

2. **Validation Partition ($L = 600$ steps per machine):**
   $$N_{\text{val\_mach}} = \left\lfloor \frac{600 - 30}{10} \right\rfloor + 1 = 57 + 1 = 58\text{ windows}$$
   Across 10 machines: $10 \times 58 = \mathbf{580\text{ windows}}$.
   *Indices span $[2800, 3399]$. Window starts at step 3,370 and terminates at step 3,399. Zero overlap with step 3,400.*

3. **Testing Partition ($L = 600$ steps per machine):**
   $$N_{\text{test\_mach}} = \left\lfloor \frac{600 - 30}{10} \right\rfloor + 1 = 57 + 1 = 58\text{ windows}$$
   Across 10 machines: $10 \times 58 = \mathbf{580\text{ windows}}$.
   *Indices span $[3400, 3999]$. Window starts at step 3,970 and terminates at step 3,999.*

#### Straddling Windows Elimination Breakdown
- **Raw continuous windows:** $10 \times \left( \left\lfloor \frac{4000 - 30}{10} \right\rfloor + 1 \right) = 10 \times 398 = 3,980\text{ windows}$.
- **Isolated partition windows:** $2,780 + 580 + 580 = \mathbf{3,940\text{ windows}}$.
- **Difference:** $3,980 - 3,940 = \mathbf{40\text{ windows}}$ (20 crossing the Train/Val boundary + 20 crossing the Val/Test boundary).
- **Result:** Exactly 40 straddling windows eliminated. **Temporal leakage is 0.00%.**

---

### 3.3 Health State & Anomaly Distribution by Partition

A window is labelled anomalous (`is_anomaly = 1`) if any timestep in the window exhibits an injected physical fault.

| Partition | Total Sequences | Normal Sequences | Anomaly Sequences | Anomaly Proportion | Operational Stage Represented |
|---|---:|---:|---:|---:|---|
| **Train** | 2,780 | 2,700 | 80 | **2.88%** | Baseline healthy operations + subtle inception onset |
| **Validation** | 580 | 348 | 232 | **40.00%** | Moderate degradation & parameter drift |
| **Test** | 580 | 348 | 232 | **40.00%** | Severe wear, critical breakdown, imminent failure |
| **Total** | **3,940** | **3,396** | **544** | **13.81%** | **Realistic manufacturing operational spectrum** |

---

### 3.4 Physical Telemetry Pearson Correlation Analysis

The Pearson correlation coefficients ($r$) among physical sensors on the training baseline exhibit expected industrial dynamics:

| Sensor Pair | Correlation ($r$) | Physical Industrial Explanation |
|---|---:|---|
| **Temperature — Current** | **+0.412** | Increased motor winding electrical current causes $I^2 R$ Joule heating. |
| **Vibration — Current** | **+0.385** | Mechanical friction/eccentricity in bearings increases electrical torque load. |
| **Pressure — RPM** | **+0.218** | Centrifugal pump pressure is proportional to rotational shaft velocity. |
| **Vibration — Temperature** | **+0.344** | Bearing sub-surface fatigue causes concurrent frictional heat and micro-shocks. |
| **Pressure — Temperature** | **-0.082** | Fluid expansion slightly reduces viscosity and operating head pressure. |

---

## 4. Visual Evidence Gallery

All 5 high-resolution analytical figures have been generated and saved to [`reports/phase2/preprocessing/`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/):

### Figure 1: Sensor Feature Distributions Before vs After Standardization
*Shows kernel density estimates and histograms of all 5 sensor channels in engineering units (left) vs standardized $Z$-scores with $\mu=0, \sigma=1$ (right).*
File: [`reports/phase2/preprocessing/sensor_distributions_before_after.png`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/sensor_distributions_before_after.png)

### Figure 2: Chronological Split Distribution
*Visualizes sample counts and operational time proportions across Train (70%), Validation (15%), and Testing (15%).*
File: [`reports/phase2/preprocessing/split_distribution.png`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/split_distribution.png)

### Figure 3: Sequence Extraction Counts & Elimination of Straddling Windows
*Shows the partition sequence breakdown ($2,780, 580, 580$) and explicitly annotates the elimination of the 40 boundary-crossing windows.*
File: [`reports/phase2/preprocessing/sequence_counts.png`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/sequence_counts.png)

### Figure 4: Health State Breakdown Across Partitions
*Grouped bar charts comparing Normal vs Anomaly counts and percentages in raw telemetry (40,000 timesteps) vs sequence windows (3,940 windows).*
File: [`reports/phase2/preprocessing/anomaly_distribution_by_split.png`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/anomaly_distribution_by_split.png)

### Figure 5: Industrial Physical Telemetry Pearson Correlation Matrix
*Heatmap annotating linear correlation coefficients across all 5 physical telemetry features.*
File: [`reports/phase2/preprocessing/sensor_correlation_heatmap.png`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing/sensor_correlation_heatmap.png)

---

## 5. Artifact & File Inventory

### Source Modules & Pipelines
1. [`backend/app/ml/__init__.py`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/__init__.py) — Machine learning subpackage marker.
2. [`backend/app/ml/preprocessing/__init__.py`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/preprocessing/__init__.py) — Preprocessing package export interface.
3. [`backend/app/ml/preprocessing/sensor_preprocessing.py`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/preprocessing/sensor_preprocessing.py) — Reusable, production-grade preprocessing, sequence extraction, and visualization pipeline.

### Unit & Integration Tests
4. [`backend/tests/test_sensor_preprocessing.py`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_sensor_preprocessing.py) — Comprehensive 8-test pytest suite (**8/8 PASSED in 18.54s**).

### Model & Scaler Artifacts
5. [`ml/models_store/sensor_scaler.joblib`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib) — Serialized `StandardScaler` fitted on Train data.

### Processed Datasets & Compressed Sequence Tensors
6. [`data/processed/scaled_sensor_train.csv`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/scaled_sensor_train.csv) — 28,000 scaled training rows.
7. [`data/processed/scaled_sensor_val.csv`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/scaled_sensor_val.csv) — 6,000 scaled validation rows.
8. [`data/processed/scaled_sensor_test.csv`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/scaled_sensor_test.csv) — 6,000 scaled test rows.
9. [`data/processed/sequences_train.npz`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/sequences_train.npz) — Compressed tensors for LSTM: `X (2780, 30, 5)`.
10. [`data/processed/sequences_val.npz`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/sequences_val.npz) — Compressed tensors for LSTM: `X (580, 30, 5)`.
11. [`data/processed/sequences_test.npz`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/sequences_test.npz) — Compressed tensors for LSTM: `X (580, 30, 5)`.
12. [`data/processed/clean_sensor_windows.csv`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/data/processed/clean_sensor_windows.csv) — Clean sequence window metadata (3,940 rows, 0 straddling).

### Statistical Records & Audit Reports
13. [`reports/phase2/preprocessing_statistics.json`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing_statistics.json) — Complete machine-readable metrics.
14. [`reports/phase2/preprocessing_report.md`](file:///d:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/preprocessing_report.md) — This document.

---

## 6. Next Step Approval Gate

Step 1 (Telemetry Preprocessing & Sequence Generation) is **COMPLETE, VALIDATED, AND AUDITED**.

In accordance with our strict protocol:
- Isolation Forest, LSTM, Random Forest, XGBoost, SHAP, and ResNet model training have **NOT** been started.
- All original databases (SQLite `manumind.db` and Supabase PostgreSQL `postgres`) remain **UNTOUCHED**.

Awaiting user approval to proceed to:
**Step 2 — Model 1: Tabular Anomaly Detection (Isolation Forest)**.
