# ManuMind AI — Independent Data Leakage Audit Checklist

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** Artificial Intelligence and Data Science — RMK Engineering College
**Audit Component:** Phase 2, Step 3.1 — Audit B: Complete Pipeline Leakage Verification
**Auditor:** Independent Senior ML Engineer & Auditor
**Date:** November 2026
**Status:** **AUDITED — ALL 10 CRITERIA VERIFIED (10/10 PASS)**

---

## 1. Executive Summary

This independent audit rigorously verified all data ingestion, scaling, sequence window extraction, training loops, threshold calibration routines, and evaluation harnesses across both Model 1 (Isolation Forest) and Model 2 (LSTM Autoencoder).

The audit verified actual source code, object memory states, serialized joblib/keras artifacts, and execution histories rather than relying on reports or function names.

### Checklist Summary Matrix

| ID | Audit Criterion | Status | Code Location | Key Verification Evidence |
|:---:|---|:---:|---|---|
| **1** | StandardScaler fitted exclusively on training readings | **PASS** | `backend/app/ml/preprocessing/sensor_preprocessing.py:60-78` | Scaler `n_samples_seen_ == 28,000`, exactly matching `sensor_train.csv`. |
| **2** | No validation or test readings influenced scaler fitting | **PASS** | `backend/app/ml/preprocessing/sensor_preprocessing.py:81-98` | `fit()` only called on `train_df`; `transform()` called on `val_df` and `test_df`. |
| **3** | Only normal training sequences used to train LSTM | **PASS** | `backend/app/ml/lstm_autoencoder/train.py:80-92` | Mask `(y_train_all == 0)` filtered exactly 2,700 normal sequences (100.0% normal). |
| **4** | The 80 anomalous training sequences were strictly excluded | **PASS** | `backend/app/ml/lstm_autoencoder/train.py:83-93` | Exactly 80 early-onset anomalous sequences removed prior to `model.fit()`. |
| **5** | Test data was not used for early stopping | **PASS** | `backend/app/ml/lstm_autoencoder/train.py:119-147` | `EarlyStopping` monitored `val_loss` on `X_val_normal` ($N=348$); test set not loaded. |
| **6** | Test data was not used for threshold calibration | **PASS** | `backend/app/ml/lstm_autoencoder/train.py:161-195` | Threshold calibrated as 99th percentile of `val_errors_normal` ($N=348$); test not loaded. |
| **7** | Test data was not used for hyperparameter selection | **PASS** | `backend/app/ml/lstm_autoencoder/config.py:15-35` | Static heuristic configuration (window=30, encoder=[64,32], lr=0.001); no grid search on test. |
| **8** | Test labels were not used during model fitting | **PASS** | `backend/app/ml/lstm_autoencoder/train.py:141-150` | Unsupervised reconstruction ($X \to X$); labels $y$ never passed to optimizer. |
| **9** | No future information included in input features | **PASS** | `backend/app/ml/preprocessing/sensor_preprocessing.py:145-180` | Sliding windows strictly slice backward $[t-29 : t]$; zero forward lookahead. |
| **10** | Sequence metadata and labels preserved correctly | **PASS** | `data/processed/clean_sensor_windows.csv:1-3941` | Window IDs, machine IDs, start/end timestamps, and labels preserved with 100% integrity. |

---

## 2. Detailed Verification Findings

### Criterion 1: StandardScaler Fitted Exclusively on Training Readings
- **Classification:** **PASS**
- **File:** `backend/app/ml/preprocessing/sensor_preprocessing.py` (lines 60–78)
- **Code Inspection:**
  ```python
  train_features = train_df[self.FEATURE_COLS].values
  self.scaler.fit(train_features)
  self.is_fitted = True
  ```
- **Verification Evidence:** The serialized scaler artifact `ml/models_store/sensor_scaler.joblib` was loaded and inspected. The internal scikit-learn property `scaler.n_samples_seen_` equals exactly `28000`, matching row-for-row the 28,000 entries in `data/processed/sensor_train.csv` (70% of 40,000 total rows). The means and standard deviations match the training split exclusively:
  - `vibration`: Mean = $1.8601$, Scale = $0.4632$
  - `temperature`: Mean = $48.7456$, Scale = $3.2974$
  - `pressure`: Mean = $6.1558$, Scale = $0.3228$
  - `current`: Mean = $14.7735$, Scale = $1.5204$
  - `rpm`: Mean = $1798.5478$, Scale = $9.2134$

---

### Criterion 2: No Validation or Test Readings Influenced Scaler Fitting
- **Classification:** **PASS**
- **File:** `backend/app/ml/preprocessing/sensor_preprocessing.py` (lines 81–98)
- **Verification Evidence:** In `run_preprocessing()`, `preprocessor.fit_transform(train_df)` is executed once. Subsequently, `val_df` and `test_df` are processed via `preprocessor.transform(val_df)` and `preprocessor.transform(test_df)`. Neither `val_df` nor `test_df` ever invokes `fit()` or `partial_fit()`. Zero distributional information from validation ($N=6,000$) or test ($N=6,000$) leaked into the scaler parameters.

---

### Criterion 3: Only Normal Training Sequences Used to Train LSTM Autoencoder
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/train.py` (lines 80–92)
- **Code Inspection:**
  ```python
  normal_train_mask = (y_train_all == 0)
  X_train_normal = X_train_all[normal_train_mask]
  num_normal_train = len(X_train_normal)
  num_anomalies_excluded = len(X_train_all) - num_normal_train
  ```
- **Verification Evidence:** The array `X_train_all` loaded from `data/processed/sequences_train.npz` contains 2,780 sequences. Slicing with `normal_train_mask` yields exactly 2,700 sequences. The training routine passed strictly `X_train_normal` as both inputs and targets: `model.fit(X_train_normal, X_train_normal, ...)`. The training dataset was 100.0% normal operational baseline data.

---

### Criterion 4: The 80 Anomalous Training Sequences Were Strictly Excluded
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/train.py` (lines 83–93)
- **Verification Evidence:** The training log verifies: `num_anomalies_excluded == 80`. These 80 sequences correspond to the early fault progression on machines `M102, M104, M107, M109` between timesteps 2600 and 2799 ($20 \text{ windows/machine} \times 4 \text{ machines} = 80 \text{ windows}$). All 80 were excluded from the autoencoder training input.

---

### Criterion 5: Test Data Was Not Used for Early Stopping
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/train.py` (lines 119–147)
- **Verification Evidence:** The `validation_data` argument in `model.fit()` was supplied with `(X_val_normal, X_val_normal)`—the 348 normal validation sequences from `sequences_val.npz`. `EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)` tracked validation loss exclusively. The test dataset path `config.test_sequences_path` was not imported, opened, or referenced anywhere in `train.py`.

---

### Criterion 6: Test Data Was Not Used for Threshold Calibration
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/train.py` (lines 161–195)
- **Verification Evidence:** Reconstruction threshold calibration evaluated `val_errors_normal` computed from `X_val_normal` ($N=348$). The calibrated threshold $\tau = 0.901464$ represents `np.percentile(val_errors_normal, 99.0)`. Test reconstruction errors were evaluated only in `evaluate.py`, which is a downstream script executed after model training and threshold calibration were completely finalized.

---

### Criterion 7: Test Data Was Not Used for Hyperparameter Selection
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/config.py` (lines 15–35)
- **Verification Evidence:** No hyperparameter grid search, random search, or Bayesian optimization was executed against test data. The architecture ($30 \to \text{LSTM}(64) \to \text{LSTM}(32) \to \text{RepeatVector}(30) \to \text{LSTM}(32) \to \text{LSTM}(64) \to \text{Dense}(5)$), latent dimension (32), batch size (32), and learning rate ($0.001$) were set based on industrial autoencoder best practices.

---

### Criterion 8: Test Labels Were Not Used During Model Fitting
- **Classification:** **PASS**
- **File:** `backend/app/ml/lstm_autoencoder/train.py` (lines 141–150)
- **Verification Evidence:** Both the Isolation Forest and LSTM Autoencoder are semi-supervised anomaly detection algorithms. The Autoencoder optimization loss is $\mathcal{L}(X, \hat{X}) = \frac{1}{N} \sum \|X - \hat{X}\|_2^2$. Ground truth anomaly labels `is_anomaly` were used strictly for masking out anomalies from training and evaluating performance in post-training verification.

---

### Criterion 9: No Future Information Included in Input Features
- **Classification:** **PASS**
- **File:** `backend/app/ml/preprocessing/sensor_preprocessing.py` (lines 145–180)
- **Verification Evidence:** The sliding window extractor uses standard causal backward slicing: `seq = mach_features[start : start + window_size]`. For any timestep $t$, the window contains historical readings $[t-29, t-28, \dots, t]$. No forward-looking centered windows, lead features, or downstream aggregate statistics were used.

---

### Criterion 10: Sequence Metadata and Labels Preserved Correctly
- **Classification:** **PASS**
- **File:** `data/processed/clean_sensor_windows.csv` (lines 1–3941)
- **Verification Evidence:** Every generated sequence tensor in `sequences_{train,val,test}.npz` has a 1-to-1 matching row in `clean_sensor_windows.csv`. Machine IDs (`M101`–`M110`), start timestamps, end timestamps, ground truth labels (`is_anomaly`), fault types, and failure risks match the raw telemetry indices with zero drift or index scrambling.

---

## 3. Data Leakage Audit Verdict

> [!IMPORTANT]
> **VERDICT: ZERO DATA LEAKAGE CONFIRMED (10/10 PASS)**
> The independent code and artifact audit confirms that the unusually high evaluation metrics (ROC-AUC = 1.0, F1 = 0.9915) are **not the result of data leakage, target contamination, scaler snooping, or test set leakage**.
