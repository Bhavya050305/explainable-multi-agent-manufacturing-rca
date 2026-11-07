# ManuMind AI — Phase 2 Step 7: Independent Implementation & Scientific Integrity Audit

**Department of AI & Data Science — RMK Engineering College**
**Role:** Senior Computer Vision ML Engineer, ML Research Auditor & Independent Git Release Auditor
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Repository:** `D:\Desktop\FInal year project\manumind-ai`
**Branch:** `main`
**Baseline Commit:** `11d979f`
**Audit Date:** 2026-11-07
**Status:** **AUDIT COMPLETE — CONDITIONAL APPROVAL (CORRECTIONS REQUIRED PRIOR TO STAGING)**

---

## Executive Summary of Audit Verdict

An exhaustive, independent technical audit was conducted on the Phase 2 Step 7 ResNet Vision Defect Classifier implementation, training artifacts, evaluation metrics, automated test suite, and Git state.

### Final Audit Determination: <badge color="warning">CONDITIONAL APPROVAL — CORRECTIONS REQUIRED</badge>

The underlying Python code, Keras model architecture, manifest DataLoader, training pipeline, evaluation calculations, and unit tests are technically sound, leak-free, and fully reproducible. Zero regressions were introduced across previous Phase 1 and Phase 2 Steps 0–6 (77/77 backend tests pass).

However, staging is conditionally withheld pending the reconciliation of **three documentation discrepancies** identified between the implementation report (`reports/phase2/resnet_defect_classifier_report.md`) and the verified source code / manifest data:
1. **Batch Identifier Mismatch:** The report states batch IDs as `B202401`, `B202402`, and `B202403`, whereas the canonical source of truth (`defect_manifest.json`) and the Python config (`config.py`) use `B-8821`, `B-7740`, and `B-9910`.
2. **Stem Layer Narrative Inaccuracy:** The report describes the stem as a "single $3\times3$ convolution with stride 1 (avoiding $7\times7$ filters)", whereas the actual implemented code (`model.py` lines 113–124) utilizes a classic ResNet stem: `Conv2D(32, 7x7, strides=2)` followed by `BatchNormalization`, `ReLU`, and `MaxPooling2D(3x3, strides=2)`.
3. **Dropout Layer Classification:** The report refers to "Spatial Dropout", whereas the code implements standard post-pooling `layers.Dropout(rate=0.35)`.

Once these documentation records are reconciled, the release is cleared for staging.

---

## 1. Verified Architecture & Parameter Counts

### 1.1 Source-Code Inspection (`model.py` and `config.py`)
- **Residual Block Structure:** Implemented via `residual_basic_block()` in [`model.py` lines 17–92](file:///d:/Desktop/FInal%20year%20project/manumind-ai/backend/app/ml/defect_classifier/model.py#L17-L92). Each block consists of:
  $$\text{Conv2D}(3\times3, \text{stride}) \to \text{BN} \to \text{ReLU} \to \text{Conv2D}(3\times3, \text{stride}=1) \to \text{BN} \to \text{Add}(\text{shortcut}) \to \text{ReLU}$$
  Projection shortcuts with `Conv2D(1x1, stride)` and `BatchNormalization` are correctly applied when spatial downsampling occurs or when channel count changes.
- **Stage Layout:** Four residual stages with 2 BasicBlocks each (`stage_blocks = [2, 2, 2, 2]`), matching the 18-layer residual topology (1 stem conv + 16 residual convs + 1 dense head = 18 parameterized layers).
- **Channel Progression:** `[32, 64, 128, 256]` with strides `[1, 2, 2, 2]` across stages 1 through 4.
- **Stem Architecture:**
  - Code: `Conv2D(filters=32, kernel_size=7, strides=2, padding="same", use_bias=False)` $\to$ `BatchNormalization` $\to$ `ReLU` $\to$ `MaxPooling2D(pool_size=3, strides=2, padding="same")`.
  - Audited finding: This retains the standard ResNet receptive field while halving the channel depth (32 vs. 64 filters).
- **Classification Head:**
  - `GlobalAveragePooling2D` $\to$ `Dropout(rate=0.35)` $\to$ `Dense(units=4, activation="softmax", kernel_regularizer=l2(1e-4))`.
- **Regularization:** $L_2$ kernel regularization ($1 \times 10^{-4}$) is applied across all 17 convolutional layers, 3 projection layers, and the final dense projection layer.
- **Training from Scratch Verification:** Genuinely built from scratch (`weights=None`). No pretrained weights (ImageNet or otherwise) are initialized or downloaded.

### 1.2 Parameter Count Verification
Parameter counts were verified by evaluating Keras tensors directly and independently summing trainable and non-trainable weights:

| Architectural Metric | Audited Code Summary (`model.py`) | Metadata Sidecar (`metadata.json`) | Implementation Report Table | Audit Match |
| :--- | :---: | :---: | :---: | :---: |
| **Total Parameters** | **2,804,708** | 2,804,708 | 2,804,708 | **EXACT MATCH** |
| **Trainable Parameters** | **2,799,908** | 2,799,908 | 2,799,908 | **EXACT MATCH** |
| **Non-Trainable (BN) Parameters** | **4,800** | 4,800 | 4,800 | **EXACT MATCH** |
| **Number of BN Layers** | 20 layers ($20 \times 4$ params/channel) | 20 layers | 20 layers | **EXACT MATCH** |

### 1.3 Standard ResNet-18 Baseline Equivalence
The comparative standard ResNet-18 implementation in `model.py` (`build_standard_resnet18()`) was audited. It uses an **equivalent 4-class classification head** (`GlobalAveragePooling2D -> Dropout(0.35) -> Dense(4, softmax)`), identical $L_2$ regularization ($10^{-4}$), identical BN momentum ($0.85$), and identical input shape ($128 \times 128 \times 3$), varying strictly in channel progression (`[64, 128, 256, 512]` and stem filters 64).
- Standard ResNet-18 parameters: **11,188,164** ($11,178,564$ trainable, $9,600$ non-trainable BN).
- Parameter delta: **74.93% reduction** ($2,804,708$ vs. $11,188,164$). The comparison is methodologically fair and mathematically exact.

---

## 2. Dataset and Manifest Integrity Audit

### 2.1 Manifest Source of Truth (`data/defect_images/defect_manifest.json`)
The manifest was parsed and audited:
- **Total Records:** Exactly **600** records.
- **Split Breakdown:**
  - `train`: **420** records (70.0%)
  - `val`: **88** records (14.67%)
  - `test`: **92** records (15.33%)
- **Class Balance:** Exactly **150** samples per class across the entire manifest (`surface_crack`: 150, `spalling`: 150, `dent`: 150, `normal_surface`: 150).
  - Train partition: Exactly **105** samples per class.
  - Validation partition: Exactly **22** samples per class.
  - Frozen test partition: Exactly **23** samples per class.
- **Manifest-Only Loading:** Verified in `dataset.py` line 60. `load_manifest()` strictly reads JSON entries from `defect_manifest.json`. No disk discovery (`os.walk` / `os.listdir`) is performed.
- **Legacy Prototype File Exclusion:** Confirmed that the 16 unmanifested prototype BMP files on disk (`M101_normal_surface_01.bmp` through `04.bmp`, `M102_dent_01.bmp` through `04.bmp`, `M104_spalling_01.bmp` through `04.bmp`, `M104_surface_crack_01.bmp` through `04.bmp`) do not exist in `defect_manifest.json` and are never loaded into memory.
- **Corrupt Image Check:** All 600 manifest image files open cleanly with PIL, have dimensions $128 \times 128$, and 3 RGB color channels.
- **Duplicate Hashes:** Evaluated in Phase 1 audit: 0 duplicate cryptographic hashes among the 600 images.

### 2.2 Critical Reconciliation: Batch Identifier Discrepancy
The audit discovered a discrepancy between the batch numbers stated in the implementation report and those stored in the actual manifest and configuration:

| Machine ID | Defect Class | Actual Manifest Batch (`defect_manifest.json`) | Config Lookup Batch (`config.py`) | Reported Batch (`report.md` Section 7) | Discrepancy Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **M104** | `surface_crack` | **`B-8821`** | **`B-8821`** | `B202401` | **Report Typo** |
| **M104** | `spalling` | **`B-8821`** | **`B-8821`** | `B202401` | **Report Typo** |
| **M102** | `dent` | **`B-7740`** | **`B-7740`** | `B202402` | **Report Typo** |
| **M101** | `normal_surface` | **`B-9910`** | **`B-9910`** | `B202403` | **Report Typo** |

**Auditor Finding on Confounding Reality:**
- The actual batch identifiers in the repository are **`B-8821`**, **`B-7740`**, and **`B-9910`**.
- The Python configuration (`config.py` `MACHINE_BATCH_LOOKUP`) and Pydantic tests (`test_pydantic_schema_compatibility`) already use the true manifest values (`B-8821`, `B-7740`, `B-9910`).
- The previous implementation report narrative inadvertently substituted placeholder names (`B202401`, `B202402`, `B202403`).
- **The documented machine/batch confounding remains 100% accurate and valid:**
  - Both `surface_crack` and `spalling` are bound to **M104 / B-8821**.
  - `dent` is bound to **M102 / B-7740**.
  - `normal_surface` is bound to **M101 / B-9910**.
  - All three machine/batch combinations span train, val, and test splits.

---

## 3. Training Dynamics & Leakage Audit

### 3.1 Gradient Isolation & Partition Separation
- **Gradient Updates:** `train.py` line 187 calls `model.fit(train_ds, validation_data=val_ds, ...)`.
  - `train_ds` is populated strictly from `partitions["train"]` (420 samples).
  - Backpropagation and gradient updates are computed solely from `train_ds`.
- **Data Augmentation Scoping:**
  - `build_augmentation_layer()` is invoked only on `train_ds` when `is_training=True` (`dataset.py` lines 208–211).
  - `val_ds` is constructed with `is_training=False`, `augment_layer=None`, and `shuffle=False`.
- **Test Set Zero-Exposure:**
  - `train.py` does not load, preprocess, augment, or evaluate `partitions["test"]`.
  - Preprocessing is a fixed mathematical mapping: $x \mapsto \frac{x}{127.5} - 1.0$. Because this transformation contains no empirical parameters (unlike `StandardScaler` mean and variance), there is zero inter-sample statistical leakage.

### 3.2 Checkpoint Selection & Callbacks
- **Validation-Based Selection:** `ModelCheckpoint` monitors `val_loss` with `save_best_only=True` and `mode="min"`.
- **Early Stopping & Weight Restoration:** `EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)` and `ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4)`.
- **Restoration Integrity:** Training ran for 35 epochs. Validation loss reached its minimum of **$0.424704$** at **Epoch 33**. Weights were restored from Epoch 33 at the conclusion of training.

---

## 4. Frozen Test Evaluation Audit

### 4.1 Evaluation Evidence & Single-Pass Verification
The evaluation artifacts in `reports/phase2/defect_classifier/` and `ml/models_store/` were audited:
- **Test Sample Count:** Exactly **92** test predictions in `defect_predictions.csv` and `defect_classifier_results.json`.
- **Prediction Representation:** Every single one of the 92 test images from the manifest appears exactly once in `defect_predictions.csv` with matching metadata (`machine_id`, `batch_number`, `defect_type`).
- **Confusion Matrix Sum:**
  $$\begin{pmatrix} 23 & 0 & 0 & 0 \\ 0 & 23 & 0 & 0 \\ 0 & 0 & 23 & 0 \\ 0 & 0 & 0 & 23 \end{pmatrix} \implies \sum C_{ij} = 92$$
- **Metric Verification:**
  - Accuracy: $\frac{92}{92} = 1.0000$ (100.0%)
  - Macro F1: $\frac{1}{4} \sum_{c=1}^4 1.0 = 1.0000$
  - Macro Precision: $1.0000$
  - Macro Recall: $1.0000$
  - Per-class precision, recall, specificity, and F1: Exactly $1.0000$ across all 4 classes.
  - Multi-class One-vs-Rest ROC-AUC: $1.0000$ for all classes.
- **Probability Simplex Normalization:**
  - Raw Softmax tensor output sums to $1.0$ within machine float32 precision ($|\sum p_i - 1.0| \le 1.192 \times 10^{-7}$).
  - In `defect_predictions.csv`, values are formatted to 4 decimal places, producing row sums between $0.9999$ and $1.0001$ strictly due to float truncation.
- **Single Evaluation Verification:** Timestamps and metadata confirm the test partition was evaluated strictly once on the restored Epoch 33 checkpoint.

### 4.2 Numerical Correctness vs. Scientific Generalization
> [!IMPORTANT]
> **Auditor Caveat on Perfect Metrics:**
> While the $1.0000$ Macro F1-score is **numerically verified and mathematically correct** on the frozen test partition, this perfect score **does not imply that the model will generalize to real-world industrial environments or unseen machines**.
> The 100% accuracy is a direct consequence of:
> 1. High topological feature contrast in the synthetic procedural defect generator.
> 2. Complete machine and batch entanglement (all test images share the background characteristics of the training images from M101, M102, and M104).

---

## 5. Batch Normalization Calculation Audit

### 5.1 Verification of Stated Mathematical Relations
In Keras Batch Normalization, moving statistics are updated per batch via:
$$\mu_{\text{mv}}^{(t)} = m \cdot \mu_{\text{mv}}^{(t-1)} + (1 - m) \cdot \mu_{\text{batch}}^{(t)}$$
Unrolling over $k = 14$ batches (1 epoch on 420 samples with batch size 32):
$$\mu_{\text{mv}}^{(14)} = m^{14} \mu_{\text{mv}}^{(0)} + \sum_{i=1}^{14} (1 - m) m^{14-i} \mu_{\text{batch}}^{(i)}$$
The cumulative weight assigned to new observations (the assimilation factor) is:
$$\alpha(k) = 1 - m^k$$

- **Default Momentum ($m = 0.99$, $k = 14$):**
  $$0.99^{14} \approx 0.868743 \implies \alpha(14) = 1 - 0.868743 \approx 0.131257 \approx \mathbf{13.13\%}$$
- **Configured Momentum ($m = 0.85$, $k = 14$):**
  $$0.85^{14} \approx 0.102766 \implies \alpha(14) = 1 - 0.102766 \approx 0.897234 \approx \mathbf{89.72\%}$$
- **Three Epochs with Configured Momentum ($m = 0.85$, $k = 42$):**
  $$0.85^{42} \approx 0.001085 \implies \alpha(42) = 1 - 0.001085 \approx \mathbf{99.89\%}$$

### 5.2 Scientific Distinction: Algebraic Assimilation vs. Statistical Convergence
The audit confirms that the reported percentages ($13.1\%$ and $89.7\%$) represent the **algebraic exponential weight decay of the initial prior** in the linear recurrence relation.

**Critical Distinction:**
- Algebraic assimilation measures the *speed* at which the moving average incorporates recent batch inputs.
- It does **not** prove mathematical convergence to the true population distribution moments $\mathbb{E}[X]$ and $\text{Var}[X]$. Representation drift in early convolutional layers during initial training epochs can still perturb moving estimates.
- Empirically, however, setting $m = 0.85$ prevented the severe evaluation-mode activation shifts observed under $m = 0.99$.

---

## 6. Latency Audit & Benchmarking Methodology

### 6.1 Benchmark Implementation Inspection (`evaluate.py`)
- **Warm-up Passes:** Exactly **10** forward passes (`n_warmup = 10`) to prime TensorFlow computational graphs.
- **Timed Iterations:** Exactly **100** individual forward passes (`n_iterations = 100`).
- **Batch Size:** Strictly **$1$** (`input_shape = (1, 128, 128, 3)`), accurately simulating single-workpiece edge camera inspection.
- **Timing Scope:**
  - Code times strictly: `_ = model(dummy_input, training=False)`.
  - Disk I/O, BMP decoding, resizing, and normalization are **excluded**.
  - Model loading is **excluded**.
- **Reported Statistics (Host CPU):**
  - Mean Latency: **$156.57\text{ ms}$**
  - Median Latency: **$159.39\text{ ms}$**
  - 95th Percentile (P95): **$214.09\text{ ms}$**
  - Min / Max: **$101.89\text{ ms}$ / $259.64\text{ ms}$**
  - Throughput: **$6.4\text{ images/second}$**

### 6.2 Deployment Caveat
This benchmark was conducted on native Windows host CPU execution without GPU acceleration. It represents a **local workstation baseline**, not an industrial production SLA. Real-world edge inspection latency would incorporate camera image acquisition and GigE transfer overhead, while the forward pass itself would be accelerated significantly ($< 15\text{ ms}$) on dedicated edge accelerators (NVIDIA Jetson, Intel OpenVINO).

---

## 7. Automated Test Suite Audit

### 7.1 Test Inspection (`backend/tests/test_resnet_defect_classifier.py`)
The 11 unit and integration tests were inspected for assertion rigor:

| Test Name | Verified Assertion | Test Nature / Rigor |
| :--- | :--- | :--- |
| `test_manifest_loading_and_unmanifested_isolation` | Exactly 600 records (420/88/92); excludes 16 legacy files | **High Rigor** (Structural integrity) |
| `test_image_dimensions_and_channel_order` | Dimensions $(128, 128, 3)$, dtype `float32` | **High Rigor** (Tensor validity) |
| `test_deterministic_label_mapping` | Exact 4-class bijection and config mappings | **High Rigor** (Contract integrity) |
| `test_partition_class_balance` | Exact balance per class across all 3 splits | **High Rigor** (Statistical balance) |
| `test_deterministic_preprocessing_bounds` | Pixel bounds strictly in $[-1.0, 1.0]$ | **High Rigor** (Numerical bounds) |
| `test_model_architecture_and_parameter_counts` | Exactly $2,804,708$ total, $2,799,908$ trainable | **High Rigor** (Exact parameter counts) |
| `test_model_output_shape_and_simplex_properties` | Output shape $(B, 4)$, probabilities sum to 1.0 | **High Rigor** (Simplex properties) |
| `test_data_augmentation_pipeline` | Checks output shape $(2, 128, 128, 3)$ | **Moderate Rigor** (Smoke test on shape) |
| `test_multiclass_evaluation_metrics` | Computes metrics on synthetic known cases | **High Rigor** (Algorithmic accuracy) |
| `test_latency_benchmarking` | Validates benchmark outputs $> 0$ | **Smoke Test** (Execution only) |
| `test_pydantic_schema_compatibility` | Schema serialization and validation | **High Rigor** (API contract) |

### 7.2 Full Backend Regression Suite Execution
Executed `pytest backend/tests -v` across the entire project:
- `test_isolation_forest.py`: 10 passed
- `test_lstm_autoencoder.py`: 10 passed
- `test_phase1_audit_and_expansion.py`: 9 passed
- `test_phase1_db_and_generator.py`: 4 passed
- `test_resnet_defect_classifier.py`: 11 passed
- `test_sensor_attribution.py`: 18 passed
- `test_shap_explainability.py`: 15 passed

**Total:** **77 passed out of 77 collected items in 53.32s (100% pass rate, 0 regressions)**.

---

## 8. Artifact and Reproducibility Audit

### 8.1 Model Artifact & Checksum Verification
- **Artifact Path:** `ml/models_store/resnet_defect_classifier.keras` (32.8 MB)
- **Metadata Path:** `ml/models_store/resnet_defect_classifier_metadata.json` (7.9 KB)
- **Cryptographic SHA-256 Checksum:**
  - Actual File Hash: `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98`
  - Metadata Recorded: `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98`
  - **Verdict:** Exact cryptographic match.

### 8.2 Git Ignore Policy
- `.gitignore` line 34 specifies `ml/models_store/*` with exception `!ml/models_store/.gitkeep`.
- As verified via `git status --ignored`, both the binary `.keras` model weights and the `.json` metadata file in `ml/models_store/` are properly ignored by Git. This prevents committing large binaries to the repository.
- Reproducibility is guaranteed because `backend/app/ml/defect_classifier/train.py` can regenerate identical weights from scratch using deterministic seed 42.

---

## 9. Protected Artifact and Git Audit

### 9.1 Baseline Commit & Working Tree Verification
- Current Git HEAD: `11d979f53f5ae5c6058b9c3a7b37d87cf75f3718` (`11d979f`).
- Branch: `main` (synchronized with `origin/main`).
- Tracked File Diff (`git diff`): **Clean (0 lines modified)**.
- Staged Diff (`git diff --cached`): **Clean (0 staged changes)**.

### 9.2 Preservation of Prior Steps (Steps 0–6)
- Phase 1 synthetic data & migrations: **100% preserved**.
- Phase 2 Step 1 scaler (`sensor_scaler.joblib`) & scaled CSVs: **100% preserved**.
- Phase 2 Step 2 Isolation Forest (`isolation_forest.joblib`): **100% preserved**.
- Phase 2 Step 4 LSTM Autoencoder (`lstm_autoencoder.keras`): **100% preserved**.
- Phase 2 Step 6 SHAP Explainability Engine: **100% preserved**.
- Untracked files are strictly restricted to Step 7 modules, tests, reports, and generated evaluation artifacts.

---

## 10. Outstanding Corrections & Action Items

Before Git staging and commit authorization, the following three documentation corrections must be applied to `reports/phase2/resnet_defect_classifier_report.md`:

| # | File | Location | Existing Inaccurate Content | Required Correct Content | Reason |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | `reports/phase2/resnet_defect_classifier_report.md` | Sections 7.1 & 7.2 | References to batches `B202401`, `B202402`, `B202403` | Replace with canonical manifest batches: **`B-8821`** (M104), **`B-7740`** (M102), **`B-9910`** (M101) | Align report with `defect_manifest.json` and `config.py` |
| **2** | `reports/phase2/resnet_defect_classifier_report.md` | Section 2.1 | "Single 3x3 convolution with 32 filters, stride 1" | Replace with actual code: **"Conv2D(32, 7x7, stride 2) + BN + ReLU + MaxPool2D(3x3, stride 2)"** | Match actual `model.py` implementation |
| **3** | `reports/phase2/resnet_defect_classifier_report.md` | Section 2.1 | "Spatial Dropout ($p=0.35$)" | Replace with: **"Dropout ($p=0.35$) following GlobalAveragePooling2D"** | Accurate layer classification |

---

## 11. Final Decision & Next Steps

### Official Audit Verdict:
<badge color="warning">CONDITIONAL APPROVAL — CORRECTIONS REQUIRED</badge>

**Summary:** The code, architecture, training, and evaluation are verified and scientifically sound. Once the three documentation corrections in `reports/phase2/resnet_defect_classifier_report.md` are performed, the release is approved for staging and commit.

**Status:** STOPPING AS INSTRUCTED. AWAITING USER REVIEW AND EXPLICIT INSTRUCTIONS TO PROCEED WITH REPORT CORRECTIONS.
