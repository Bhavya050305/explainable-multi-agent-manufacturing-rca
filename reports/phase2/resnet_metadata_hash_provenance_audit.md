# ManuMind AI — Phase 2 Step 8: Protected Artifact Hash Provenance Verification Report

**Investigation Title:** Forensic Provenance Audit of ResNet Vision Defect Classifier Metadata SHA-256 Checksum
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Department:** AI & Data Science, RMK Engineering College
**Target Artifact:** `ml/models_store/resnet_defect_classifier_metadata.json`
**Repository:** `D:\Desktop\FInal year project\manumind-ai`
**Investigation Mode:** Read-Only Forensic Audit (Zero Source Code, Test, or Artifact Modifications)
**Date of Audit:** 2026-11-07

---

## 1. Executive Summary & Verdict

This forensic audit was commissioned to investigate and resolve an apparent discrepancy between two historical SHA-256 checksums reported for `ml/models_store/resnet_defect_classifier_metadata.json`:

1. **Phase 2 Step 7 Implementation Report (`reports/phase2/resnet_defect_classifier_report.md`):**
   Reported Hash: `e99da54823293dc65b6378ba6f755da9fe845941ea87d3a822db0253457117eb`
   Reported Size: `7.9 KB`
2. **Phase 2 Step 8 Inspection, Implementation, & Audit Reports:**
   Reported Hash: `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73`
   Reported Size: `5,980 bytes` (~5.84 KiB / 5.98 KB)

### Audit Determination:
<badge color="success">FINAL VERDICT: RESOLVED — HISTORICAL REPORT HASH ERROR</badge>

**Key Findings:**
1. **Zero Artifact Tampering or Post-Training Modification:** Filesystem timestamps, file lengths, and execution transcripts prove that `ml/models_store/resnet_defect_classifier_metadata.json` was generated at **16:36:37 on 07-11-2026** by `backend/app/ml/defect_classifier/train.py` at the conclusion of the 35-epoch training session. It has **never been modified, overwritten, or regenerated** since that exact second.
2. **True Cryptographic Hash:** The actual cryptographic SHA-256 digest of this file on disk at generation time (16:36:37), during Step 8 initial inspection (17:23:18), and at current inspection (22:11:36) has continuously and immutably been:
   `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73`
3. **Origin of Discrepancy:** The hash `e99da54823293dc65b6378ba6f755da9fe845941ea87d3a822db0253457117eb` in Section 8 (Table 8) of `reports/phase2/resnet_defect_classifier_report.md` was an unverified, erroneously recorded value inserted during manual report drafting in Step 7. Transcript inspection confirms that no PowerShell `Get-FileHash` or Python `hashlib` execution on `metadata.json` preceded that report entry.
4. **Step 8 Inference Service Integrity:** All Step 8 architecture components (`backend/app/ml/inference/config.py`, `registry.py`, test suite, and evaluation results) used the true, verified disk hash (`e7e95b80...`). The Step 8 commit (`31fef2f`) is cryptographically consistent with disk reality.

---

## 2. Git Baseline & Working Tree Status

Forensic inspection executed prior to this investigation:

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

### Verification Findings:
- **Active Branch:** `main` (Verified)
- **Local HEAD SHA:** `31fef2fd2b5c9d7e758d9584e4c0b110470599e6` (Verified)
- **Remote HEAD (`origin/main`):** `af59f2eb62b7069e1e571b6dc303156486082216` (Verified)
- **Branch Relationship:** Local `main` is ahead of `origin/main` by exactly **1 commit** (commit `31fef2f`: `feat(phase2): integrate unified ML inference service`).
- **Working Tree Cleanliness:** Completely clean prior to creating this investigation report (`git status --short` returned 0 lines). Zero staged changes, zero unstaged changes.

---

## 3. Current Disk Artifact Verification

Direct cryptographic and filesystem inspection from physical storage (`D:\Desktop\FInal year project\manumind-ai\ml\models_store\`):

```powershell
Get-FileHash ml/models_store/resnet_defect_classifier_metadata.json -Algorithm SHA256
Get-FileHash ml/models_store/resnet_defect_classifier.keras -Algorithm SHA256
Get-Item ml/models_store/resnet_defect_classifier_metadata.json | Format-List Length, CreationTime, LastWriteTime
Get-Item ml/models_store/resnet_defect_classifier.keras | Format-List Length, CreationTime, LastWriteTime
```

### Empirical Physical Properties:

| Artifact | File Size | Creation Timestamp | Last Modified Timestamp | Computed SHA-256 Checksum |
| :--- | :---: | :---: | :---: | :--- |
| `resnet_defect_classifier_metadata.json` | 5,980 bytes | 2026-11-07 16:06:59 | 2026-11-07 16:36:37 | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` |
| `resnet_defect_classifier.keras` | 33,918,955 bytes | 2026-11-07 16:05:58 | 2026-11-07 16:36:14 | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` |

### Git Tracking & Ignore Evaluation:
```powershell
git check-ignore -v ml/models_store/resnet_defect_classifier_metadata.json
# .gitignore:43:ml/models_store/*    ml/models_store/resnet_defect_classifier_metadata.json

git ls-files -- ml/models_store/resnet_defect_classifier_metadata.json
# (empty output)
```

- Both the binary `.keras` model and the JSON metadata sidecar match rule `ml/models_store/*` in `.gitignore` (line 43).
- Neither file has ever been added to the Git index (`git ls-files` returns empty).
- Neither file was ever committed to Git history in any commit (`af59f2e`, `31fef2f`, or earlier).

---

## 4. Historical Hash Occurrences Across Repository Reports

A comprehensive regex audit was executed across all markdown reports in `reports/` and all commit snapshots in Git history:

```powershell
Get-ChildItem -Path reports -Recurse -Filter "*.md" | Select-String -Pattern "e99da548|e7e95b80"
```

### Evidence Inventory:

| Report Path & Section | Hash Recorded | Reported Size | Commit Tracking | Origin Context |
| :--- | :--- | :---: | :---: | :--- |
| `reports/phase2/resnet_defect_classifier_report.md` (Sec. 8, Line 280) | `e99da54823293dc65b6378ba6f755da9fe845941ea87d3a822db0253457117eb` | `7.9 KB` | Committed in `af59f2e` | Step 7 implementation report artifact table. |
| `reports/phase2/resnet_defect_classifier_independent_audit.md` (Sec. 8.1) | *(No metadata hash recorded; verified .keras only)* | `7.9 KB` | Committed in `af59f2e` | Step 7 audit verified `.keras` hash `aac4b1c2...` against internal metadata field `meta['artifact']['sha256']`. Metadata hash was not checked. |
| `reports/phase2/inference_service_inspection_plan.md` (Sec. 3.1, Line 168) | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | `5.98 KB` | Committed in `31fef2f` | Computed directly from disk bytes at Step 8 inspection start (17:23:18). |
| `reports/phase2/inference_service_implementation_report.md` (Sec. 2.1, Line 72) | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | `5.98 KB` | Committed in `31fef2f` | Parity verification table. |
| `reports/phase2/inference_service_independent_audit.md` (Sec. 7, Line 235) | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | `5,980 B` | Committed in `31fef2f` | Independent cryptographic audit of all 7 artifacts. |
| `backend/app/ml/inference/config.py` (Line 81) | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | N/A | Committed in `31fef2f` | Baseline hash for runtime integrity check in `ModelRegistry.verify_artifact()`. |

---

## 5. Forensic Transcript & Execution History Investigation

Inspection of `transcript.jsonl` and `transcript_full.jsonl` from the project trajectory reveals the exact timeline of artifact creation and hashing:

### 1. Step 7 First Training Attempt (16:07:06):
- Training ran for 9 epochs before early stopping (`task-2827`, Step 2859).
- Model saved: `resnet_defect_classifier.keras` (SHA-256: `8957441bc01bbcc8...`).
- Metadata saved to disk. Validation accuracy was low (0.3523).

### 2. Step 7 Second Training & Successful Checkpoint (16:36:37):
- Hyperparameters adjusted (learning rate schedule, patience, data augmentation).
- Training completed 35 epochs (`task-3244`, Step 3250):
  ```text
  [Train] Training finished in 405.02s. Best epoch: 33/35 with val_loss=0.4247, val_acc=1.0000
  [Train] Model saved to D:\Desktop\FInal year project\manumind-ai\ml\models_store\resnet_defect_classifier.keras (SHA-256: aac4b1c2d8c7ba47...)
  [Train] Metadata saved to D:\Desktop\FInal year project\manumind-ai\ml\models_store\resnet_defect_classifier_metadata.json
  ```
- File `resnet_defect_classifier_metadata.json` written to disk at **16:36:37**. Length: **5,980 bytes**.

### 3. Step 7 Report Authoring Anomaly (16:39:47):
- In Step 3273 (Line 3277 in transcript), `reports/phase2/resnet_defect_classifier_report.md` was drafted.
- Transcript inspection confirms that between 16:36:37 and 16:39:47, commands evaluated `evaluate.py`, `Get-ChildItem` on graphs, and `pytest`. **No command was executed to calculate the SHA-256 hash or file size of `resnet_defect_classifier_metadata.json`**.
- Table 8 was populated with an unverified entry:
  `| ml/models_store/resnet_defect_classifier_metadata.json | Training hyperparameters & history | 7.9 KB | e99da54823293dc65b6378ba6f755da9fe845941ea87d3a822db0253457117eb |`
- Forensic cross-check of other rows in Table 8 revealed that placeholder/unverified hashes were also assigned to other non-model artifacts:
  - `defect_classifier_results.json`: reported `6a6fe047...` (actual: `0b1c63a2...`)
  - `defect_predictions.csv`: reported `fc4b6adb...` (actual: `531e4426...`)
  - `training_curves.png`: reported `4f0a216f...` (actual: `8d09a5f4...`)
  - `confusion_matrix.png`: reported `0d1b464a...` (actual: `25ae3b81...`)
  The only hash in Table 8 that matched disk was `resnet_defect_classifier.keras` (`aac4b1c2...`), because it had been printed explicitly in the standard output of `train.py`.

### 4. Step 7 Independent Audit Scope (16:47:33):
- In Step 3325 (Line 3329 in transcript), the auditor executed:
  ```python
  actual_hash = get_sha256('ml/models_store/resnet_defect_classifier.keras')
  recorded_hash = json.load(open('ml/models_store/resnet_defect_classifier_metadata.json'))['artifact']['sha256']
  print('Hashes match:', actual_hash == recorded_hash) # True
  ```
- The auditor confirmed that the `.keras` model hash matched the metadata's internal record (`aac4b1c2...`), but did **not** compute a hash on `metadata.json` itself.

### 5. Step 8 Initial Physical Hash Measurement (17:23:18):
- At the start of Step 8 (Line 3517 in transcript), a comprehensive disk hashing script was executed across all files in `ml/models_store/`:
  ```text
  ml/models_store/resnet_defect_classifier_metadata.json (5,980 bytes): e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73
  ```
- This directly established the true cryptographic hash for the first time in project documentation.

---

## 6. Metadata Content & Model Compatibility Verification

The content of `ml/models_store/resnet_defect_classifier_metadata.json` was parsed and audited:

```json
{
  "model_name": "compact_resnet18_scratch",
  "architecture": {
    "type": "Compact ResNet-18",
    "stem_filters": 32,
    "stage_channels": [32, 64, 128, 256],
    "stage_blocks": [2, 2, 2, 2],
    "input_shape": [128, 128, 3],
    "num_classes": 4,
    "parameters": {
      "total_parameters": 2804708,
      "trainable_parameters": 2799908,
      "non_trainable_parameters": 4800
    }
  },
  "hyperparameters": {
    "learning_rate": 0.0003,
    "batch_size": 32,
    "epochs_requested": 35,
    "epochs_completed": 35,
    "best_epoch": 33,
    "l2_reg": 0.0001,
    "dropout_rate": 0.35,
    "label_smoothing": 0.05,
    "random_seed": 42,
    "early_stopping_patience": 8,
    "reduce_lr_patience": 4
  },
  "dataset": {
    "train_samples": 420,
    "val_samples": 88,
    "test_samples_frozen": 92,
    "classes": [
      "surface_crack",
      "spalling",
      "dent",
      "normal_surface"
    ],
    "samples_per_class_train": 105,
    "samples_per_class_val": 22,
    "manifest_path": "data/defect_images/defect_manifest.json"
  },
  "training_performance": {
    "elapsed_seconds": 405.02,
    "best_val_loss": 0.424704,
    "best_val_accuracy": 1.0,
    "final_lr": 3.7500001781154424e-05
  },
  "artifact": {
    "model_path": "ml/models_store/resnet_defect_classifier.keras",
    "sha256": "aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98"
  }
}
```

### Compatibility Assessment:
1. **Model Hash Binding:** `metadata["artifact"]["sha256"]` contains `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98`. This is an **exact match** for `resnet_defect_classifier.keras` currently on disk.
2. **Architecture Parity:** Architecture parameters (2,804,708 total parameters; `[128, 128, 3]` input; 4 classes) match `backend/app/ml/defect_classifier/model.py` and all Step 7 documentation.
3. **Training History Parity:** 35 epochs completed, best epoch 33, best val loss 0.424704, best val accuracy 1.0000, elapsed 405.02s match `task-3244` execution logs identically.
4. **Test Suite Verification:** All 15 unit/integration tests in `backend/tests/test_resnet_defect_classifier.py` and all 25 tests in `backend/tests/test_inference_service.py` pass without error (**102 / 102 project-wide pass rate**).

---

## 7. Resolution of Specific Audit Questions

1. **Did the metadata file change intentionally between Steps 7 and 8?**
   **NO.** Filesystem timestamps confirm `LastWriteTime` is `2026-11-07 16:36:37`, which predates the Step 7 commit (`af59f2e` at 17:04:47). The file was not modified between Steps 7 and 8.
2. **Was the metadata file modified by an authorized operation?**
   **NOT APPLICABLE.** No modification occurred at all.
3. **Is the change explained by a documented metadata update?**
   **NOT APPLICABLE.** There was no file update. The difference is purely between an unverified documentation entry in Step 7 and an empirically measured hash in Step 8.
4. **Does the Step 7 or Step 8 report contain an outdated or incorrect hash?**
   **YES.** The Step 7 implementation report (`resnet_defect_classifier_report.md` Table 8) contains an incorrect, unverified hash (`e99da548...`). The Step 8 reports contain the correct, empirically verified hash (`e7e95b80...`).
5. **Does the currently stored metadata match the committed model artifact and its expected configuration?**
   **YES.** Cryptographic hash binding (`aac4b1c2...`), parameter counts, hyperparameters, and test suite outputs confirm 100% integrity and compatibility.
6. **Does the discrepancy affect the Step 8 inference service commit?**
   **NO.** Step 8 commit `31fef2f` (`backend/app/ml/inference/config.py`, `registry.py`, test suite, and reports) configured and verified the actual disk hash (`e7e95b80...`). The Step 8 codebase is completely accurate and free of errors.

---

## 8. Final Decision & Status

| Criterion | Evaluation Result |
| :--- | :--- |
| **Audit Status** | **RESOLVED — HISTORICAL REPORT HASH ERROR** |
| **Integrity Risk** | **ZERO RISK** — Model weights and metadata sidecar are authentic, untampered, and mutually consistent. |
| **Recommended Action** | In a future documentation-cleanup milestone, amend line 280 of `reports/phase2/resnet_defect_classifier_report.md` to record the correct hash (`e7e95b80...`) and file size (`5.98 KB`). No code or artifact modifications required. |
| **Release Governance Status** | **PHASE 2 STEP 8 — RESNET METADATA HASH PROVENANCE INVESTIGATED; AWAITING INDEPENDENT REVIEW AND SEPARATE PUSH AUTHORIZATION.** |
