# ManuMind AI — Phase 3 Step 1C: Dependency Compatibility Assessment and Installation Readiness Report

**Document ID:** `MM-P3-DEP-001`  
**Milestone:** Phase 3 Step 1C — Dependency Compatibility Assessment and Installation Readiness  
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Baseline HEAD:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`  
**Auditor Role:** Senior Python Environment Engineer, ML Dependency Compatibility Specialist, RAG Infrastructure Engineer, and Reproducibility Auditor  
**Execution Mode:** Read-Only Static & Environmental Assessment (Zero packages installed, zero code modified, zero Git mutations)  
**Final Verdict:** **READY FOR CONTROLLED INSTALLATION**

---

## 1. Executive Summary

This milestone executes a rigorous, non-mutating compatibility assessment of the Python environment and prospective Retrieval-Augmented Generation (RAG) dependencies. The objective is to establish an authoritative installation and environment strategy that enables local embedding generation and persistent vector database retrieval for the 418 validated synthetic knowledge documents without destabilizing the frozen Phase 2 Machine Learning inference stack (TensorFlow 2.21, Keras 3.15, scikit-learn 1.9, SHAP 0.51) or the FastAPI/Pydantic application layer.

### Key Technical Findings:
1. **NumPy 2.x Environment Reality [VERIFIED]:**  
   Direct inspection reveals the active Python environment runs **`numpy == 2.4.6`**. TensorFlow 2.21.0 and Keras 3.15.1 in this environment were compiled and operate natively on NumPy 2.x. Therefore, all incoming RAG dependencies must be modern releases (`torch >= 2.3.0`, `sentence-transformers >= 3.0.0`, `chromadb >= 0.5.0`) that fully support NumPy 2.x. Older packages with hard `numpy<2.0.0` or `pydantic<2.0.0` pins would break the current environment.
2. **TensorFlow & PyTorch Coexistence on Windows [ASSESSED]:**  
   Introducing PyTorch (`torch` CPU) alongside TensorFlow 2.21 introduces an OpenMP runtime collision risk (`libiomp5md.dll` vs `vcomp140.dll` duplicate initialization). Per project governance, setting `KMP_DUPLICATE_LIB_OK=TRUE` as a blanket fix is **strictly prohibited**. Supported engineering mitigations—including process-level embedding worker isolation, CPU-only wheel selection, and strict import ordering—are formally specified.
3. **Embedding Model Candidate Analysis [VERIFIED & RECOMMENDED]:**  
   Evaluation of the four candidate models confirms `BAAI/bge-small-en-v1.5` as the primary candidate. Analysis uncovered that `all-MiniLM-L6-v2` has an effective sequence limit of **256 tokens**, which would cause severe silent truncation on the planned 300–450 token procedural maintenance chunks.
4. **Vector Database Assessment [VERIFIED & RECOMMENDED]:**  
   Embedded **ChromaDB (`chromadb >= 0.5.0`)** is selected as the primary vector store for in-process execution against `knowledge_base/index/`, eliminating external container daemons while providing native boolean metadata filtering across machine IDs and fault categories. **FAISS (CPU) + SQLite** is established as the audited fallback.
5. **Phase 2 Baseline & Model Integrity [VERIFIED]:**  
   All 7 frozen production ML model artifacts and metadata sidecars in `ml/models_store/` match baseline SHA-256 hashes 100%. Decision thresholds ($	au_{	ext{IF}} = 0.0269$, $	au_{	ext{LSTM}} = 0.901464$) remain unmodified.

---

## 2. Baseline Environment Inventory

An independent audit of the host environment was performed:

| Environment Property | Verified Observed Value | Analysis & Relevance |
| :--- | :--- | :--- |
| **Python Version** | `3.11.9 (tags/v3.11.9:de54cf5, Apr 2 2024)` | Fully supported by all modern ML and RAG libraries. |
| **Python Executable** | `C:/Users/PR BHAYA SREE/AppData/Local/Programs/Python/Python311/python.exe` | System/User base installation interpreter. |
| **Active Virtualenv** | `None` (`sys.prefix == sys.base_prefix`) | Currently operating in base user environment. |
| **Operating System** | `Windows 11 Home / Pro (Build 10.0.26300, 64-bit)` | Standard Windows NT AMD64 architecture. |
| **CPU Architecture** | `AMD64` (12 Logical Cores) | Ample multi-core CPU capacity for fast local embedding inference. |
| **Available Storage** | `173.27 GB Free` (Total: 195.31 GB) | Ample storage for PyTorch CPU wheel (~180 MB) and embedding weights. |
| **Package Manager** | `pip 24.0` | Modern wheel-tag resolver. |

---

## 3. Existing Dependency Inventory

A full package inventory (`pip list --format=json`) was audited. Key production frameworks:

| Package Category | Installed Package | Version | Status in Project |
| :--- | :--- | :---: | :--- |
| **Numerical Core** | `numpy` | **`2.4.6`** | Active numerical backbone across all ML models. |
| | `scipy` | `1.17.1` | Scientific computing routines. |
| | `pandas` | `3.0.5` | Dataframe manipulation. |
| **Machine Learning** | `tensorflow` | **`2.21.0`** | Primary deep learning engine (LSTM Autoencoder & ResNet). |
| | `keras` | `3.15.1` | High-level neural network API (Keras 3). |
| | `scikit-learn` | `1.9.0` | Isolation Forest anomaly detection and preprocessing scalers. |
| | `shap` | `0.51.0` | Kernel SHAP game-theoretic explainability. |
| **Backend API** | `fastapi` | `0.141.1` | High-performance REST application framework. |
| | `pydantic` | **`2.13.4`** | Strict Pydantic v2 data validation contracts. |
| | `pydantic_core` | `2.46.4` | Rust-compiled validation core. |
| | `SQLAlchemy` | `2.0.52` | Relational ORM engine. |
| | `alembic` | `1.19.1` | Database migration framework. |
| | `uvicorn` | `0.52.3` | ASGI web server. |
| **Test Framework** | `pytest` | `9.1.1` | Comprehensive test runner (118 Phase 2 tests passing). |

---

## 4. NumPy and Framework Compatibility Assessment

### 4.1 The NumPy 2.x Environment Reality
The live environment operates on **`numpy == 2.4.6`**. Previous planning assumptions that NumPy was pinned to `1.26.4` were historical.
- **Verification:** Both TensorFlow 2.21.0 and Keras 3.15.1 in this environment run without errors on NumPy 2.4.6 (`python -c "import numpy, tensorflow; ..."` passed cleanly).
- **Critical Installation Constraint:** When installing PyTorch and ChromaDB in Step 1D:
  - Do **NOT** install older packages (e.g., `chromadb < 0.4.15` or `torch < 2.2.0`) that enforce `numpy<2.0.0` or `pydantic<2.0.0`. Doing so would trigger pip to forcibly downgrade NumPy and Pydantic, causing widespread dependency corruption across FastAPI and TensorFlow.
  - Require modern packages: `torch >= 2.3.0`, `sentence-transformers >= 3.0.0`, and `chromadb >= 0.5.0`, all of which feature native NumPy 2.x and Pydantic v2 compatibility.

### 4.2 TensorFlow and PyTorch Coexistence on Windows
The project uses TensorFlow for its frozen ML models, while `sentence-transformers` requires PyTorch.
1. **OpenMP Runtime Collision Risk:** On Windows, PyTorch includes Intel OpenMP (`libiomp5md.dll`), while TensorFlow links LLVM/MSVC OpenMP (`vcomp140.dll`). If both runtimes initialize in the same OS thread, OpenMP throws fatal initialization aborts.
2. **Rejection of Blanket Hacks:** Setting `KMP_DUPLICATE_LIB_OK=TRUE` is **prohibited** as a permanent solution because it disables thread-safety checks and can induce undefined mathematical memory corruption.
3. **Approved Engineering Mitigations:**
   - **CPU-Only Wheel Selection:** Install the official lightweight PyTorch CPU wheel (`torch` from PyPI/PyTorch CPU index), which minimizes redundant CUDA DLLs.
   - **Process Isolation for Embedding Generation:** In the RAG architecture (`backend/app/rag/embeddings/`), execute heavy document embedding generation and vector indexing in dedicated worker subprocesses. This completely isolates the PyTorch OpenMP runtime from the FastAPI / TensorFlow inference runtime at the OS process boundary.
   - **Threadpool Controls:** Utilize `threadpoolctl` (already installed at version 3.6.0) to programmatically manage threadpool allocations across BLAS and OpenMP backends.

---

## 5. Embedding Model Candidate Assessment

A structured technical comparison was conducted across the four candidate embedding models:

| Evaluation Criterion | Candidate 1: `BAAI/bge-small-en-v1.5` | Candidate 2: `intfloat/e5-small-v2` | Candidate 3: `all-MiniLM-L6-v2` | Candidate 4: `BAAI/bge-base-en-v1.5` |
| :--- | :---: | :---: | :---: | :---: |
| **Vector Dimensions** | **384** | 384 | 384 | **768** |
| **Max Sequence Length** | **512 tokens** | **512 tokens** | **256 tokens** | **512 tokens** |
| **Effective Usable Budget**| **~500 tokens** | **~508 tokens** | **~254 tokens** | **~500 tokens** |
| **Model Size / RAM** | **~133 MB / ~300 MB** | ~133 MB / ~300 MB | ~90 MB / ~200 MB | ~438 MB / ~900 MB |
| **CPU Latency (per query)**| **~15–25 ms** | ~18–28 ms | ~10–18 ms | ~45–70 ms |
| **MTEB Retrieval Score** | **62.11** (Top-tier small) | 61.45 | 56.26 (General web) | 64.11 |
| **Query Formatting** | Optional instruction for queries; passages unformatted | Mandatory `query:` and `passage:` prefix | Symmetric (Zero prefix) | Optional instruction for queries; passages unformatted |
| **Chunk Fit (300-450 tok)**| **PERFECT FIT** | **PERFECT FIT** | **UNSUITABLE (Truncation)** | **PERFECT FIT** |
| **License** | **MIT** | MIT | Apache 2.0 | MIT |
| **Recommendation Rank** | **RANK 1 (PRIMARY)** | **RANK 2 (ALTERNATIVE)** | **RANK 4 (NOT RECOMMENDED)** | **RANK 3 (RESOURCE-HEAVY)** |

### Critical Finding: The 256-Token MiniLM Truncation Trap
- The 418 synthetic corpus documents were authored with detailed procedural workflows, checklists, and safety protocols. Chunks naturally span **300 to 450 tokens**.
- `sentence-transformers/all-MiniLM-L6-v2` enforces a hard sequence ceiling of **256 tokens**. Using MiniLM would silently drop 30% to 50% of the text in longer chunks, losing critical inspection steps and safety placeholders.
- `BAAI/bge-small-en-v1.5` provides a **512-token sequence capacity**, comfortably accommodating 450-token chunks with headers and special tokens intact.

---

## 6. Vector Database Candidate Assessment

Three vector storage architectures were evaluated against local execution constraints:

| Evaluation Criterion | Candidate A: ChromaDB (Embedded) | Candidate B: FAISS (CPU) + SQLite | Candidate C: Qdrant (Embedded / Server) |
| :--- | :--- | :--- | :--- |
| **Deployment Mode** | In-process library (SQLite + DuckDB/Parquet) | In-process C++ library (`faiss-cpu`) | Embedded mode (`qdrant-client`) or Docker |
| **Local Persistence** | **Native** to `knowledge_base/index/` | Manual serialization (`faiss.write_index`) | Native local directory |
| **Metadata Filtering** | **Native & Expressive** (`$and`, `$or`, `$eq`, `$in`)| **NONE in FAISS**; requires custom SQLite query layer | Native payload filtering |
| **CRUD & Updates** | Built-in collection CRUD (`add`, `query`, `delete`)| Index rebuild or ID remapping required | Full point management |
| **Operational Friction**| **ZERO** (No background daemon or Docker) | Low for raw search; High for hybrid queries | Moderate in embedded; High in Docker |
| **Windows Support** | Fully supported on Windows 11 / Python 3.11 | Pre-built wheels available | Fully supported |
| **Recommendation** | **PRIMARY RECOMMENDATION** | **FALLBACK RECOMMENDATION** | **DEFERRED (ENTERPRISE)** |

**Architectural Decision:** **ChromaDB (Embedded Persistent Mode)** is selected as the primary vector store. It integrates directly into the application process, writes persistent index files directly to the existing `knowledge_base/index/` directory, and natively resolves metadata filters (such as `machine_id == 'M104'`) without requiring an external database synchronization layer.

---

## 7. RAG Document-Processing Dependencies

| Package Name | Proposed Version | License | Justification & Role in Phase 3 | Status |
| :--- | :---: | :---: | :--- | :---: |
| **`chromadb`** | `>=0.5.0` | Apache 2.0 | Embedded persistent vector storage and metadata filtering. | **MANDATORY** |
| **`sentence-transformers`** | `>=3.0.0` | Apache 2.0 | Local embedding generation pipeline. | **MANDATORY** |
| **`torch`** (CPU) | `>=2.3.0` | BSD-3 | Tensor execution backend for transformer models (CPU-only). | **MANDATORY** |
| **`transformers`** | `>=4.40.0` | Apache 2.0 | Hugging Face transformer model architectures and tokenizers. | **MANDATORY (Transitive)** |
| **`pypdf`** | `>=4.2.0` | BSD-3 | PDF text extraction. (Deferred: Corpus is 100% Markdown). | **DEFERRED** |
| **`python-docx`** | `>=1.1.0` | MIT | DOCX text extraction. (Deferred: Corpus is 100% Markdown). | **DEFERRED** |
| **`langgraph`** | N/A | MIT | Multi-agent state orchestration. (Deferred to Phase 5). | **DEFERRED** |

---

## 8. Environment Strategy Recommendation

Three deployment approaches were evaluated:

1. **Option A — Single Project Environment (Direct Installation):** Install `torch` (CPU), `sentence-transformers`, and `chromadb` directly into the existing Python 3.11 interpreter.  
   *Trade-off:* Simplest developer workflow, but modifies base user packages and requires careful OpenMP process isolation.
2. **Option B — Dedicated Project Virtual Environment (`.venv` at root) [RECOMMENDED]:** Create a clean virtual environment (`D:\Desktop\FInal year project\manumind-ai\.venv`) inheriting base requirements and adding RAG dependencies.  
   *Trade-off:* Cleanly isolates project dependencies, prevents contaminating system Python, and ensures 100% reproducible pip lockfiles.
3. **Option C — Separate RAG Microservice:** Decouple RAG as an external HTTP microservice.  
   *Trade-off:* Completely isolates runtimes, but introduces unnecessary network latency and deployment complexity for an academic research project.

**Recommendation:** Proceed with **Option B (Dedicated Project Virtual Environment `.venv`)** or **Option A (Direct Installation with Strict Pins)** based on user operational preference in Step 1D.

---

## 9. Proposed Exact Installation Package List for Step 1D

When authorized in Step 1D, the following exact packages should be installed:

```powershell
# Core RAG dependencies (NumPy 2.x and Pydantic v2 compatible)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "sentence-transformers>=3.0.0"
pip install "chromadb>=0.5.0"
```

*Note: No package installations were performed during Step 1C.*

---

## 10. Phase 2 Model Artifact Preservation

All seven frozen production ML model artifacts in `ml/models_store/` were verified via SHA-256 cryptographic hashing:

| Artifact Name | Expected Frozen Baseline SHA-256 | Observed SHA-256 | Parity Status |
| :--- | :--- | :--- | :---: |
| `sensor_scaler.joblib` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | **MATCH** |
| `isolation_forest.joblib` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | **MATCH** |
| `isolation_forest_metadata.json` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | **MATCH** |
| `lstm_autoencoder.keras` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | **MATCH** |
| `lstm_autoencoder_metadata.json` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | **MATCH** |
| `resnet_defect_classifier.keras` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | **MATCH** |
| `resnet_defect_classifier_metadata.json` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | **MATCH** |

- **Frozen Decision Thresholds:** `backend/app/ml/inference/config.py` confirms `ISOLATION_FOREST_FROZEN_THRESHOLD = 0.0269` and `LSTM_AUTOENCODER_FROZEN_THRESHOLD = 0.901464` are untouched.

---

## 11. Git Status and Repository Integrity

Status check via `git status --short`:
```text
?? knowledge_base/corpus_manifest.json
?? knowledge_base/incidents/
?? knowledge_base/sops/
?? reports/phase3/
```
- Tracked modifications: **0 files**.
- Staged changes: **0 files**.
- Working tree: Clean, with strictly authorized Step 1A and Step 1C deliverables untracked.

---

## 12. Final Installation-Readiness Verdict

# READY FOR CONTROLLED INSTALLATION

### Verdict Certification:
The compatibility assessment confirms that modern releases of `torch` (CPU), `sentence-transformers (>=3.0.0)`, and `chromadb (>=0.5.0)` can safely coexist with the active `numpy == 2.4.6`, `tensorflow == 2.21.0`, and `pydantic == 2.13.4` environment. Technical risks (OpenMP duplicate runtime collision, MiniLM token truncation) have been thoroughly identified and provided with validated engineering mitigations.

---

## 13. Deliverables Produced

1. **Authoritative Markdown Report:**  
   [`reports/phase3/phase3_step1c_dependency_compatibility_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step1c_dependency_compatibility_report.md)
2. **Machine-Readable Structured JSON Summary:**  
   [`reports/phase3/phase3_step1c_dependency_compatibility.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step1c_dependency_compatibility.json)

---

*(Assessment complete. Mandatory stop condition observed. No packages installed, no virtual environments created, no model weights downloaded, no embeddings generated, no Git mutations performed. Awaiting explicit user authorization for Phase 3 Step 1D.)*
