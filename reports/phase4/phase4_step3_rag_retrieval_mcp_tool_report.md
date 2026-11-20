# ManuMind AI — Phase 4 Step 3: Read-Only RAG Retrieval MCP Tool Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Target Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`  
**Remote Origin:** `https://github.com/Bhavya050305/explainable-multi-agent-manufacturing-rca.git`  
**Synchronization Status:** Synchronized (`ahead 0, behind 0`)  
**Predecessor Milestone:** Phase 4 Step 2 — Read-Only Manufacturing MCP Tools Implementation (Tools 1–3)  
**Current Milestone:** Phase 4 Step 3 — Read-Only RAG Retrieval MCP Tool Implementation via Process Bridge (`search_manuals`)  
**Execution Timestamp:** 2026-11-15T18:00:00+05:30  
**Verdict:** **`READY FOR STEP 4`**

---

## 1. Executive Summary & Final Verdict

During **Phase 4 Step 3**, the read-only RAG retrieval tool `search_manuals(query: str, k: int = 5)` was implemented, registered on the active `MCPServer`, and verified end-to-end:

1. **Controlled Subprocess Bridge:** Built an isolated process bridge between the primary MCP server host environment (Base Python 3.11.9) and the dedicated RAG environment (`.venv-rag`). The bridge eliminates dependency cross-contamination by keeping PyTorch 2.5.1, Transformers 4.46.3, tokenizers, and ChromaDB 0.5.23 strictly inside `.venv-rag`.
2. **Deterministic Stream Protocol:** The bridge runner (`backend/app/rag/bridge_runner.py`) reads JSON from `stdin`, runs the existing Phase 3 `RetrievalService`, outputs a single line of structured JSON to `stdout`, and routes all diagnostic logs, telemetry, and third-party notices strictly to `stderr`.
3. **Pydantic Schema & Input Validation:** Strict input bounds are enforced in `backend/app/mcp_server/rag_bridge.py`: non-empty, non-whitespace queries capped at 500 characters, and $1 \le k \le 20$. Tool 5 returns ranked `ManualSearchResult` objects including document ID, category, section headings, cosine similarity scores $[0.0, 1.0]$, excerpt content, synthetic provenance indicators, and safety disclaimers.
4. **End-to-End Test Suite:** Created `backend/tests/test_mcp_rag_retrieval.py` containing 15 automated tests covering input validation, live ChromaDB retrieval, synthetic provenance flagging, schema enforcement (`extra="forbid"`), bridge exception resilience, server tool discovery, and a full stdio subprocess lifecycle test over JSON-RPC 2.0. All 15 tests passed.
5. **Full Regression & Invariant Preservation:** Verified that all 20 tests in `test_mcp_manufacturing_tools.py` and all 4 tests in `test_mcp_server_skeleton.py` continue to pass. Confirmed zero mutations to SQLite (`machines: 10, readings: 40000, alerts: 5, tickets: 1`), zero mutations to ChromaDB (564 embeddings, 384 dimensions), and unchanged lockfile SHA-256 (`778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2`).
6. **Strict Governance:** Zero Git staging, commits, pushes, resets, or stash operations were performed.

**Final Verdict:** **`READY FOR STEP 4`**

---

## 2. Preflight Git and Environment State

Preflight inspections verified repository integrity and complete synchronization with `origin/main`:

| Parameter | Observed Value | Expected Baseline | Status |
| :--- | :--- | :--- | :--- |
| **Branch** | `main` | `main` | MATCH |
| **Current HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | MATCH |
| **Remote Status** | `origin/main` | Synchronized (`ahead 0, behind 0`) | MATCH |
| **Staged Modifications** | `0 files` | `0 files` | PASS |
| **Tracked Modifications** | `0 files` | `0 files` | PASS |
| **Python Environment (MCP)** | Base Python 3.11.9 (AMD64) | Base Python 3.11.9 | PASS |
| **Python Environment (RAG)** | `.venv-rag` Python 3.11.9 | `.venv-rag` Python 3.11.9 | PASS |
| **RAG Lockfile SHA-256** | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Identical to Phase 3 baseline | PASS |
| **Active SQLite Row Counts** | `machines: 10, readings: 40000, alerts: 5, tickets: 1` | Exact Phase 3 baseline | PASS |
| **ChromaDB Index Count** | 564 embeddings (dim 384) | 564 embeddings (dim 384) | PASS |

---

## 3. Subprocess Bridge Architecture

To respect the frozen Phase 3 environment boundary without polluting the base MCP host environment with heavy ML/RAG dependencies (PyTorch, Transformers, ChromaDB, tokenizers), a short-lived synchronous subprocess bridge was implemented:

```
[MCP Client / LangGraph]
        │ JSON-RPC 2.0 (stdio)
        ▼
[MCP Server (Base Python 3.11.9)]
   ├── Tool 1: get_machine_data
   ├── Tool 2: detect_anomaly
   ├── Tool 3: predict_failure_risk
   └── Tool 5: search_manuals
           │
           │  Subprocess Stdio Bridge (rag_bridge.py)
           │  JSON Payload on stdin: {"query": "...", "k": 5}
           ▼
[Bridge Runner (backend/app/rag/bridge_runner.py)]
   └── Python Executable: .venv-rag\Scripts\python.exe
           │
           │  In-process RetrievalService invocation
           ├── BAAI/bge-small-en-v1.5 Embedding Model
           └── ChromaDB Index: knowledge_base/index/chroma_bge_small_v1 (564 docs)
           │
           │  JSON Response on stdout: {"status": "SUCCESS", "results": [...]}
           │  Diagnostics / Telemetry strictly to stderr
           ▼
[MCP Server] Parse JSON, validate Pydantic SearchManualsResponse, return to caller
```

### Stream Isolation Guarantees
- **`stdout` Reservation:** The bridge runner flushes only valid, single-line JSON responses to `sys.stdout`.
- **`stderr` Routing:** ChromaDB telemetry, HuggingFace loading notices, and application logs are directed to `sys.stderr`.
- **Environment Telemetry Supression:** Set `ANONYMIZED_TELEMETRY="False"`, `CHROMA_TELEMETRY="False"`, and `TOKENIZERS_PARALLELISM="false"` prior to imports.
- **Child Error Handling:** Non-zero child exit codes, timeouts (default 30.0s), and malformed JSON are intercepted and mapped to typed exceptions (`RAGBridgeTimeoutError`, `RAGBridgeProcessError`, `RAGBridgeError`).

---

## 4. Tool Contract and Implementation

### Tool 5: `search_manuals`
- **MCP Tool Name:** `search_manuals`
- **Description:** Execute read-only semantic vector retrieval across manufacturing standard operating procedures (SOPs), troubleshooting manuals, and safety documentation indexed in ChromaDB. Returns ranked knowledge excerpts with cosine similarity scores, section headings, and synthetic provenance indicators. Excludes LLM generative synthesis or hallucinated advice.
- **Input Parameters:**
  - `query` (`str`, required): Semantic search query describing machine symptoms, maintenance procedures, or safety standards (min 1, max 500 characters).
  - `k` (`int`, optional, default `5`): Number of top ranked knowledge segments to retrieve (min 1, max 20).
- **Output Schema (`SearchManualsResponse`):**
  - `status`: `"SUCCESS"` or `"NO_RESULTS"`.
  - `query`: Cleaned query string.
  - `requested_k`: Requested top_k count.
  - `returned_count`: Number of retrieved items.
  - `results`: List of `ManualSearchResult` objects:
    - `rank`: Integer rank (1-indexed).
    - `document_id`: Canonical document identifier (e.g., `DOC-TRB-BEARING-001`).
    - `category`: Category (`SOP`, `TROUBLESHOOTING`, `SAFETY`, `INCIDENT`).
    - `section_heading`: Section title string.
    - `parent_heading`: Parent heading or `null`.
    - `similarity_score`: Derived cosine similarity $[0.0, 1.0]$.
    - `content`: Retrieved text excerpt.
    - `source_path`: Relative repository path.
    - `is_synthetic`: Boolean indicating synthetic demonstration origin.
    - `is_safety_related`: Boolean indicating safety or lockout-tagout procedure.
    - `source_type`: Origin classification string.
    - `segment_id`: Unique ChromaDB segment ID.
    - `parent_chunk_id`: Parent chunk identifier.
    - `content_hash`: Content SHA-256 hash.
    - `provenance_validated`: Boolean confirming provenance hash match.
  - `disclaimer`: Mandatory interpretation disclaimer.
  - `collection_name`: `"manumind_bge_small_v1"`.
  - `embedding_model`: `"BAAI/bge-small-en-v1.5"`.

---

## 5. Verification and Test Results

### 5.1 Step 3 RAG Retrieval Test Suite (`test_mcp_rag_retrieval.py`)
Executed with `pytest backend/tests/test_mcp_rag_retrieval.py -v`:

| Test Name | Focus Area | Result |
| :--- | :--- | :--- |
| `test_rag_input_validation_valid` | Valid queries, whitespace trimming, boundary $k \in \{1, 20\}$ | **PASSED** |
| `test_rag_input_validation_invalid_query` | Empty, whitespace-only, non-string, oversized (>500 chars) | **PASSED** |
| `test_rag_input_validation_invalid_k` | Negative, zero, $>20$, string, float, bool types | **PASSED** |
| `test_rag_venv_python_discovery` | Discovery of `.venv-rag\Scripts\python.exe` interpreter | **PASSED** |
| `test_search_manuals_live_retrieval_ranked_results` | Live vector search against ChromaDB, descending score ranking | **PASSED** |
| `test_search_manuals_safety_procedure_retrieval` | Safety documentation retrieval (`is_safety_related=True`) | **PASSED** |
| `test_search_manuals_synthetic_provenance` | Synthetic disclosure notice and `is_synthetic=True` | **PASSED** |
| `test_search_manuals_schemas_forbid_extra` | Strict Pydantic enforcement (`extra="forbid"`) | **PASSED** |
| `test_rag_bridge_timeout_error` | Subprocess timeout handling (`RAGBridgeTimeoutError`) | **PASSED** |
| `test_rag_bridge_nonzero_exit_code` | Non-zero exit code diagnostics (`RAGBridgeProcessError`) | **PASSED** |
| `test_rag_bridge_malformed_json_output` | Malformed JSON parsing resilience | **PASSED** |
| `test_rag_bridge_empty_stdout` | Empty stdout detection | **PASSED** |
| `test_rag_bridge_error_status_in_json` | Error payload mapping (`RAGBridgeError`) | **PASSED** |
| `test_mcp_server_registers_all_five_tools` | MCPServer tool registry verification (5 tools total) | **PASSED** |
| `test_mcp_server_real_stdio_search_manuals_lifecycle` | End-to-end stdio client JSON-RPC 2.0 lifecycle test | **PASSED** |

**Summary: 15 passed in 32.63s.**

### 5.2 Full Test Suite Regression Verification

1. **MCP Server Skeleton Tests (`test_mcp_server_skeleton.py`):**
   - 4 tests passed in 6.34s.
2. **MCP Manufacturing Tools Tests (`test_mcp_manufacturing_tools.py`):**
   - 20 tests passed in 73.09s (includes live Isolation Forest, LSTM Autoencoder, and SHAP tests).
3. **Dependency Health (`pip check`):**
   - Base Python 3.11.9: `No broken requirements found.`
   - `.venv-rag` Python: `No broken requirements found.`

---

## 6. Project Invariants and Safety Integrity

| Invariant | Value / Status | Verification Method |
| :--- | :--- | :--- |
| **SQLite Database** | 10 machines, 40000 readings, 5 alerts, 1 ticket | Direct SQLite query |
| **ChromaDB Index** | 564 embeddings, 384 dimensions | `chromadb.PersistentClient.count()` |
| **RAG Lockfile** | SHA-256 `778fde76...` | Hash verification |
| **No LLM Generation** | Excluded | Code audit |
| **No LangGraph Agents** | Excluded | Code audit |
| **No Database Writes** | Read-only queries | Schema & transaction audit |
| **Tools 4, 6, 7** | Excluded | Tool registry inspection |

---

## 7. Modified & Created Files with SHA-256 Hashes

| File Path | SHA-256 Checksum | Size | Action |
| :--- | :--- | :--- | :--- |
| `backend/app/rag/bridge_runner.py` | `7efdb74db2226d19001fcca1fb1712889ca6469c93d528f5b0d6e96c62f47c44` | 4,585 bytes | Created |
| `backend/app/mcp_server/rag_bridge.py` | `e1b5427e3d247cd54447a1e91c5b36f5570733f0cbf541cbd0ad3391e083a32a` | 7,641 bytes | Created |
| `backend/app/mcp_server/schemas.py` | `73dded037189a82aa6338c6fe60716b1e35f9600565d446054a06d381abc8911` | 10,154 bytes | Updated |
| `backend/app/mcp_server/tools.py` | `80c85da58e4d20f5bb1740b7c0450edab117fc0235dff251e8fa39d2ec8beb2c` | 19,723 bytes | Updated |
| `backend/app/mcp_server/server.py` | `9db8c4655f92c3d82d0b476b7ba67f569225ad997341504c4baab7eed77c9689` | 9,746 bytes | Updated |
| `backend/app/mcp_server/__init__.py` | `92707bf04dab3f93c8e5c411e519cea0810640dd62a4ca016d09b69298058808` | 1,647 bytes | Updated |
| `backend/tests/test_mcp_rag_retrieval.py` | `204ba04eaa37797644704a67ae920b4f68543489cb8b81f575e413c08402bbc2` | 16,514 bytes | Created |
| `backend/tests/test_mcp_manufacturing_tools.py` | `1faa8db25f8b96f1e57aab3c805a4b78d3a421ef939af8f870af36e430a49682` | 16,532 bytes | Updated |
| `reports/phase4/phase4_step3_rag_retrieval_mcp_tool.json` | Recorded above | — | Created |
| `reports/phase4/phase4_step3_rag_retrieval_mcp_tool_report.md` | Recorded above | — | Created |

---

## 8. Readiness for Phase 4 Step 4

All prerequisites for Phase 4 Step 3 have been successfully implemented and verified:
1. Tool 5 (`search_manuals`) is registered and operational.
2. The subprocess bridge between Base Python 3.11 and `.venv-rag` is robust and thoroughly tested.
3. Total active MCP tools registered on `MCPServer`: **5** (`ping`, `get_machine_data`, `detect_anomaly`, `predict_failure_risk`, `search_manuals`).
4. Step 4 scope is ready to proceed with Tool 4 (`get_maintenance_history`) and/or Tool 6/7 according to the approved roadmap.
