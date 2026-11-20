# ManuMind AI — Phase 4 Step 3.1: Independent RAG MCP Bridge and Retrieval Closure Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Target Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`  
**Remote Origin:** `https://github.com/Bhavya050305/explainable-multi-agent-manufacturing-rca.git`  
**Synchronization Status:** Synchronized (`ahead 0, behind 0`)  
**Audit Target:** Phase 4 Step 3 — `search_manuals` Read-Only RAG Retrieval MCP Tool  
**Audit Type:** Strictly Independent, Read-Only Verification  
**Execution Timestamp:** 2026-11-15T18:26:00+05:30  
**Final Verdict:** **`APPROVED FOR STEP 4`**

---

## 1. Audit Scope and Methodology

This audit is an independent, read-only architectural, security, and empirical closure review of **Phase 4 Step 3**, in which the read-only RAG retrieval tool `search_manuals` was implemented across a process bridge between the primary MCP server host environment (Base Python 3.11.9) and the dedicated RAG environment (`.venv-rag`).

### Audit Methodology
1. **Repository Integrity Preflight:** Inspected Git HEAD, branch tracking, staging index, working tree state, and untracked file inventory.
2. **Subprocess Bridge Security Audit:** Traced process execution boundaries, argument construction, shell avoidance, stream isolation, timeout enforcement, memory bounds, and failure modes across `rag_bridge.py` and `bridge_runner.py`.
3. **Retrieval Correctness & Score Semantics Audit:** Compared the bridge execution path with Phase 3 `RetrievalService`, verified model weights and ChromaDB collections queried, analyzed the mathematical derivation of cosine similarity from HNSW raw distance, and verified synthetic provenance flagging and safety metadata preservation.
4. **Protected Invariant Reconciliation:** Independently queried and verified SQLite table counts, ChromaDB record counts, embedding dimensions, Phase 3 corpus metrics, calibrated ML thresholds, lockfile SHA-256 hashes, and environment separation.
5. **Test Evidence Audit:** Executed regression test suites across both environments without mutating persistent databases or vector indices.
6. **Findings Classification:** Systematically classified observations according to defined severity tiers (CRITICAL, HIGH, MEDIUM, LOW, INFO) with blocking criteria.

---

## 2. Repository Preflight and Implementation Inventory

### 2.1 Git State
- **Branch:** `main` tracking `origin/main` (`ahead 0, behind 0`).
- **HEAD Commit:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` (`feat(rag): complete Phase 3 grounded generation, safety validation, and audit evidence`).
- **Staged Files:** Exactly `0` files.
- **Tracked Modifications:** Exactly `0` files.
- **Untracked Inventory:** All existing Phase 3 and Phase 4 audit reports, server implementation modules, and test suites are strictly preserved.

### 2.2 Implementation File Path Reconciliation
The audit verified the following implementation modules:
- `backend/app/rag/bridge_runner.py`: Subprocess runner executed within `.venv-rag`. *(Note: Audit prompt referenced `backend/app/mcp_server/bridge_runner.py`; the file is situated in `backend/app/rag/` to align with the RAG package structure)*.
- `backend/app/mcp_server/rag_bridge.py`: Base Python bridge orchestrator.
- `backend/app/mcp_server/schemas.py`: Pydantic input/output schemas with `extra="forbid"`.
- `backend/app/mcp_server/tools.py`: Tool 5 handler function `handle_search_manuals`.
- `backend/app/mcp_server/server.py`: Registered `@server.tool(name="search_manuals")`.
- `backend/tests/test_mcp_rag_retrieval.py`: 15 automated test cases.

---

## 3. Subprocess Bridge Security Audit

The bridge design was evaluated against 12 security and operational criteria:

| Criterion | Implementation Mechanism | Audit Finding | Status |
| :--- | :--- | :--- | :--- |
| **1. Target Interpreter** | Resolves `repo_root / ".venv-rag" / "Scripts" / "python.exe"` (or `bin/python` on POSIX) | Hardcoded relative to repo root; non-user-controllable | **PASS** |
| **2. Config vs User Path** | Path determined strictly by filesystem inspection | No user query or header affects interpreter path | **PASS** |
| **3. Shell Injection Avoidance** | `subprocess.run([str(venv_python), "-u", "-m", ...], shell=False)` | Uses direct OS argument vector (`CreateProcessW`); zero shell interpolation | **PASS** |
| **4. Explicit CWD** | `cwd=str(repo_root)` | Explicitly set to repository root | **PASS** |
| **5. Structured Protocol** | `stdin` carries JSON payload `{"query": ..., "k": ...}` | Structured JSON I/O over standard pipes | **PASS** |
| **6. Clean Child `stdout`** | `sys.stdout.write(json.dumps(...) + "\n")` | Responds with exactly one JSON line; telemetry disabled | **PASS** |
| **7. Diagnostics to `stderr`** | `StreamHandler(sys.stderr)` configured in runner | HuggingFace and ChromaDB notices routed to `stderr` | **PASS** |
| **8. Schema Validation** | `SearchManualsResponse` and `ManualSearchResult` (`extra="forbid"`) | Rejects undeclared fields or malformed data | **PASS** |
| **9. Finite Timeout** | `timeout=30.0` passed to `subprocess.run` | Enforced by standard library timeout mechanism | **PASS** |
| **10. Process Cleanup** | Standard library `subprocess.run` handles termination | `process.kill()` and `process.wait()` called on `TimeoutExpired` | **PASS** |
| **11. Secret Protection** | Exception formatting does not dump `env` or secrets | Sanitized diagnostic error strings | **PASS** |
| **12. Failure Modes** | Handles non-zero exits, empty stdout, and malformed JSON | Safely maps to `RAGBridgeProcessError` or `RAGBridgeError` | **PASS** |

### Specific Investigation: Extra `stdout` Line Rejection
In `rag_bridge.py` lines 179–188:
```python
stdout_text = proc.stdout.strip()
if not stdout_text:
    raise RAGBridgeProcessError("RAG bridge subprocess returned empty output on stdout.")

try:
    response_data = json.loads(stdout_text)
except json.JSONDecodeError as exc:
    raise RAGBridgeProcessError(f"Malformed JSON from RAG bridge runner: {exc}") from exc
```
If any extraneous string or warning were prepended or appended to `stdout`, `json.loads` strictly raises `json.JSONDecodeError: Extra data` (e.g., at line 2 column 1). The bridge catches this exception and rejects the payload with `RAGBridgeProcessError`. Extraneous lines cannot be accepted as valid.

### Specific Investigation: Memory Boundedness
- Input `k` is clamped to $[1, 20]$.
- Canonical chunk lengths in `knowledge_base/index/chroma_bge_small_v1` average ~600 characters (max 424 tokens).
- Maximum theoretical JSON payload for $k=20$ is $<50\text{ KB}$.
- `capture_output=True` buffers $<50\text{ KB}$ in memory, guaranteeing zero risk of memory exhaustion or pipe deadlock.

---

## 4. Retrieval Correctness and Score Semantics

### 4.1 Underlying Model and Collection Verification
- **Embedding Model:** `BAAI/bge-small-en-v1.5` pinned to commit `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.
- **Embedding Dimensions:** 384 dimensions, L2-normalized unit vectors (`normalize=True`).
- **Vector Store:** ChromaDB collection `manumind_bge_small_v1` located at `knowledge_base/index/chroma_bge_small_v1` (564 vector embeddings).
- **Pipeline Delegation:** Delegated directly to Phase 3 `RetrievalService`. Zero duplicated search or embedding code was introduced in the bridge.

### 4.2 Critical Similarity-Score Mathematical Analysis
In `backend/app/rag/retrieval_service.py` lines 163–167:
```python
# Cosine distance to similarity: similarity = 1.0 - distance
# For unit-normalized vectors: cosine_dist = 1 - cosine_sim
raw_dist_float = float(dist)
derived_sim = max(0.0, min(1.0, 1.0 - raw_dist_float))
```

1. **Distance Metric:** ChromaDB collection configured with `hnsw:space = "cosine"`.
2. **Formula:** For L2-normalized embeddings $u, v \in \mathbb{R}^{384}$:
   $$\text{cosine\_distance} = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2} = 1 - \cos(\theta) \in [0.0, 2.0]$$
3. **Score Derivation:**
   $$\text{similarity\_score} = \max(0.0, \min(1.0, 1.0 - \text{raw\_dist})) = \max(0.0, \min(1.0, \cos(\theta)))$$
4. **Properties:**
   - Range: strictly bounded to $[0.0, 1.0]$.
   - Monotonicity: larger values strictly represent greater angular proximity in embedding space.
   - Mathematically sound representation of non-negative cosine similarity.
5. **Score Labeling & Disclaimer Compliance:**
   - `schemas.py` explicitly documents `similarity_score` as `"Derived cosine similarity score [0.0, 1.0]"`.
   - The tool does **not** label this score as a probability, confidence interval, or likelihood of machine failure.
   - Includes mandatory disclaimer: `"Retrieved excerpts are for reference and troubleshooting assistance only. Material derived from synthetic incident logs is clearly identified and does NOT constitute approved operational directives or verified physical root cause."`

### 4.3 Provenance and Metadata Retention
- **Metadata Preserved:** `document_id`, `parent_chunk_id`, `category`, `section_heading`, `parent_heading`, `source_path`, `content`, `content_hash`, `provenance_validated`.
- **Synthetic Flags:** Synthetic incident logs retain `is_synthetic: true` and the required notice (`> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL...**`).
- **Safety Flags:** Safety-critical documents retain `is_safety_related: true`.

---

## 5. Protected Invariant Reconciliation

Every project invariant was independently queried and confirmed:

| Invariant | Expected Value | Observed Value | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **SQLite Machines** | 10 | 10 | Direct SQL count (`SELECT COUNT(*) FROM machines`) | **EXACT MATCH** |
| **SQLite Sensor Readings** | 40,000 | 40,000 | Direct SQL count (`SELECT COUNT(*) FROM sensor_readings`) | **EXACT MATCH** |
| **SQLite Alerts** | 5 | 5 | Direct SQL count (`SELECT COUNT(*) FROM alerts`) | **EXACT MATCH** |
| **SQLite Tickets** | 1 | 1 | Direct SQL count (`SELECT COUNT(*) FROM tickets`) | **EXACT MATCH** |
| **ChromaDB Collection** | `manumind_bge_small_v1` | `manumind_bge_small_v1` | `PersistentClient.get_collection()` | **EXACT MATCH** |
| **ChromaDB Record Count** | 564 | 564 | `collection.count()` | **EXACT MATCH** |
| **Embedding Dimensions** | 384 | 384 | `len(peek['embeddings'][0])` | **EXACT MATCH** |
| **Phase 3 Source Documents** | 418 | 418 | Reconciliation manifest check | **EXACT MATCH** |
| **Canonical Chunks** | 564 | 564 | Chunk manifest check | **EXACT MATCH** |
| **Synthetic Placeholders** | 123 | 123 | Placeholder audit catalog check | **EXACT MATCH** |
| **Isolation Forest Threshold** | 0.0269 | 0.0269 | `backend.app.ml.inference.config` | **EXACT MATCH** |
| **LSTM Autoencoder Threshold**| 0.901464 | 0.901464 | `backend.app.ml.inference.config` | **EXACT MATCH** |
| **RAG Lockfile SHA-256** | `778fde76...` | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | SHA-256 calculation | **EXACT MATCH** |
| **Base Python Dependencies** | Clean | Clean (`No broken requirements found`) | `pip check` | **PASS** |
| **`.venv-rag` Dependencies** | Clean | Clean (`No broken requirements found`) | `pip check` | **PASS** |
| **MCP Server Tools Count** | 5 | 5 (`ping`, `get_machine_data`, `detect_anomaly`, `predict_failure_risk`, `search_manuals`) | `MCPServer._tool_manager` inspection | **EXACT MATCH** |

---

## 6. Test Evidence Audit

The independent audit reviewed all test suites and verified that 62 automated tests pass across both Python environments:

| Test Suite | Environment | Total Tests | Passed | Execution Time | Focus Area |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `test_mcp_rag_retrieval.py` | Base Python | 15 | 15 | 32.63s | Input validation, live bridge retrieval, schema enforcement, subprocess error handling, stdio lifecycle |
| `test_mcp_manufacturing_tools.py` | Base Python | 20 | 20 | 73.09s | Tools 1–3, time windows, live Isolation Forest & LSTM Autoencoder, Kernel SHAP, stdio lifecycle |
| `test_mcp_server_skeleton.py` | Base Python | 4 | 4 | 6.34s | Server initialization, ping tool metadata & execution, stdio lifecycle |
| `test_rag_retrieval.py` | `.venv-rag` | 14 | 14 | 2.32s | QueryProcessor, RetrievalService, ranking order, distance conversion, machine & safety filtering |
| `test_rag_source_resolver.py` | `.venv-rag` | 9 | 9 | 0.03s | Source path existence, hash verification, row bounds |
| **Total Automated Tests** | — | **62** | **62** | — | **100% Passing** |

---

## 7. Findings and Severity Classification

| Finding ID | Severity | File Reference | Summary | Step 4 Blocking |
| :--- | :--- | :--- | :--- | :--- |
| **`F-PHASE4-S3-001`** | **INFO** | `backend/app/rag/bridge_runner.py:1` | Bridge runner placed in `backend/app/rag/` rather than `mcp_server/` to respect Phase 3 package modularity. | No |
| **`F-PHASE4-S3-002`** | **INFO** | `backend/app/rag/retrieval_service.py:166` | Derived cosine similarity score is accurately described; disclaimers prevent probability confusion. | No |
| **`F-PHASE4-S3-003`** | **LOW** | `backend/app/mcp_server/rag_bridge.py:146` | Short-lived subprocess execution introduces ~9.8s cold-start latency per search. Safe and acceptable for Phase 4. | No |
| **`F-PHASE4-S3-004`** | **INFO** | `backend/app/mcp_server/rag_bridge.py:179` | Single-line JSON protocol strictly rejects extraneous stdout or diagnostic output. | No |
| **`F-PHASE4-S3-005`** | **INFO** | `backend/tests/test_mcp_rag_retrieval.py:378` | Real stdio subprocess tests on Windows require loopback permissions for ProactorEventLoop self-pipe. | No |

*Zero CRITICAL, HIGH, or MEDIUM severity findings were identified.*

---

## 8. Git Governance and Audit Manifest

1. **Staging Index:** Exactly 0 staged files. No `git add` or `git commit` commands were executed.
2. **Untracked Evidence:** All Phase 3 and Phase 4 audit files remain intact.
3. **Audit Artifacts Created:**
   - Manifest: `reports/phase4/phase4_step3_1_independent_rag_mcp_audit.json`
   - Report: `reports/phase4/phase4_step3_1_independent_rag_mcp_audit_report.md`

---

## 9. Final Verdict and Next Action

**Final Verdict:** **`APPROVED FOR STEP 4`**

### Recommended Next Action
Phase 4 Step 3 and Step 3.1 have been completed and verified. The repository is ready for explicit user authorization to proceed to **Phase 4 Step 4** (implementing Tool 4: `get_maintenance_history` and/or subsequent read-only tools according to the approved roadmap).
