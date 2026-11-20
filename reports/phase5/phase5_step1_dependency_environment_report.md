# ManuMind AI — Phase 5 Step 1: LangGraph Dependency and Environment Preparation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Baseline HEAD Commit:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`  
**Milestone:** Phase 5 Step 1 — LangGraph Dependency and Environment Preparation  
**Timestamp:** 2026-11-17T17:30:00+05:30  
**Overall Verdict:** `BLOCKED` (Mandatory Stop Gate Triggered During Dry Run)

---

## 1. Executive Summary

In accordance with Phase 5 Step 1 specifications, environment preparation was initiated to install the multi-agent orchestration layer into Base Python 3.11.9.

The target requirements file `backend/requirements-phase5.txt` was created containing the exact pinned dependencies specified in the Step 0.1 solution architecture:
- `langgraph==0.2.45`
- `langchain-core==0.3.15`
- `langchain==0.3.7`

Per Section 4 governance rules, a mandatory dependency resolution dry run was executed using the explicit Base Python interpreter (`C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe`):
```powershell
python -m pip install --dry-run --report phase5_step1_pip_dry_run.json -r backend/requirements-phase5.txt
```

### Critical Stop Gate Finding
Inspection of the resulting dependency resolution graph (`phase5_step1_pip_dry_run.json`) revealed a **critical dependency conflict between the legacy `langchain==0.3.7` package and the protected machine learning environment**:
1. `langchain==0.3.7` declares an explicit constraint `numpy<2,>=1` for Python versions below 3.12.
2. In Base Python 3.11.9, `numpy==2.4.6` is installed to support:
   - Protected package `shap==0.51.0` (which requires `numpy>=2`).
   - `ml_dtypes==0.6.0`, the core tensor typing subdependency of protected package `tensorflow==2.21.0` (which requires `numpy>=2.0.0`).
3. Pip's resolver proposed downloading and installing `numpy==1.26.4`.
4. If `numpy` is downgraded to 1.26.4:
   - Protected package `shap==0.51.0` dependency requirement is violated.
   - `tensorflow==2.21.0` tensor type library (`ml_dtypes`) is broken.
   - `pip check` fails with exit code 1 (`shap 0.51.0 has requirement numpy>=2; ml_dtypes 0.6.0 has requirement numpy>=2.0.0`).
5. If pip resolves against the whole environment including `shap`, it resolves the conflict by **downgrading protected package `shap` from `0.51.0` to `0.49.1`**, directly violating the invariant: *"STOP without installing anything if SQLAlchemy, Alembic, FastAPI, TensorFlow, scikit-learn or SHAP would be changed unexpectedly."*

### Stop Gate Action Taken
In strict adherence to the mandate:
> *"STOP without installing anything if any protected package would be unexpectedly upgraded or downgraded... If a conflict occurs, document it and recommend a safe alternative. Do not silently change the selected versions."*

**The installation was immediately halted.** Zero packages were installed, upgraded, or downgraded. Both the Base Python environment and the `.venv-rag` environment remain 100% clean and intact.

---

## 2. Git and Repository Preflight State

The repository state was audited prior to and after dry-run execution:

| Parameter | Value / State | Status |
| :--- | :--- | :---: |
| **Repository Root** | `D:\Desktop\FInal year project\manumind-ai` | Verified |
| **Active Branch** | `main` | Verified |
| **Current HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Verified |
| **Remote Tracking** | `origin/main` (ahead 0, behind 0) | Synchronized |
| **Tracked Changes** | `backend/app/models/__init__.py` (preserved Phase 4 import) | Preserved |
| **Untracked Artifacts** | Phase 4 MCP server files, tests, reports, and Step 1 dry-run files | Preserved |
| **Created Step 1 File** | `backend/requirements-phase5.txt` | Created |

### Working Tree Verification (`git status --short`)
```text
 M backend/app/models/__init__.py
?? backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py
?? backend/app/mcp_server/
?? backend/app/ml/defect_runner.py
?? backend/app/models/ticket_proposal.py
?? backend/app/rag/bridge_runner.py
?? backend/requirements-mcp.txt
?? backend/requirements-phase5.txt
?? backend/tests/test_mcp_defect_image.py
?? backend/tests/test_mcp_maintenance_history.py
?? backend/tests/test_mcp_manufacturing_tools.py
?? backend/tests/test_mcp_rag_retrieval.py
?? backend/tests/test_mcp_server_skeleton.py
?? backend/tests/test_mcp_ticket_creation.py
?? phase5_step1_pip_dry_run.json
?? reports/phase4/
?? reports/phase5/
```

---

## 3. Host Environment Preflight Audit

### 3.1 Base Python 3.11.9 Environment
- **Interpreter Path:** `C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe`
- **Python Version:** 3.11.9 (64-bit Windows)
- **Preflight `pip check`:** Clean (`No broken requirements found.`)

#### Protected Packages Baseline
| Package | Baseline Version | Invariant Constraint | Coexistence Status |
| :--- | :---: | :--- | :---: |
| `pydantic` | `2.13.4` | Must remain V2 (`>=2.7.4`) | Fully Compatible |
| `pydantic-core` | `2.46.4` | Must match Pydantic | Fully Compatible |
| `mcp` | `2.3.0` | MCP Server SDK | Fully Compatible |
| `sqlalchemy` | `2.0.52` | Manufacturing ORM | Fully Compatible |
| `alembic` | `1.19.1` | Migration engine | Fully Compatible |
| `fastapi` | `0.141.1` | REST Gateway | Fully Compatible |
| `tensorflow` | `2.21.0` | ML Anomaly detection | Requires `numpy>=1.26.0`, `ml_dtypes>=0.6.0` |
| `scikit-learn` | `1.9.0` | ML Preprocessing | Requires `numpy>=1.24.1` |
| `shap` | `0.51.0` | Explainability engine | **Requires `numpy>=2.0.0`** |
| `ml_dtypes` | `0.6.0` | TensorFlow float types | **Requires `numpy>=2.0.0`** |
| `numpy` | `2.4.6` | Scientific computing | Current baseline |
| `anyio` | `4.14.2` | Async event loop | Fully Compatible |
| `httpx` | `0.28.1` | HTTP client | Fully Compatible |

### 3.2 RAG Isolated Environment (`.venv-rag`)
- **Interpreter Path:** `D:\Desktop\FInal year project\manumind-ai\.venv-rag\Scripts\python.exe`
- **Lockfile:** `backend/requirements-rag.lock`
- **Lockfile SHA-256:** `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` (Exact match)
- **ChromaDB Path:** `D:\Desktop\FInal year project\manumind-ai\knowledge_base\index\chroma_bge_small_v1`
- **Collection Name:** `manumind_bge_small_v1`
- **Total Vectors:** 564 embeddings (dimension 384, cosine distance)
- **Isolation Status:** Untouched; zero writes, zero modifications.

---

## 4. Mandatory Dependency Resolution Dry-Run Analysis

### 4.1 Target Specification (`backend/requirements-phase5.txt`)
```text
langgraph==0.2.45
langchain-core==0.3.15
langchain==0.3.7
```

### 4.2 Dry-Run Resolution Output
Command executed:
```powershell
& "C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe" -m pip install --dry-run --report phase5_step1_pip_dry_run.json -r backend/requirements-phase5.txt
```

Pip resolved 20 packages for installation:
1. `langgraph`: 0.2.45
2. `langchain-core`: 0.3.15
3. `langchain`: 0.3.7
4. `aiohappyeyeballs`: 2.7.1
5. `aiohttp`: 3.14.5
6. `aiosignal`: 1.4.0
7. `frozenlist`: 1.8.0
8. `jsonpatch`: 1.47
9. `jsonpointer`: 3.12
10. `langchain-text-splitters`: 0.3.2
11. `langgraph-checkpoint`: 2.1.2
12. `langgraph-sdk`: 0.1.74
13. `langsmith`: 0.1.147
14. **`numpy`: 1.26.4 (PROPOSED DOWNGRADE)**
15. `orjson`: 3.13.0
16. `ormsgpack`: 1.13.1
17. `packaging`: 24.2
18. `requests-toolbelt`: 1.0.0
19. `tenacity`: 9.2.1
20. `yarl`: 1.25.1

### 4.3 Root Cause Analysis of the Dependency Conflict

```
                      +-----------------------------+
                      |   langchain == 0.3.7        |
                      |   requires numpy < 2        |
                      +--------------+--------------+
                                     |
                                     v
                       [ Downgrades numpy to 1.26.4 ]
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
+----------------------------+                 +----------------------------+
|        shap == 0.51.0      |                 |     ml_dtypes == 0.6.0     |
|     requires numpy >= 2    |                 |   requires numpy >= 2.0.0  |
|          [BROKEN]          |                 |   (tensorflow subdependency)
+----------------------------+                 |          [BROKEN]          |
                                               +----------------------------+
```

1. **Origin of the Constraint:** `langchain==0.3.7` wheel metadata declares:
   `numpy (>=1,<2) ; python_version < "3.12"`
2. **Origin of NumPy 2.x in Base Python:** Base Python uses `numpy==2.4.6` because modern releases of `shap` (`0.51.0`) and TensorFlow's tensor-type engine `ml_dtypes` (`0.6.0`) are compiled against NumPy 2.0 C-API ABI and require `numpy>=2.0.0`.
3. **Collision Impact:**
   - If `numpy` is downgraded to `1.26.4`, `pip check` fails immediately with two broken requirements:
     - `shap 0.51.0 has requirement numpy>=2, but you have numpy 1.26.4.`
     - `ml_dtypes 0.6.0 has requirement numpy>=2.0.0, but you have numpy 1.26.4.`
   - If `shap` is included in resolution, pip resolves the conflict by **downgrading `shap` from 0.51.0 to 0.49.1**, mutating the protected machine learning environment.

---

## 5. Evaluation Against Mandatory Stop Gate Criteria

The Phase 5 Step 1 specification defines six explicit stop-gate conditions:

| Stop Gate Condition | Condition Evaluated | Stop Triggered? | Evidence / Findings |
| :--- | :---: | :---: | :--- |
| **1. Protected package upgraded/downgraded** | Yes | **YES** | Installing requires downgrading `shap` to 0.49.1 or breaking `shap 0.51.0`. |
| **2. Pydantic V2 compatibility broken** | Yes | No | `pydantic==2.13.4` is preserved across all dependencies. |
| **3. MCP SDK compatibility uncertain** | Yes | No | `mcp==2.3.0` dependencies (`pydantic`, `anyio`) are satisfied. |
| **4. ML packages changed unexpectedly** | Yes | **YES** | `tensorflow==2.21.0` subdependency `ml_dtypes==0.6.0` and `shap` conflict with `numpy<2`. |
| **5. Dependency resolution conflict** | Yes | **YES** | Direct conflict: `langchain==0.3.7` (`numpy<2`) vs `shap==0.51.0` (`numpy>=2`). |
| **6. Installation affects `.venv-rag`** | Yes | No | `.venv-rag` remains strictly isolated. |

**Verdict:** The stop gate was triggered under Conditions 1, 4, and 5. The installation was safely halted prior to executing `pip install`.

---

## 6. Technical Analysis & Recommended Solution Architecture

### 6.1 Architectural Reality: ManuMind AI Does Not Need the Monolithic `langchain` Package
In modern multi-agent systems, LangGraph (`langgraph==0.2.45`) is the orchestration runtime.
- **Workflow Engine:** `from langgraph.graph import StateGraph, START, END` (lives in `langgraph`).
- **State Management:** `from langchain_core.messages import BaseMessage, ToolMessage` and Pydantic models (lives in `langchain_core`).
- **Tool Execution:** ManuMind AI connects to tools via the dedicated in-process MCP Server (`mcp.server.fastmcp`).
- **RAG Execution:** RAG retrieval is delegated to `.venv-rag` via the subprocess bridge runner (`backend/app/rag/bridge_runner.py`).

The monolithic `langchain` package contains legacy agent abstractions, chains, and document loaders that **ManuMind AI does not use**. Neither `langgraph==0.2.45` nor `langchain-core==0.3.15` depends on `numpy`.

### 6.2 Comparison of Solution Alternatives

```carousel
### Alternative 1: Exclude monolithic `langchain` (RECOMMENDED)
<!-- slide -->
**Action:** Modify `backend/requirements-phase5.txt` to:
```text
langgraph==0.2.45
langchain-core==0.3.15
```
**Pros:**
- 100% clean installation; zero package downgrades.
- `numpy==2.4.6`, `shap==0.51.0`, and `tensorflow==2.21.0` remain untouched.
- `pip check` remains completely clean.
- Provides all required primitives (`StateGraph`, `START`, `END`, `Command`, `Send`).
**Cons:**
- Omits the monolithic `langchain` package (which is unused anyway).
<!-- slide -->
### Alternative 2: Upgrade LangChain to 0.3.20+ and LangChain Core to 0.3.41
<!-- slide -->
**Action:** Update `backend/requirements-phase5.txt` to:
```text
langgraph==0.2.45
langchain-core==0.3.41
langchain==0.3.20
```
**Pros:**
- In version 0.3.20+, LangChain removed the `numpy<2` constraint entirely, making it compatible with NumPy 2.x.
- Retains the monolithic `langchain` package if future code needs it.
**Cons:**
- Requires upgrading `langchain-core` beyond `0.3.15` to `0.3.41`.
<!-- slide -->
### Alternative 3: Downgrade Host ML Stack to NumPy 1.x
<!-- slide -->
**Action:** Downgrade `numpy` to `1.26.4`, `shap` to `0.49.1`, and `ml_dtypes` to `<0.6.0`.
**Pros:**
- Permits exact pinned version `langchain==0.3.7`.
**Cons:**
- High regression risk. Mutates core ML dependencies and breaks Phase 4 non-regression guarantee.
- **REJECTED.**
```

---

## 7. RAG Environment and ChromaDB Integrity Verification

The RAG isolated virtual environment was audited to confirm zero contamination from the Step 1 preflight and dry-run operations:

| Verification Target | Expected Value | Actual Value | Invariant Status |
| :--- | :--- | :--- | :---: |
| **RAG Lockfile** | `backend/requirements-rag.lock` | Present | Preserved |
| **Lockfile SHA-256** | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | **VERIFIED (EXACT MATCH)** |
| **ChromaDB Path** | `knowledge_base/index/chroma_bge_small_v1` | Present | Preserved |
| **Collection Name** | `manumind_bge_small_v1` | `manumind_bge_small_v1` | **VERIFIED** |
| **Vector Count** | 564 embeddings | 564 embeddings | **VERIFIED (EXACT MATCH)** |
| **Embedding Dim** | 384 dimensions | 384 dimensions | **VERIFIED** |
| **RAG Pip Check** | `No broken requirements found.` | `No broken requirements found.` | **VERIFIED CLEAN** |

---

## 8. Summary of Executed Commands and Verifications

| Check / Operation | Execution Mode | Result | Notes |
| :--- | :---: | :---: | :--- |
| **Git Status Audit** | Sandboxed | Clean | Only expected untracked files present |
| **Base Python `pip check` Preflight** | Sandboxed | Clean | `No broken requirements found.` |
| **Pip Dry Run Resolution** | BypassSandbox (PyPI metadata) | Completed (code 0) | Generated `phase5_step1_pip_dry_run.json` |
| **Conflict Analysis Script** | Sandboxed | Completed (code 0) | Identified `langchain 0.3.7` vs `shap/ml_dtypes` |
| **RAG Lockfile SHA-256** | Sandboxed | Completed (code 0) | Hash verified identical to baseline |
| **ChromaDB Collection Query** | Sandboxed | Completed (code 0) | 564 embeddings verified via `.venv-rag` |
| **Host Environment Protection** | Sandboxed | Preserved | Zero packages installed; zero state mutated |

---

## 9. Final Milestone Verdict

### Milestone Verdict: `BLOCKED`

**Justification:**
1. In strict compliance with the Phase 5 Step 1 Stop Gate rules, installation of the requested pinned versions (`langgraph==0.2.45`, `langchain-core==0.3.15`, `langchain==0.3.7`) was halted because `langchain==0.3.7` produces an unresolvable dependency conflict with protected packages `shap==0.51.0` and `tensorflow==2.21.0` (`ml_dtypes==0.6.0`) via its legacy `numpy<2` constraint.
2. Rather than silently modifying the package specifications or mutating the protected ML stack, this condition is documented with clear, validated alternatives.
3. Upon receiving user authorization to proceed with **Alternative 1** (installing `langgraph==0.2.45` and `langchain-core==0.3.15`, omitting the unused monolithic `langchain`), installation can proceed safely with zero conflict and 100% clean `pip check`.
