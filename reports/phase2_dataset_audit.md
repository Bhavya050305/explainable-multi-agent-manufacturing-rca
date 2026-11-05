# ManuMind AI — Phase 2: Machine Learning Dataset Quality & Audit Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science
**Report Type:** Phase 2 Pre-Training Dataset Quality Audit (Step 0)
**Date:** November 2026
**Status:** **AUDIT COMPLETE — READY FOR REVIEW & APPROVAL**

---

## 1. Executive Summary

Prior to initiating any model training for Phase 2 of ManuMind AI, a rigorous, automated audit of all operational datasets, temporal splits, sliding windows, failure horizons, visual inspection images, and maintenance logs was conducted using `backend/app/ml/inspect_datasets.py`.

### Key Audit Findings

| Data Component | Metric / Parameter | Value | Assessment |
|---|---|---|---|
| **Sensor Telemetry** | Total readings | 40,000 | Complete (10 machines $\times$ 4,000 steps) |
| | Missing / Null values | 0 (0.00%) | Passed |
| | Duplicate rows | 0 (0.00%) | Passed |
| | Sampling interval | 5.0 minutes (exact) | Uniform & strictly monotonic |
| | Total anomalies | 5,600 (14.00%) | Balanced operational anomaly distribution |
| **Temporal Splits** | Train / Val / Test split | 70% / 15% / 15% | Strictly chronological (0..2799, 2800..3399, 3400..3999) |
| **Sliding Windows** | Window count / Size / Stride | 3,980 windows / 30 steps / 10 stride | Verified |
| | Temporal leakage in raw windows | 40 straddling windows detected | **Action Required:** Fix window extraction boundaries |
| **Failure Prediction Horizon** | Degradation span | 1,400 steps (116.7 hours) | Gradual exponential degradation |
| | 24-hour lead horizon | 288 timesteps | **Optimal & highly actionable** |
| | 48-hour lead horizon | 576 timesteps | Feasible for long-term warning |
| **Defect Images** | Total count / Dimensions | 600 images / 128 $\times$ 128 $\times$ 3 BMP | Valid 24-bit headers, uncorrupted |
| | Class balance | 150 per class (4 classes) | Perfectly balanced (surface_crack, spalling, dent, normal) |
| | Image duplicates | 0 duplicate SHA-256 hashes | Verified |
| **Maintenance History** | Total records | 400 (40 per machine) | Consistent maintenance history |

---

## 2. Sensor Telemetry Dataset Audit

### 2.1 File & Record Integrity
- **File path:** `data/raw/sensor_readings.csv`
- **Total records:** 40,000 rows across 10 machines (`M101` through `M110`), exactly 4,000 rows per machine.
- **Null values:** 0 in all columns (`machine_id`, `timestamp`, `vibration`, `temperature`, `pressure`, `current`, `rpm`, `is_anomaly`, `fault_type`, `fault_severity`, `failure_risk`).
- **Timestamp monotonicity:** Verified strictly monotonic for all machines ($t_i > t_{i-1}$).
- **Sampling cadence:** Uniform 5.0-minute interval ($\Delta t = 300\text{ s}$). Total operational span per machine is $4,000 \times 5\text{ min} = 20,000\text{ min} \approx 13.89\text{ days}$.

### 2.2 Physical Sensor Channel Statistics

All 5 physical telemetry channels were validated against realistic industrial operating bounds for rotational equipment (electric motors, pumps, gearboxes, compressors):

| Channel | Units | Min | 1st Pct | Mean | Median | 99th Pct | Max | Std Dev | Plausibility |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **Vibration** | mm/s (RMS) | 0.816 | 1.289 | 1.962 | 1.820 | 6.403 | 10.984 | 0.841 | **Passed** (ISO 10816 class II/III) |
| **Temperature** | °C | 41.030 | 43.540 | 49.390 | 48.370 | 78.330 | 96.560 | 5.846 | **Passed** (Normal: 45–55°C, Fault: >75°C) |
| **Pressure** | bar | 2.170 | 3.810 | 6.172 | 6.200 | 7.340 | 8.350 | 0.422 | **Passed** (Hydraulic baseline ~6.2 bar) |
| **Current** | Amperes (A) | 11.620 | 12.900 | 14.878 | 14.610 | 23.740 | 32.250 | 1.727 | **Passed** (Motor draw nominal ~15A) |
| **Speed (RPM)** | RPM | 1700.400 | 1769.599 | 1799.316 | 1799.800 | 1817.400 | 1832.400 | 8.964 | **Passed** (Nominal 1800 RPM synchronous) |

### 2.3 Fault Distribution & Machine Breakdown
The dataset exhibits a realistic manufacturing health distribution:
- **Healthy Machines (60%):** `M101`, `M103`, `M105`, `M106`, `M108`, `M110` exhibit continuous normal baseline telemetry across all 4,000 timesteps (`is_anomaly = 0`).
- **Faulted Machines (40%):**
  - `M102` — Overheating fault (1,400 fault readings; peak temperature 96.56°C).
  - `M104` — Bearing wear fault (1,400 fault readings; peak vibration 10.984 mm/s, current rise to 32.25A).
  - `M107` — Pressure drop fault (1,400 fault readings; pressure degradation down to 2.17 bar).
  - `M109` — Lubrication failure (1,400 fault readings; concurrent friction-induced temperature rise and vibration spikes).

Overall label distribution:
- **Normal (`is_anomaly = 0`):** 34,400 readings (**86.0%**)
- **Anomaly (`is_anomaly = 1`):** 5,600 readings (**14.0%**)

---

## 3. Temporal Splitting & Leakage Audit

### 3.1 Chronological Partitioning
The dataset is split chronologically per machine to preserve time dependency:
- **Train Split (70%):** 28,000 rows (steps 0 to 2,799 per machine).
- **Validation Split (15%):** 6,000 rows (steps 2,800 to 3,399 per machine).
- **Test Split (15%):** 6,000 rows (steps 3,400 to 3,999 per machine).

### 3.2 Anomaly Progression Across Splits
Because fault onset was injected at step 2,600 (out of 4,000), the progression through the temporal splits realistically captures early onset, moderate progression, and severe degradation:
- **Train (steps 0..2799):** Contains 200 anomaly steps for each faulted machine (steps 2600..2799, initial subtle onset). 6 healthy machines are 100% normal.
- **Validation (steps 2800..3399):** Contains 600 anomaly steps per faulted machine (progressive drift).
- **Test (steps 3400..3999):** Contains 600 anomaly steps per faulted machine (severe failure progression).

### 3.3 Critical Finding: Boundary Straddling Windows
In `data/processed/sensor_windows.csv`, windows were extracted by sliding a window of length $W=30$ with stride $S=10$ across the entire 4,000-timestep sequence per machine.

**The Audit Detected 40 Straddling Windows:**
- Windows starting at steps 2,780 and 2,790 end at steps 2,810 and 2,820, crossing the Train-Validation boundary (step 2,800).
- Windows starting at steps 3,380 and 3,390 end at steps 3,410 and 3,420, crossing the Validation-Test boundary (step 3,400).
- Across 10 machines, $4 \times 10 = 40$ windows cross split boundaries.

> [!WARNING]
> **Temporal Leakage Risk in Direct Window Utilization:** If models are trained or evaluated on `sensor_windows.csv` without partition boundary isolation, observations from the validation or test sets would leak into training sequences.

### 3.4 Corrective Action for Step 1
In the preprocessing pipeline (`backend/app/ml/preprocessing/sensor_preprocessing.py`), sequence windows will be extracted **within each partition independently**:
- **Train Windows:** Extracted only from indices $t \in [0, 2769]$ (all window timesteps $\le 2799$).
- **Validation Windows:** Extracted only from indices $t \in [2800, 3369]$ (all window timesteps $\le 3399$).
- **Test Windows:** Extracted only from indices $t \in [3400, 3969]$ (all window timesteps $\le 3999$).
- **Result:** Exactly zero boundary-straddling windows and mathematical guarantee of zero temporal leakage.

---

## 4. Failure Prediction Horizons & Target Formulation

### 4.1 Time Horizons at 5-Minute Cadence
- $1\text{ hour} = 12\text{ timesteps}$
- $24\text{ hours} = 288\text{ timesteps}$
- $48\text{ hours} = 576\text{ timesteps}$

### 4.2 Degradation Timeline
For the 4 degraded machines (`M102, M104, M107, M109`):
1. **Normal Baseline:** Steps 0 to 2,599 ($0\text{ to }216.7\text{ hours}$). `failure_risk` $\le 0.08$.
2. **Degradation Inception:** Step 2,600 ($t = 216.7\text{ hours}$). `failure_risk` begins rising exponentially.
3. **Actionable Warning Phase:** Steps 3,400 to 3,750 ($t = 283.3\text{ to }312.5\text{ hours}$). `failure_risk` spans $0.40$ to $0.80$.
4. **Critical Breakdown Threshold:** Around step 3,750–3,800. `failure_risk` exceeds $0.80$, vibration exceeds $6.0\text{ mm/s}$, or temperature exceeds $80^\circ\text{C}$.

### 4.3 Proposed Predictive Target Definition
To train Random Forest and XGBoost classifiers for predictive maintenance:
$$\text{failure\_in\_24h}_t = \begin{cases} 1 & \text{if machine reaches critical breakdown within } [t, t + 288] \\ 0 & \text{otherwise} \end{cases}$$

This target gives plant operators a 24-hour actionable lead time to schedule maintenance before functional failure occurs, satisfying all academic and practical requirements.

---

## 5. Visual Defect Inspection Dataset Audit

### 5.1 Image Specifications
- **Manifest path:** `data/defect_images/defect_manifest.json`
- **Total images:** 600 files stored in `data/defect_images/`
- **Format:** Uncompressed Windows Bitmap (BMP), 24-bit true color (8 bits per RGB channel).
- **Dimensions:** Exactly $128 \times 128 \times 3$ pixels.
- **Header integrity:** 100% of images verified with `BM` header signature and valid DIB header structure.
- **Corrupted files:** 0 corrupted or unreadable images.
- **Cryptographic uniqueness:** 0 duplicate SHA-256 hashes across all 600 files.
- **Synthetic provenance:** 100% of images verified with `is_synthetic: true`.

### 5.2 Defect Class Distribution
The dataset is balanced across 4 surface inspection categories:

| Defect Class | Image Count | Class Proportion | Description / Visual Signature |
|---|---:|---:|---|
| **normal_surface** | 150 | 25.0% | Clean, machined surface texture with uniform background noise |
| **surface_crack** | 150 | 25.0% | Irregular linear dark fissures traversing across the component |
| **spalling** | 150 | 25.0% | Localized pitting and flaking clusters caused by subsurface fatigue |
| **dent** | 150 | 25.0% | Circular impact impressions with central depression and shaded rim |
| **Total** | **600** | **100.0%** | **Perfect 4-class balance** |

### 5.3 Partition Distribution
- **Train Split:** 420 images (70.0%)
- **Validation Split:** 88 images (14.7%)
- **Test Split:** 92 images (15.3%)

---

## 6. Maintenance History Quality Audit

- **Records:** 400 total rows across 10 machines (40 records per machine).
- **Schema:** `id`, `machine_id`, `maintenance_date`, `maintenance_type`, `description`, `technician_id`, `parts_replaced`, `notes`.
- **Integrity:** 0 null values, valid ISO 8601 timestamps, consistent foreign keys matching `machines`.
- **Feature Engineering Utility:** Provides historical maintenance intervals ($\Delta t$ since last maintenance, cumulative maintenance count) as predictive features for failure risk models.

---

## 7. Machine Learning Pipeline Recommendations (Phase 2 Steps 1–7)

Based on this comprehensive audit, the following implementation architecture is formulated:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 2 ML Pipeline                             │
└────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┴───────────────────────────┐
       ▼                                                        ▼
┌───────────────────────────────┐               ┌──────────────────────────────┐
│     Telemetry Models          │               │      Vision Model            │
├───────────────────────────────┤               ├──────────────────────────────┤
│ 1. Preprocessing:             │               │ 6. ResNet Defect Classifier  │
│    - StandardScaler on Train  │               │    - Input: 128x128x3        │
│    - Non-leaking sequences    │               │    - 4 classes (Crack, Dent, │
│ 2. Isolation Forest (Tabular) │               │      Spalling, Normal)       │
│ 3. LSTM Autoencoder (Temporal)│               │    - Target: F1 >= 0.85      │
│ 4. Sensor Attribution (Error) │               └──────────────────────────────┘
│ 5. Failure Risk:              │
│    - RF vs XGBoost (24h lead) │
│    - PR-AUC, ROC-AUC >= 0.85  │
│    - SHAP TreeExplainer       │
└───────────────────────────────┘
```

1. **Step 1 — Preprocessing & Sequence Windows:**
   - Fit `StandardScaler` strictly on the 28,000-row Train split.
   - Extract isolated sequence windows: Train (steps 0..2769), Val (steps 2800..3369), Test (steps 3400..3969).
   - Guarantee zero temporal leakage.
2. **Step 2 — Model 1: Tabular Anomaly Detection (Isolation Forest):**
   - Train on healthy operating readings (`is_anomaly = 0` in Train set).
   - Evaluate on Test split: target F1 $\ge 0.85$, ROC-AUC $\ge 0.90$.
3. **Step 3 — Model 2: Temporal Sequence Anomaly Detection (LSTM Autoencoder):**
   - Input shape: $(30, 5)$ (30 timesteps $\times$ 5 sensor channels).
   - Architecture: Encoder LSTM(64) $\to$ LSTM(32) $\to$ RepeatVector(30) $\to$ Decoder LSTM(32) $\to$ LSTM(64) $\to$ TimeDistributed(Dense(5)).
   - Set threshold at 99th percentile of normal validation reconstruction error.
4. **Step 4 — Model 3: Sensor-Level Anomaly Attribution:**
   - Compute channel-wise Mean Squared Error: $\text{MSE}_c = \frac{1}{T} \sum_{t=1}^T (x_{t,c} - \hat{x}_{t,c})^2$.
   - Attribute anomaly root causes to specific sensor channels (vibration, temperature, pressure, current, rpm).
5. **Step 5 — Model 4: Failure-Risk Prediction (Random Forest vs XGBoost):**
   - Feature engineering: rolling means ($W=12, 36$), rolling stds ($W=12, 36$), rate of change, time since maintenance.
   - Compare Random Forest and XGBoost with ROC-AUC and PR-AUC.
6. **Step 6 — Model 5: Explainability with SHAP:**
   - Initialize `shap.TreeExplainer` on the best failure-risk model.
   - Generate summary plot, feature importance bar plot, and local waterfall plot for top anomalies; save to `reports/figures/`.
7. **Step 7 — Model 6: Vision Defect Classification (ResNet):**
   - Train ResNet on 128$\times$128$\times$3 images across the 4 balanced defect classes.
   - Evaluate on test set (92 images): target F1 $\ge 0.85$.

---

## 8. Audit Verification Status & Sign-Off

- **Telemetry Data Quality:** **PASSED** (0 nulls, 0 duplicates, monotonic 5-min cadence)
- **Image Data Quality:** **PASSED** (0 corrupted, 100% valid headers, 0 duplicates, perfectly balanced)
- **Temporal Partitioning:** **PASSED** (Chronological 70/15/15 split)
- **Temporal Leakage Safeguard:** **DEFINED & READY** (Boundary-safe window extraction designed)
- **Predictive Horizon Feasibility:** **CONFIRMED** (24h lead time with 288 steps)

**Audit Status:** Complete and verified. Ready for user review and approval to proceed with Step 1 (Preprocessing & Sequence Window generation).
