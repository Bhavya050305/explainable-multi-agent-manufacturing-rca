# ManuMind AI — Phase 3 Step 1D: Controlled Dependency Installation and Environment Smoke Testing Report

**Milestone:** Phase 3 Step 1D — Controlled Dependency Installation and Environment Smoke Testing  
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** [`D:/Desktop/FInal year project/manumind-ai`](file:///D:/Desktop/FInal%20year%20project/manumind-ai)  
**Branch:** `main` | **HEAD:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`  
**Role:** Senior Python Environment Engineer, Windows ML Runtime Specialist, Dependency Reproducibility Auditor, and Independent Verification Engineer  
**Execution Date:** 2026-11-09  
**Execution Status:** **STEP 1D INCOMPLETE (Subprocess IPC Test Inconclusive)**

---

## 1. Executive Summary & Verdict

### Final Milestone Verdict:
# `FAIL — STEP 1D INCOMPLETE`

### Verdict Justification:
1. **Isolated Virtual Environment Created Successfully:** `.venv-rag` was initialized with strict isolation (`include-system-site-packages = false`) and Git ignore protection (`.venv-rag/` added to [`.gitignore`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/.gitignore) line 10).
2. **Controlled Installation Succeeded:** The reconciled candidate set (`torch==2.5.1+cpu`, `sentence-transformers==3.4.1`, `transformers==4.46.3`, `tokenizers==0.20.3`, `chromadb==0.5.23`, `pydantic-settings==2.7.1`) was installed into `.venv-rag`. `pip check` confirmed **zero broken requirements**.
3. **Core Smoke Tests Passed:**
   - **Stage 1 (Base Environment):** TensorFlow 2.21, Keras 3.15.1, scikit-learn 1.9.0, SHAP 0.51.0, and ResNet defect model forward pass (`128x128x3`) passed without errors.
   - **Stage 2 (RAG Environment):** PyTorch 2.5.1 CPU, NumPy 2.4.6 interoperability (`torch.from_numpy`, `tensor.numpy`), Sentence Transformers offline imports, and ChromaDB persistence + `$and` metadata filtering passed.
4. **Stage 3 Subprocess IPC Test HUNG / INCONCLUSIVE:** During Stage 3, the test script attempting to spawn a child process running PyTorch in `.venv-rag` from a parent process with TensorFlow hung indefinitely on anonymous pipe / event loop communication. In strict accordance with user governance instructions, the hanging process was terminated, zero completed iterations were recorded, and the test is formally classified as **INCONCLUSIVE**.
5. **Phase 2 Invariance Preserved:** All 7 frozen ML model artifacts match baseline SHA-256 hashes 100%. Both thresholds ($\\tau_{\\text{IF}} = 0.0269$, $\\tau_{\\text{LSTM}} = 0.901464$) remain strictly intact. Base environment packages are 100% unchanged.

---

## 2. Environment Creation & Ignore Protection Evidence

### 2.1 Git Ignore Protection Verification
- File: [`.gitignore`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/.gitignore)
- Change: Added exact entry `.venv-rag/` on line 10 immediately following `.venv/`.
- Verification command:
  ```powershell
  git check-ignore -v .venv-rag/
  # Output: .gitignore:10:.venv-rag/    .venv-rag/ (Exit code 0)
  ```
- Result: Zero untracked `.venv-rag/` files detected in `git status`.

### 2.2 Environment Configuration Audit
- **Executable:** `D:/Desktop/FInal year project/manumind-ai/.venv-rag/Scripts/python.exe`
- **Prefix (`sys.prefix`):** `D:/Desktop/FInal year project/manumind-ai/.venv-rag`
- **Base Prefix (`sys.base_prefix`):** `C:/Users/PR BHAYA SREE/AppData/Local/Programs/Python/Python311`
- **`include-system-site-packages`:** `false` (in `pyvenv.cfg`)
- **Isolation Check:** Attempting to import `tensorflow`, `shap`, `keras`, `sklearn` in fresh `.venv-rag` all raised `ImportError` (Strictly clean).

---

## 3. Dependency Resolver Evidence & Installation Audit

### 3.1 Resolver Simulation & Conflict Resolution
During initial pre-installation resolution of the approved candidates, `chromadb==0.5.23` conflicted with `transformers==4.48.3` and `tokenizers==0.21.0` due to ChromaDB's hard constraint `tokenizers<=0.20.3`.  
Upon explicit user authorization, the reconciled version set was simulated via `pip install --dry-run --report`:
- **`tokenizers`:** `0.20.3` (Pre-built Windows `cp311-none-win_amd64.whl`)
- **`transformers`:** `4.46.3` (Universal pure Python wheel)
- **`torch`:** `2.5.1+cpu` (Official PyTorch CPU wheel from `https://download.pytorch.org/whl/cpu`)
- **`sentence-transformers`:** `3.4.1`
- **`chromadb`:** `0.5.23`
- **`pydantic-settings`:** `2.7.1`
- **`numpy`:** `2.4.6`
- **Result:** Exit code 0, 104 packages resolved, zero CUDA/torchvision/torchaudio dependencies.

### 3.2 Installation Execution & Integrity Check
Installation into `.venv-rag` executed successfully:
```powershell
& ".\.venv-rag\Scripts\python.exe" -m pip check
# Output: No broken requirements found. (Exit code 0)
```
- **Reproducibility Lockfile Created:** [`backend/requirements-rag.lock`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/requirements-rag.lock) (108 lines, UTF-8 clean, generated from `pip freeze`).
- **Excluded Packages Confirmed:** `torchvision` (ABSENT), `torchaudio` (ABSENT), `langgraph` (ABSENT), `faiss` (ABSENT), `qdrant` (ABSENT).

---

## 4. Runtime Smoke Test Evidence

### 4.1 Stage 1: Base Environment Verification
- **Interpreter:** Base user Python 3.11.9 (`C:/Users/PR BHAYA SREE/AppData/Local/Programs/Python/Python311/python.exe`)
- **Packages Verified:** `numpy == 2.4.6`, `tensorflow == 2.21.0`, `keras == 3.15.1`, `scikit-learn == 1.9.0`, `shap == 0.51.0`.
- **ResNet Defect Model Loading:** Loaded [`ml/models_store/resnet_defect_classifier.keras`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/resnet_defect_classifier.keras) successfully.
- **Forward Pass Smoke Test:** Executed on dummy tensor with input contract `(1, 128, 128, 3)`.  
  Output shape: `(1, 4)`. Prediction: `[[0.0072, 0.0112, 0.8485, 0.1330]]`.
- **Verdict:** **PASSED**.

### 4.2 Stage 2: RAG Worker Environment Verification
- **Interpreter:** `.venv-rag\Scripts\python.exe`
- **PyTorch Verification:** Version `2.5.1+cpu`, `cuda.is_available() == False`. CPU tensor addition `[1,2,3] + [4,5,6] = [5,7,9]` verified.
- **NumPy 2.4.6 Interoperability:**
  - `torch.from_numpy(arr)`: Verified.
  - `tensor.numpy()`: Verified.
  - Numerical equality check (`np.allclose`): Verified.
- **Transformers & Tokenizers:** Verified `transformers == 4.46.3`, `tokenizers == 0.20.3`. Offline tokenizer classes import cleanly. No model weights downloaded.
- **ChromaDB Persistence & Query:**
  - Initialized `PersistentClient` in `scratch/chroma_smoke_test`.
  - Added 3 records with metadata (`machine_id`, `fault_category`, `doc_type`).
  - Executed query with `$and` filter: `{"$and": [{"machine_id": "M101"}, {"fault_category": "BEARING_FAILURE"}]}`.
  - Returned record: `doc_001` with distance `0.0`.
  - Reopened client from persistent directory: verified count = 3 and record retrieval.
  - Cleaned up scratch directory.
- **Verdict:** **PASSED**.

### 4.3 Stage 3: Subprocess IPC and OpenMP Isolation Test (INCIDENT AUDIT)
- **Architecture:** Base process (TensorFlow 2.21) spawning child process (`.venv-rag\Scripts\python.exe` running PyTorch) communicating via stdin/stdout JSON.
- **Observation:**
  - Base process initialized TensorFlow successfully.
  - Child process was invoked via `asyncio.create_subprocess_exec`.
  - Test entered an indefinite wait state with 0% CPU and 0% disk activity.
  - Stderr log showed TensorFlow initialization logs, but the child process banner (`[CHILD] Initializing PyTorch child worker...`) never appeared in stderr.
  - Completed iterations: **0 of 3**.
- **Root Cause Diagnosis:**
  - On Windows, asynchronous subprocess pipe handling (`asyncio.ProactorEventLoop` with standard I/O redirection) can block indefinitely if standard handles are constrained by sandbox process containment or if anonymous pipe synchronization encounters deadlocks before child script execution begins.
- **Corrective Action Taken:**
  - Following explicit user instructions, the hung test task (`task-5563`) was cancelled and gracefully terminated.
  - No residual zombie processes remain.
  - No OpenMP workarounds (`KMP_DUPLICATE_LIB_OK=TRUE`) were introduced.
- **Verdict:** **INCONCLUSIVE / BLOCKED**.

---

## 5. Phase 2 Baseline Invariance Audit

All 7 production ML model artifacts and metadata sidecars in [`ml/models_store/`](file:///D:/Desktop/FInal year project/manumind-ai/ml/models_store/) were audited via SHA-256:

| Artifact File | Verified SHA-256 Hash | Baseline Verification |
| :--- | :--- | :---: |
| `sensor_scaler.joblib` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | **100% MATCH** |
| `isolation_forest.joblib` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | **100% MATCH** |
| `isolation_forest_metadata.json` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | **100% MATCH** |
| `lstm_autoencoder.keras` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | **100% MATCH** |
| `lstm_autoencoder_metadata.json` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | **100% MATCH** |
| `resnet_defect_classifier.keras` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | **100% MATCH** |
| `resnet_defect_classifier_metadata.json` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | **100% MATCH** |

- **Frozen Production Thresholds:**
  - $\\tau_{\\text{IF}} = 0.0269$ (Verified intact)
  - $\\tau_{\\text{LSTM}} = 0.901464$ (Verified intact)

---

## 6. Git Invariance & Deliverables

### 6.1 Git Status
- **HEAD Commit:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`
- **Branch:** `main` (Synchronized with `origin/main`: `0 0`)
- **Tracked Modifications:** Exactly 1 tracked modification:
  - `M .gitignore` (line 10: `.venv-rag/` addition, authorized by user)
- **Untracked Deliverables:**
  - `backend/requirements-rag.lock` (Lockfile for `.venv-rag`)
  - `knowledge_base/corpus_manifest.json` (Phase 3 Step 1A)
  - `knowledge_base/incidents/`
  - `knowledge_base/sops/`
  - `reports/phase3/`
- Zero `.venv-rag` binaries or virtual environment files are untracked or staged.
- Zero Git staging, commits, or pushes were performed.

### 6.2 Deliverables Produced
1. **Markdown Audit Report:**  
   [`reports/phase3/phase3_step1d_dependency_installation_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step1d_dependency_installation_report.md)
2. **Machine-Readable JSON Evidence:**  
   [`reports/phase3/phase3_step1d_dependency_installation.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step1d_dependency_installation.json)

---

## 7. Mandatory Stop Condition

**Installation and audit sequence concluded. Mandatory stop condition observed.**
- The base environment remains 100% untouched.
- All 7 Phase 2 model artifacts match baseline hashes 100%.
- Both thresholds remain untouched.
- The hung Stage 3 IPC test has been terminated and recorded as `INCONCLUSIVE`.
- In strict adherence to governance instructions, the verdict is recorded as **`FAIL — STEP 1D INCOMPLETE`** pending review and correction of the subprocess IPC execution harness.
- Awaiting user instruction before any further action. Progression to Phase 3 Step 2 is **strictly blocked**.
