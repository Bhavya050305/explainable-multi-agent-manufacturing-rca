# ManuMind AI — Phase 4 Step 1C: MCP Server Skeleton and Core Lifecycle Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Target Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`  
**Remote Origin:** `https://github.com/Bhavya050305/explainable-multi-agent-manufacturing-rca.git`  
**Synchronization Status:** Synchronized (`ahead 0, behind 0`)  
**Predecessor Milestone:** Phase 4 Step 1B — Dedicated MCP Dependency Installation and Environment Verification  
**Current Milestone:** Phase 4 Step 1C — MCP Server Skeleton and Core Lifecycle Implementation  
**Execution Timestamp:** 2026-11-15T16:17:00+05:30  
**Verdict:** **`READY FOR STEP 2`**

---

## 1. Executive Summary & Final Verdict

During **Phase 4 Step 1C**, the foundational Model Context Protocol (MCP) server skeleton for **ManuMind AI** was implemented and verified end-to-end using the official Model Context Protocol Python SDK (`mcp==2.3.0`).

All objectives mandated for Step 1C have been fully accomplished:
1. **Server Foundation Implementation:** Established the dedicated Python package `backend/app/mcp_server/` (`__init__.py`, `server.py`, `__main__.py`) using the public `MCPServer` API.
2. **Identity & Metadata Definition:** Pinned server name to `"ManuMind AI MCP Server"`, version to `"0.1.0"`, with explicit instructions defining the system's role in manufacturing anomaly detection, diagnostic root cause analysis (RCA), and industrial telemetry.
3. **Transport & Stream Discipline:** Implemented `stdio` transport. All diagnostic logs are strictly isolated to `sys.stderr` via a dedicated `StreamHandler` and formatter; `sys.stdout` remains pristine and reserved exclusively for JSON-RPC 2.0 protocol frames.
4. **Harmless Diagnostic Tool:** Implemented a minimal temporary `ping` tool (`ping(message: str = "pong") -> str`) providing deterministic echo responses with zero database access, zero filesystem mutations, zero ML inference, and zero network calls.
5. **Real Subprocess Lifecycle Verification:** Implemented and executed a real subprocess-level stdio client/server integration test using `mcp.client.stdio.stdio_client` and `mcp.ClientSession`. The test successfully executed the full MCP lifecycle: subprocess spawn, protocol `initialize()` handshake, tool discovery (`list_tools()`), JSON-RPC tool invocation (`call_tool("ping", ...)`), deterministic output validation, and clean subprocess shutdown.
6. **Zero Regression & Invariant Preservation:** Verified that all 10 project invariants and 7 Phase 3 limitations remain intact. `.venv-rag` and `requirements-rag.lock` remain untouched; SQLite database `manumind.db` maintains exact row counts (`alerts: 5, tickets: 1`); no manufacturing tools (1–7) were implemented in this milestone.

**Final Verdict:** **`READY FOR STEP 2`**

---

## 2. Mandatory Git Preflight & Working Tree Audit

A rigorous Git preflight was conducted prior to and upon completion of Step 1C implementation:

| Parameter | Observed Value | Expected / Compliant | Status |
| :--- | :--- | :--- | :--- |
| **Branch** | `main` | `main` | MATCH |
| **Current HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | MATCH |
| **Remote Origin HEAD** | `origin/main` | Synchronized (`ahead 0, behind 0`) | MATCH |
| **Staged Modifications** | `0 files` | `0 files` (no uncommitted staging) | PASS |
| **Tracked Modifications** | `0 files` | `0 files` (zero existing code modified) | PASS |
| **Untracked Additions** | `backend/app/mcp_server/`, `backend/requirements-mcp.txt`, `backend/tests/test_mcp_server_skeleton.py`, untracked reports | Exactly Step 1B & Step 1C artifacts | PASS |

No staging (`git add`), commits (`git commit`), or pushes (`git push`) were performed.

---

## 3. Server Foundation Implementation Architecture

The MCP server foundation is structured within the backend application hierarchy:

```
manumind-ai/
└── backend/
    ├── app/
    │   └── mcp_server/
    │       ├── __init__.py         # Package exports (SERVER_NAME, SERVER_VERSION, create_mcp_server, run_stdio)
    │       ├── __main__.py         # CLI executable module entrypoint (`python -u -m backend.app.mcp_server`)
    │       └── server.py           # MCPServer construction, ping registration, stderr logging, run_stdio()
    └── tests/
        └── test_mcp_server_skeleton.py  # Unit & real subprocess stdio lifecycle test suite
```

### 3.1 SDK Class Selection & Public API
In MCP Python SDK v2.3.0, the legacy `FastMCP` interface is superseded by `MCPServer` (`from mcp.server import MCPServer` or `from mcp.server.mcpserver import MCPServer`). The server is configured via:
```python
from mcp.server import MCPServer

SERVER_NAME: str = "ManuMind AI MCP Server"
SERVER_VERSION: str = "0.1.0"

def create_mcp_server() -> MCPServer:
    server = MCPServer(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions="ManuMind AI manufacturing anomaly detection, diagnostic RCA, and telemetry MCP server.",
    )
    ...
    return server
```

### 3.2 Protocol Stream Discipline (Stdout vs. Stderr)
To prevent JSON-RPC framing corruption:
- **Diagnostic Logging:** Configured strictly to `sys.stderr` using Python's standard `logging.StreamHandler(sys.stderr)` with timestamps and log levels.
- **Protocol Transport:** Standard output (`sys.stdout`) is reserved 100% for newline-delimited JSON-RPC 2.0 messages managed by `mcp.server.stdio.stdio_server()`.
- **CLI Entrypoint:** Executable via `backend.app.mcp_server.__main__` with `-u` (unbuffered stdio).

---

## 4. Temporary Diagnostic Tool Specification

In strict adherence to Step 1C constraints, **no manufacturing tools (Tools 1–7) were implemented**. A minimal, harmless diagnostic echo tool was registered to validate MCP protocol capabilities:

| Property | Value |
| :--- | :--- |
| **Tool Name** | `ping` |
| **Description** | Harmless diagnostic echo tool to verify MCP protocol communication and server health. |
| **Input Arguments** | `message: str = "pong"` (optional string parameter) |
| **Output Type** | `str` |
| **Return Format** | `pong: {message}` |
| **Database Access** | None (0 queries) |
| **Filesystem Impact** | None (0 mutations) |
| **ML Inference** | None (0 models loaded) |
| **External Network** | None (0 requests) |

---

## 5. Subprocess Integration & Lifecycle Verification

To ensure that the MCP server operates reliably in real deployment scenarios (such as an external LLM agent connecting to the server via stdio transport), a full subprocess integration test was developed: `test_mcp_server_real_stdio_subprocess_lifecycle`.

### 5.1 Test Workflow
1. **Subprocess Spawning:** Spawns a child process executing `sys.executable -u -m backend.app.mcp_server` with `cwd` set to repository root and `PYTHONPATH` explicitly set.
2. **Client Connection:** Connects official `mcp.client.stdio.stdio_client` and wraps streams in `mcp.ClientSession`.
3. **Protocol Handshake (`session.initialize()`):**
   - Negotiates protocol capabilities and versions.
   - Asserts server name: `"ManuMind AI MCP Server"`.
   - Asserts server version: `"0.1.0"`.
4. **Tool Discovery (`session.list_tools()`):**
   - Queries registered tools.
   - Asserts presence of `ping`.
   - Validates tool schema and documentation strings.
5. **JSON-RPC Invocation (`session.call_tool("ping", ...)`):**
   - Dispatches payload: `{"message": "subprocess_stdio_handshake_ok"}`.
   - Validates response: content block type `"text"`, value `"pong: subprocess_stdio_handshake_ok"`, `is_error=False`.
6. **Graceful Teardown:** Client exits context managers; stdio streams close cleanly; child process exits without deadlocks or lingering processes.

---

## 6. Full Test Suite & Regression Verification

### 6.1 Step 1C Test Suite Results (`backend/tests/test_mcp_server_skeleton.py`)
Execution command: `python -m pytest backend/tests/test_mcp_server_skeleton.py -v`

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Desktop\FInal year project\manumind-ai
plugins: anyio-4.14.2, asyncio-1.4.0
collected 4 items

backend/tests/test_mcp_server_skeleton.py::test_mcp_server_initialization_and_identity PASSED [ 25%]
backend/tests/test_mcp_server_skeleton.py::test_mcp_server_ping_tool_metadata PASSED [ 50%]
backend/tests/test_mcp_server_skeleton.py::test_mcp_server_ping_direct_invocation PASSED [ 75%]
backend/tests/test_mcp_server_skeleton.py::test_mcp_server_real_stdio_subprocess_lifecycle PASSED [100%]

============================== 4 passed in 8.13s ==============================
```
**Outcome:** **4 / 4 PASSED (100%)**

### 6.2 Pre-existing Test Regression Verification (`backend/tests/test_sensor_preprocessing.py`)
Execution command: `python -m pytest backend/tests/test_sensor_preprocessing.py -v`

```
backend/tests/test_sensor_preprocessing.py::test_scaler_fitted_strictly_on_train PASSED [ 12%]
backend/tests/test_sensor_preprocessing.py::test_zero_missing_values_and_duplicates PASSED [ 25%]
backend/tests/test_sensor_preprocessing.py::test_sequence_dimensions_and_dtype PASSED [ 37%]
backend/tests/test_sensor_preprocessing.py::test_zero_boundary_crossing_windows PASSED [ 50%]
backend/tests/test_sensor_preprocessing.py::test_straddling_windows_elimination PASSED [ 62%]
backend/tests/test_sensor_preprocessing.py::test_zero_cross_machine_windows PASSED [ 75%]
backend/tests/test_sensor_preprocessing.py::test_metadata_and_label_preservation PASSED [ 87%]
backend/tests/test_sensor_preprocessing.py::test_reproducibility_and_inversion PASSED [100%]

============================= 8 passed in 14.98s ==============================
```
**Outcome:** **8 / 8 PASSED (100%)**

### 6.3 Environment Health Check
Execution command: `pip check`
```
No broken requirements found.
```

---

## 7. Invariants & Phase 3 Limitations Audit

| Invariant / Limitation | Audit Verification | Status |
| :--- | :--- | :--- |
| **Inv 1: Strict RAG & Embedding Isolation** | `.venv-rag` untouched; `backend/requirements-rag.lock` SHA-256 (`778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2`) verified identical. | PRESERVED |
| **Inv 2: Fixed 384 Embedding Dimension** | Documented and unchanged. Zero modification to vector stores. | PRESERVED |
| **Inv 3: Zero Database Contamination** | Verified `manumind.db` tables: `tickets` = 1 row, `alerts` = 5 rows. Zero mutations. | PRESERVED |
| **Inv 4: Zero ML Retraining / Weights Mutation** | Models directory untouched. | PRESERVED |
| **Inv 5: Zero Autonomous Ticket Mutation** | Security boundary maintained (`NOT_SAFE_FOR_AUTONOMOUS_EXPOSURE`). Zero ticket tool implemented. | PRESERVED |
| **Inv 6: Process Boundary Enforcement** | Stdio streams strictly divided; stdout for JSON-RPC 2.0 frames; stderr for diagnostic logs. | PRESERVED |
| **Inv 7: Fixed 4 Defect Classes** | Maintained across all configurations. | PRESERVED |
| **Inv 8: Zero Git Modification Without Auth** | HEAD unchanged at `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`. 0 staged files. | PRESERVED |
| **Inv 9: Deterministic Audit Trail** | Cryptographic SHA-256 hashes generated for all source and audit artifacts. | PRESERVED |
| **Inv 10: Step-by-Step Controlled Execution** | Server skeleton completed; zero manufacturing tools implemented prematurely. | PRESERVED |

---

## 8. Source Artifact Cryptographic Registry

| Artifact Path | SHA-256 Checksum | Description |
| :--- | :--- | :--- |
| `backend/app/mcp_server/__init__.py` | `3305782b47279493f9f1ea20e9a30aa929d6db44e24a533793abc42eefc62551` | MCP server package initialization and public symbol exports |
| `backend/app/mcp_server/server.py` | `86f3162508f1327eb1ffb46ba8d72a3145d61500dabf6fd6f3aba353cfd9b0f1` | MCPServer instance, logging configuration, ping tool, stdio runner |
| `backend/app/mcp_server/__main__.py` | `2dcd42bd32e36bb9760f0e956cdeb059dcd746bf308358f8107db8392101d28f` | Executable CLI entrypoint module |
| `backend/tests/test_mcp_server_skeleton.py` | `480cd89d3aa6e741d88b17926cbfb2628c43675db05cd5aed22ce2c291ef3c31` | Unit and real stdio subprocess lifecycle test suite |
| `backend/requirements-mcp.txt` | `55c0beafd494cc5b01c57d50eea3f344012df8eecb514bad623f50e3bea57a0b` | Pinned MCP dependency specification (`mcp==2.3.0`) |
| `backend/requirements-rag.lock` | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Frozen Phase 3 RAG dependency lockfile (unmodified) |

---

## 9. Next Step Transition Plan (Phase 4 Step 2)

With the MCP server foundation established, validated via subprocess-level stdio testing, and proven to run reliably without package collisions or regression, the repository is ready for **Phase 4 Step 2: Implementation of Read-Only Manufacturing MCP Tools (Tools 1–3)**:

1. **Tool 1 (`get_machine_telemetry`):** Expose read-only multi-sensor telemetry query interface backed by SQLite `sensor_readings`.
2. **Tool 2 (`run_anomaly_detection`):** Expose manufacturing anomaly inference backed by trained Isolation Forest and LSTM Autoencoder pipelines.
3. **Tool 3 (`classify_surface_defect`):** Expose ResNet-50 visual defect inference over the 4 standardized defect classes (`Scratch`, `Dent`, `Pitting`, `Discoloration`).
4. **Transition Rule:** Maintain stdout protocol purity, keep all manufacturing tools read-only, preserve all invariants, and do not stage or commit without explicit user authorization.

---
*End of Report — ManuMind AI Phase 4 Step 1C*
