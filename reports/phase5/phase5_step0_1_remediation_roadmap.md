# ManuMind AI — Phase 5 Step 0.1: Prioritized Remediation Roadmap

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Baseline HEAD Commit:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`  
**Date:** 2026-11-17  
**Roadmap Status:** **`IMPLEMENTATION-READY`**  

---

## 1. Roadmap Architecture and Execution Tiers

This remediation roadmap provides an ordered, implementation-ready engineering plan to resolve all nine technical risks and architectural limitations identified in Phase 5 Step 0. The tasks are partitioned into three strictly prioritized tiers:

1. **Priority 0 (Prerequisite Foundations):** Must be resolved in Steps 1–3 before any agent logic is implemented. These tasks establish dependency stability, typed state contracts, and tool permission boundaries.
2. **Priority 1 (Core Agent Logic & Safety):** Must be resolved in Steps 4–8 before multi-agent system integration. These tasks implement agent reasoning, transaction atomicity, confidence rubrics, and prompt injection defenses.
3. **Priority 2 (Evaluation & Production Hardening):** Must be resolved in Steps 9–10 before release. These tasks benchmark diagnostic accuracy across machines M101–M110 and enforce enterprise production deployment gates.

---

## 2. Priority 0 — Prerequisite Foundations (Steps 1–3)

### Item P0-1: LangGraph and Orchestration Dependency Installation
- **Issue Reference:** `ISSUE-01`
- **Target Step:** **Phase 5 Step 1**
- **Root Cause:** Base Python 3.11.9 lacks LangGraph and LangChain Core; orchestration packages were not installed during Phases 1–4 to keep tool development isolated.
- **Selected Solution:** Install pinned orchestration dependencies (`langgraph==0.2.45`, `langchain-core==0.3.15`, `langchain==0.3.7`) directly into Base Python 3.11 using a dedicated requirements file. `.venv-rag` remains strictly untouched.
- **Repository Files Affected:**
  - Create: `backend/requirements-phase5.txt`
  - Audit: `backend/requirements-mcp.txt`
  - Verify: `backend/requirements-rag.lock` (must remain untouched, SHA-256 `778fde76...`)
- **Dependencies:** Base Python 3.11.9, `pydantic==2.13.4`, `mcp==2.3.0`.
- **Implementation Steps:**
  1. Author `backend/requirements-phase5.txt` with pinned package versions.
  2. Install packages in Base Python: `pip install -r backend/requirements-phase5.txt`.
  3. Execute `pip check` across both Base Python and `.venv-rag`.
- **Acceptance Criteria:**
  - `python -c "import langgraph, langchain_core; print('OK')"` executes with zero errors.
  - `pip check` reports *"No broken requirements found"* in both environments.
  - `.venv-rag` packages and lockfile hash remain 100% unchanged.
- **Required Tests:** Import verification test and Pydantic V2 model compilation test.
- **Technical Risks:** Potential pip dependency resolution conflicts if unpinned packages are pulled; mitigated by strict version pinning.

---

### Item P0-2: Typed Shared Workflow State and Domain Schemas
- **Issue Reference:** `ISSUE-01`, `ISSUE-05`, `ISSUE-07`
- **Target Step:** **Phase 5 Step 2**
- **Root Cause:** Multi-agent workflows require strict schema-enforced state passing; unmanaged dictionaries risk silent evidence overwriting or type mismatches.
- **Selected Solution:** Implement `ManuMindWorkflowState` using Pydantic V2 (`extra="forbid"`) with designated slice ownership and append-only reducers (`operator.add`) for trace logs and error details.
- **Repository Files Affected:**
  - Create: `backend/app/agents/__init__.py`
  - Create: `backend/app/agents/schemas.py`
  - Create: `backend/tests/test_agent_schemas.py`
- **Dependencies:** Item P0-1 (`langgraph`, `langchain-core`, `pydantic>=2.10.0`).
- **Implementation Steps:**
  1. Define enums: `WorkflowStatus`, `ApprovalStatus`, `DiagnosticSeverity`.
  2. Implement sub-models: `AnomalyDetectionStateResult`, `DefectClassificationStateResult`, `DocumentCitationState`, `RootCauseHypothesisState`.
  3. Implement `ManuMindWorkflowState` with field validation and slice-level mutation guards.
- **Acceptance Criteria:**
  - Attempting to pass undeclared fields raises `pydantic.ValidationError`.
  - Slice ownership prevents Anomaly Agent from overwriting RCA Agent output.
  - Append-only reducers preserve all error and audit log entries.
- **Required Tests:** Unit tests in `test_agent_schemas.py` verifying model validation, immutability, and serialization.
- **Technical Risks:** Excessive schema rigidity rejecting valid tool metadata; mitigated by explicit optional fields and structured metadata dicts.

---

### Item P0-3: Role-Based MCP Client Adapters
- **Issue Reference:** `ISSUE-07`
- **Target Step:** **Phase 5 Step 3**
- **Root Cause:** All nine tools are exposed on a single MCP server. Agents cannot be trusted to self-police tool access via LLM prompts alone.
- **Selected Solution:** Implement Python-level client adapter classes wrapping the MCP client, exposing only permitted tool methods for each agent role. Tool 9 (`create_maintenance_ticket`) is completely omitted from all agent adapters and restricted to the Human Approval Node.
- **Repository Files Affected:**
  - Create: `backend/app/agents/mcp_client.py`
  - Create: `backend/app/agents/mcp_adapters.py`
  - Create: `backend/tests/test_mcp_adapters.py`
- **Dependencies:** Item P0-1, Item P0-2, `backend/app/mcp_server/server.py`.
- **Implementation Steps:**
  1. Implement `BaseMCPClient` supporting in-process and stdio transport connection to `mcp_server`.
  2. Implement `AnomalyAgentToolAdapter` (exposes Tools 2, 3, 7 only).
  3. Implement `RCAgentToolAdapter` (exposes Tools 5, 6 only).
  4. Implement `SupervisorToolAdapter` (exposes Tools 2, 4 [stub], 8 only).
  5. Implement `HumanApprovalToolAdapter` (exposes Tool 9 only).
- **Acceptance Criteria:**
  - Anomaly Agent calling `propose_maintenance_ticket` raises `AttributeError` / `UnauthorizedToolError`.
  - RCA Agent calling `create_maintenance_ticket` raises `AttributeError` / `UnauthorizedToolError`.
  - Supervisor Agent has zero code path to execute Tool 9.
- **Required Tests:** Unit tests asserting physical absence of unauthorized tool methods on each adapter class.
- **Technical Risks:** Latency overhead if tool dispatch creates unnecessary subprocesses; mitigated by direct in-process `handle_*` delegation during local testing.

---

## 3. Priority 1 — Core Multi-Agent Logic and Safety (Steps 4–8)

### Item P1-1: Anomaly Detection Agent Implementation
- **Issue Reference:** `ISSUE-05`, `ISSUE-07`
- **Target Step:** **Phase 5 Step 4**
- **Root Cause:** System requires an autonomous node to evaluate 5-channel sensor telemetry and surface defect images without performing unauthorized ticket actions.
- **Selected Solution:** Implement the Anomaly Detection Agent node (`anomaly_agent.py`) using `AnomalyAgentToolAdapter`. Ingests telemetry, executes Isolation Forest and LSTM scoring, invokes ResNet-18 image classification if an image is provided, and writes structured evidence to state.
- **Repository Files Affected:**
  - Create: `backend/app/agents/anomaly_agent.py`
  - Create: `backend/tests/test_anomaly_agent.py`
- **Dependencies:** Item P0-2, Item P0-3, `backend/app/mcp_server/tools.py`.
- **Implementation Steps:**
  1. Implement node function `run_anomaly_detection(state: ManuMindWorkflowState) -> Dict[str, Any]`.
  2. Fetch machine readings via `get_machine_data`.
  3. Execute `detect_anomaly` and extract SHAP contributions.
  4. If `state.image_path` is present, call `check_defect_image`.
  5. Format and return `anomaly_result` and `defect_result` state slices.
- **Acceptance Criteria:**
  - Evaluates normal machine M101 as `NORMAL` (`is_anomaly=False`).
  - Evaluates anomalous machine M104 as `ANOMALY_DETECTED` (`is_anomaly=True`).
  - Correctly extracts and attaches top SHAP sensor attribution channels.
- **Required Tests:** Unit tests evaluating normal telemetry, progressive vibration drift, missing channels, and surface defect images.
- **Technical Risks:** Long execution time on cold-start defect image classification; mitigated by skipping image analysis when `image_path` is omitted.

---

### Item P1-2: Root Cause Analysis Agent with Citation & Injection Defense
- **Issue Reference:** `ISSUE-06`, `ISSUE-07`
- **Target Step:** **Phase 5 Step 5**
- **Root Cause:** Manual excerpts could contain indirect prompt injection; retrieved evidence could be hallucinated without proper source attribution.
- **Selected Solution:** Implement the RCA Agent node (`rca_agent.py`) using `RCAgentToolAdapter`. Implements the multi-layered context defense pipeline (XML tag stripping, system instruction invariance, deterministic citation validation, and synthetic placeholder labeling).
- **Repository Files Affected:**
  - Create: `backend/app/agents/rca_agent.py`
  - Create: `backend/app/agents/rag_context_sanitizer.py`
  - Create: `backend/tests/test_rca_agent.py`
- **Dependencies:** Item P0-2, Item P0-3, `backend/app/mcp_server/rag_bridge.py`.
- **Implementation Steps:**
  1. Construct targeted query from anomalous sensor channels (e.g. *"M104 vibration motor bearing SOP"*).
  2. Invoke `search_manuals(query, k=5)`.
  3. Invoke `get_maintenance_history(machine_id)`.
  4. Pass sanitized context through XML quarantine boundaries to LLM reasoning client.
  5. Validate generated citations: ensure every `[CIT-X]` corresponds to an actual retrieved `chunk_id`.
  6. Force `[SYNTHETIC DOCUMENTATION]` label on chunks where `is_synthetic=True`.
- **Acceptance Criteria:**
  - Prompt injection payloads inside manuals are completely ignored by the agent.
  - Every root-cause hypothesis includes valid `[CIT-X]` citation keys.
  - Zero hallucinated citations pass post-generation validation.
- **Required Tests:** Unit tests with adversarial prompt injection text, missing citations, and synthetic chunks.
- **Technical Risks:** RAG bridge subprocess timeout (60s); mitigated by falling back to telemetry + maintenance history with confidence $\le 0.45$.

---

### Item P1-3: Supervisor Agent and LangGraph Orchestration
- **Issue Reference:** `ISSUE-04`, `ISSUE-07`
- **Target Step:** **Phase 5 Step 6**
- **Root Cause:** Multi-agent system requires centralized validation, conditional routing, diagnostic synthesis, and non-hallucinating LLM client abstraction.
- **Selected Solution:** Implement the Supervisor Agent node (`supervisor.py`), `ManuMindLLMClient` protocol (with deterministic offline mock fallback), and compile the LangGraph `StateGraph` with conditional routing edges.
- **Repository Files Affected:**
  - Create: `backend/app/agents/llm_client.py`
  - Create: `backend/app/agents/supervisor.py`
  - Create: `backend/app/agents/graph.py`
  - Create: `backend/tests/test_supervisor_and_graph.py`
- **Dependencies:** Item P0-2, Item P0-3, Item P1-1, Item P1-2.
- **Implementation Steps:**
  1. Implement `ManuMindLLMClient` supporting Gemini, OpenAI, Ollama, and `DeterministicMockLLMProvider`.
  2. Implement input validation: verify `machine_id` matches `^M1(0[1-9]|10)$`.
  3. Define conditional routing: if machine is `NORMAL` and no defect, route directly to `synthesize_report`; if anomalous, route to `rca_node`.
  4. Compile `StateGraph` with checkpointer and trace logging.
- **Acceptance Criteria:**
  - Healthy machines terminate in 1 step without invoking RAG or RCA.
  - Anomalous machines trigger full RCA pipeline.
  - Offline test mode executes 100% deterministically using `DeterministicMockLLMProvider`.
- **Required Tests:** Graph branching tests, state transition tests, and offline LLM failure fallback tests.
- **Technical Risks:** Graph cyclic deadlocks; mitigated by strict Directed Acyclic Graph (DAG) state progression.

---

### Item P1-4: Database Transaction Atomicity Unification
- **Issue Reference:** `ISSUE-02`
- **Target Step:** **Phase 5 Step 7**
- **Root Cause:** Two independent commit points in `ticket_service.py` and `tools.py` create a non-atomic two-phase commit window.
- **Selected Solution:** Refactor `create_ticket_with_approval_gate` to accept `commit: bool = True`. In `handle_create_maintenance_ticket`, pass `commit=False` and execute ticket insertion, proposal status update, and `ConsumedToken` insertion inside a single `with db.begin():` transaction block.
- **Repository Files Affected:**
  - Modify: `backend/app/services/ticket_service.py`
  - Modify: `backend/app/mcp_server/tools.py`
  - Create: `backend/tests/test_transaction_atomicity.py`
- **Dependencies:** Item P0-2, `backend/app/models/ticket_proposal.py`.
- **Implementation Steps:**
  1. Update `create_ticket_with_approval_gate` signature: add `commit: bool = True`. When `False`, call `db.flush()` instead of `db.commit()`.
  2. In `handle_create_maintenance_ticket`, wrap steps 8–10 in `with db.begin():`.
  3. Verify that `proposal.status = "CONSUMED"`, `ConsumedToken`, and `Ticket` are committed in the same database transaction.
- **Acceptance Criteria:**
  - An intentional exception raised during token insertion rolls back the ticket creation completely.
  - Replayed tokens fail inside the transaction; zero duplicate tickets created.
  - Concurrent requests produce exactly 1 ticket and 1 consumed token.
- **Required Tests:** Rollback simulation test, multi-threaded concurrency test, and replay assertion tests.
- **Technical Risks:** Regressing Phase 1 unit tests; mitigated by defaulting `commit=True` in `ticket_service.py` for backward compatibility.

---

### Item P1-5: Confidence Governance and Human Escalation Controls
- **Issue Reference:** `ISSUE-05`
- **Target Step:** **Phase 5 Step 8**
- **Root Cause:** Incommensurable numerical scores cannot be averaged; low-confidence analyses must never automatically stage ungrounded maintenance work orders.
- **Selected Solution:** Implement the **Tiered Evidence Rubric** and explainable decision table in `backend/app/agents/confidence.py`. Enforces `requires_human_review = True` and caps confidence at $0.45$ whenever confidence $< 0.60$ or signals diverge.
- **Repository Files Affected:**
  - Create: `backend/app/agents/confidence.py`
  - Modify: `backend/app/agents/supervisor.py`
  - Create: `backend/tests/test_confidence_governance.py`
- **Dependencies:** Item P1-3, Item P1-4.
- **Implementation Steps:**
  1. Implement `evaluate_evidence_tiers(anomaly_res, defect_res, rca_res, maint_res) -> float`.
  2. Implement conflict detection (e.g. IF anomaly vs. LSTM normal; or high-confidence visual defect with zero sensor drift).
  3. If confidence $< 0.60$, set `state.requires_human_review = True` and suppress automatic invocation of Tool 8 (`propose_maintenance_ticket`).
- **Acceptance Criteria:**
  - Consensus scenarios score $\ge 0.80$; stage ticket proposal.
  - Single-channel or uncorroborated anomalies score $< 0.60$; trigger mandatory human review.
  - Conflicting signals penalize confidence by $0.20$ and alert engineer.
- **Required Tests:** Decision table unit tests evaluating all 6 diagnostic scenarios in Section 6.4 of the Risk Analysis report.
- **Technical Risks:** Over-escalation causing operator alert fatigue; mitigated by calibrated frozen thresholds from Phase 2.

---

## 4. Priority 2 — Evaluation, Hardening & Production Governance (Steps 9–10)

### Item P2-1: 10-Machine Diagnostic RCA Benchmark
- **Issue Reference:** `ISSUE-08`, `ISSUE-09`
- **Target Step:** **Phase 5 Step 9**
- **Root Cause:** Multi-agent accuracy and execution stability must be validated across the complete industrial dataset (M101–M110) before release.
- **Selected Solution:** Implement a comprehensive benchmark suite executing the LangGraph workflow across all 10 machines, verifying correct diagnosis of normal baselines, progressive vibration, pressure spikes, and surface defects.
- **Repository Files Affected:**
  - Create: `backend/tests/test_phase5_benchmark.py`
  - Create: `reports/phase5/phase5_step9_benchmark_results.json`
- **Dependencies:** All Priority 0 and Priority 1 items.
- **Implementation Steps:**
  1. Iterate across machines M101 to M110.
  2. Execute multi-agent graph with `DeterministicMockLLMProvider`.
  3. Assert diagnostic classification against known ground truth (M101–M103 Normal, M104 Progressive Bearing Failure, M105–M110 Specific Faults).
  4. Measure end-to-end execution latency and token usage.
- **Acceptance Criteria:**
  - 100% agreement with calibrated ground truth across all 10 machines.
  - Zero unhandled exceptions or state corruptions.
  - Execution completes within bounded time limits.
- **Required Tests:** Full 10-machine automated benchmark test.
- **Technical Risks:** Test duration exceeding timeout on slow hardware; mitigated by in-process mock LLM execution.

---

### Item P2-2: Production Security Hardening and Closure Audit
- **Issue Reference:** `ISSUE-03`, `ISSUE-09`
- **Target Step:** **Phase 5 Step 10**
- **Root Cause:** Phase 5 development uses mock human authentication adapters; production release requires formal verification that development mocks cannot be accidentally activated in production.
- **Selected Solution:** Implement fail-closed environment guards in `approval.py`; conduct an independent read-only security audit verifying all 9 MCP tools, LangGraph state safety, and transaction atomicity.
- **Repository Files Affected:**
  - Modify: `backend/app/mcp_server/approval.py`
  - Create: `reports/phase5/phase5_step10_security_audit_report.md`
  - Create: `reports/phase5/phase5_step10_security_audit.json`
- **Dependencies:** All previous items.
- **Implementation Steps:**
  1. Verify `MANUMIND_ENV=production` raises `ApprovalConfigurationError` if mock adapter is loaded.
  2. Verify secret key loading fails closed if `MANUMIND_APPROVAL_SECRET_KEY` is missing.
  3. Execute full automated regression suite across all 16 test dimensions.
  4. Generate formal closure audit report and JSON deliverable.
- **Acceptance Criteria:**
  - Production mode fails closed against mock credentials.
  - 100% automated test pass rate across all suites.
  - Protected baseline invariants (SQLite counts, ChromaDB embeddings, ML thresholds, lockfile hashes) remain 100% intact.
- **Required Tests:** Production environment gate test and full regression suite execution.
- **Technical Risks:** None (Read-only closure audit).

---

## 5. Master Implementation Schedule

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MANUMIND AI — PHASE 5 IMPLEMENTATION SCHEDULE                   │
├───────┬─────────────────────────────────────────────────────┬───────────┬──────────────┤
│ Step  │ Milestone Description                               │ Priority  │ Prereq Step  │
├───────┼─────────────────────────────────────────────────────┼───────────┼──────────────┤
│ 0     │ Architecture Readiness Audit & Risk Analysis        │ P0 (Done) │ Phase 4 6.1  │
│ 1     │ Dependency & Environment Setup (LangGraph)          │ P0        │ Step 0       │
│ 2     │ Typed Shared State & Domain Schemas                 │ P0        │ Step 1       │
│ 3     │ Role-Based MCP Client Adapters Layer                │ P0        │ Step 2       │
│ 4     │ Anomaly Detection Agent Implementation              │ P1        │ Step 3       │
│ 5     │ Root Cause Analysis Agent (RAG + Injection Defense) │ P1        │ Step 3       │
│ 6     │ Supervisor Agent & LangGraph Orchestration          │ P1        │ Step 4, 5    │
│ 7     │ Human Approval Gate & Atomic DB Transaction Fix     │ P1        │ Step 6       │
│ 8     │ Confidence Governance & Human Escalation Controls   │ P1        │ Step 7       │
│ 9     │ End-to-End Testing & 10-Machine Benchmark           │ P2        │ Step 8       │
│ 10    │ Independent Phase 5 Security & Closure Audit        │ P2        │ Step 9       │
└───────┴─────────────────────────────────────────────────────┴───────────┴──────────────┘
```

---
*Roadmap certified by Solution Architecture Lead — ManuMind AI Project, Department of AI & Data Science, RMK Engineering College.*
