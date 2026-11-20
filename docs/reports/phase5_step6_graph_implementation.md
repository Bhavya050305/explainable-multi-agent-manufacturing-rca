# ManuMind AI — Phase 5 Step 6: Multi-Agent StateGraph Orchestration & Human Gate Routing Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Milestone:** Phase 5 Step 6 — Multi-Agent StateGraph Orchestration & Human Gate Routing  
**Timestamp:** 2026-11-20T14:15:00+05:30  
**Implementation Verdict:** **SUCCESS**

---

## 1. Executive Summary

Phase 5 Step 6 interconnects the independently developed and audited worker agents (**Supervisor Agent**, **Anomaly Detection Agent**, and **Root Cause Analysis Agent**) into an authoritative, robust, and deterministic LangGraph `StateGraph` workflow within `backend/app/agents/graph.py`.

In addition to orchestrating the primary diagnostic agents, Step 6 introduces two critical governance and security boundary nodes:
1. **Verification and Evidence Governance Node (`verification_governance`)**: Operates under Supervisor authority to evaluate formulated candidate root-cause hypotheses, enforce independent multi-source corroboration ($\ge 2$ distinct source types), apply strict score capping on synthetic telemetry ($\le 0.70$), and guarantee that candidate hypotheses remain strictly `UNVERIFIED` until external human operator review.
2. **Human Approval Gate Node (`human_approval_gate`)**: Manages human-in-the-loop governance. When maintenance action proposals are generated, it halts workflow execution in `WAITING_FOR_HUMAN_APPROVAL` on `PENDING`, isolating the Phase 4 ticket-dispatch tool (`create_maintenance_ticket`) behind the external HMAC approval token boundary.

The implementation was validated against a 40-test orchestration suite covering all 7 required audit categories in `backend/tests/test_agent_graph.py` and regression-tested across the full 185-test Phase 5 test suite with a **100% pass rate** (185/185 passed).

---

## 2. Git & Baseline Environment Invariants

Strict repository and environment preservation was maintained throughout implementation:

| Metric / Check | Value / Invariant | Status |
| :--- | :--- | :--- |
| **Git Repository** | `D:\Desktop\FInal year project\manumind-ai` | Verified |
| **Current Branch** | `main` | Verified |
| **Git Baseline HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Exact Match |
| **Staged Git Modifications** | `0` (Zero files staged) | Verified |
| **Alembic Database Head** | `f3a9082b1c42` | Exact Match (Read-only) |
| **Python Environment** | Python 3.11.9 (Windows) | Verified |
| **pip check** | `No broken requirements found.` | 100% Clean |
| **RAG Lockfile SHA256** | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Exact Match |
| **ChromaDB Store** | `knowledge_base/index/chroma_bge_small_v1` | Verified |
| **Chroma Collection** | `manumind_bge_small_v1` (564 chunks, 384 dim) | Exact Match |

### Model Artifact Hashes (SHA256)
All 7 production ML models and scalers remain completely unaltered:
- `isolation_forest.joblib`: `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2`
- `isolation_forest_metadata.json`: `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5`
- `lstm_autoencoder.keras`: `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5`
- `lstm_autoencoder_metadata.json`: `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1`
- `resnet_defect_classifier.keras`: `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98`
- `resnet_defect_classifier_metadata.json`: `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73`
- `sensor_scaler.joblib`: `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf`

---

## 3. Multi-Agent StateGraph Architecture

### 3.1 Workflow Topology Diagram

```mermaid
flowchart TD
    START([START]) --> Supervisor[supervisor<br/>Dynamic Routing & Governance]
    
    Supervisor -->|ROUTE_TO_ANOMALY_DETECTION| AnomalyNode[anomaly_detection<br/>5-Channel Telemetry ML Pipeline]
    Supervisor -->|ROUTE_TO_ROOT_CAUSE_ANALYSIS| RCANode[root_cause_analysis<br/>Multi-Source Evidence & Hypotheses]
    Supervisor -->|ESCALATE_TO_HUMAN_GATE| HumanGateNode[human_approval_gate<br/>Operator Authorization & HMAC Isolation]
    Supervisor -->|COMPLETE / FAIL| END([END])
    
    AnomalyNode -->|Return Anomaly Assessment| Supervisor
    
    RCANode -->|Formulated Hypotheses| GovNode[verification_governance<br/>Source Diversity & Synthetic Capping]
    GovNode -->|Evidence Corroboration Decision| Supervisor
    
    HumanGateNode -->|PENDING: Workflow Halts| END
    HumanGateNode -->|APPROVED / REJECTED / EXPIRED| Supervisor
```

### 3.2 Graph Nodes and Responsibilities

1. **`supervisor` Node (`create_supervisor_node`)**:
   - Executes `SupervisorAgent.route(state)`.
   - Evaluates machine telemetry, anomaly outputs, candidate hypotheses, and human approval status.
   - Enforces exception boundaries: unexpected node errors are caught and recorded safely as `WorkflowStatus.FAILED` without crashing the application host.
   - Disallows circular re-execution through strict execution-state guards.

2. **`anomaly_detection` Node (`create_anomaly_detection_node`)**:
   - Executes `AnomalyDetectionAgent.detect(state)`.
   - Runs multivariate Isolation Forest scoring, statistical envelope checks, and SHAP feature attribution across all 5 physical sensors (`vibration`, `temperature`, `pressure`, `current`, `rpm`).
   - Normal telemetry cleanly concludes workflow via Supervisor evaluation without triggering unnecessary downstream RCA.

3. **`root_cause_analysis` Node (`create_rca_node`)**:
   - Executes `RootCauseAnalysisAgent.analyze(state)`.
   - Ingests anomaly context, queries MCP maintenance history (`handle_get_maintenance_history`), and performs semantic search over technical manuals via RAG bridge (`handle_search_manuals`).
   - Generates ranked candidate root cause hypotheses (`candidate_root_causes`) via `ManuMindLLMClient`.
   - Preserves source availability disclosures (`AVAILABLE`, `EMPTY`, `UNAVAILABLE`, `FAILED`).

4. **`verification_governance` Node (`verification_governance_node`)**:
   - Evaluates formulated hypotheses against the collected evidence.
   - Computes distinct evidence source diversity count ($\ge 2$ required for corroboration).
   - Applies strict capping on synthetic evidence ($\le 0.70$) to prevent simulated data from asserting high diagnostic certainty.
   - Generates an authoritative `RootCauseVerificationDecision` under `Supervisor:CorroborationEngine` with `INSUFFICIENT_DATA` status, preserving candidate hypotheses as `UNVERIFIED` awaiting physical human verification.

5. **`human_approval_gate` Node (`human_approval_gate_node`)**:
   - Governs the transition to external human decision-making.
   - When proposals require review, sets state to `current_stage=HUMAN_APPROVAL_GATE` and `workflow_status=WAITING_FOR_HUMAN_APPROVAL`.
   - **Halting Invariant**: If `approval_status == PENDING`, graph traversal halts immediately at `END`, leaving state stored awaiting external operator action.
   - When resumed with `APPROVED`, `REJECTED`, or `EXPIRED`, routes back to `supervisor` to conclude workflow safely.

---

## 4. Security & Governance Invariants

### 4.1 Acyclic State Progression & Loop Prevention
To prevent runaway execution loops, multiple independent safeguards are active:
- **Supervisor Routing Guard**: If RCA has executed (recorded in `rca_execution_status`, `root_cause_analysis_result`, or `agent_executions`), Supervisor routes directly to `human_approval_gate` rather than re-triggering RCA, even if zero hypotheses were produced.
- **Edge Routing Interceptor**: `route_from_supervisor` inspects execution history. If `action == ROUTE_TO_ROOT_CAUSE_ANALYSIS` but RCA has already completed, it intercepts the route and transitions to `human_approval_gate`.
- **Recursion Safety**: The graph enforces deterministic termination well within LangGraph's default recursion limit.

### 4.2 Worker Write Boundaries
Reducers and state update validators enforce strict channel access controls:
- **Forbidden Channels**: `human_approval`, `verification_decisions`, and `workflow_status` are restricted. Worker agents (`ANOMALY_DETECTION`, `ROOT_CAUSE_ANALYSIS`) calling `validate_agent_state_update` with these keys immediately raise `PermissionError`.
- **Self-Verification Prohibition**: `CandidateRootCause` cannot be instantiated with `verification_status=VERIFIED`. Worker agents cannot assert authoritative verification.

### 4.3 Ticket Creation Boundary & HMAC Token Isolation
- The Phase 4 tool `create_maintenance_ticket` is strictly isolated from the multi-agent graph.
- Neither `SupervisorAgent` nor worker agents import, reference, or invoke `create_maintenance_ticket`.
- The graph cannot mint HMAC authorization tokens. Maintenance ticket dispatch requires an external human operator to sign the proposal out-of-band and supply the HMAC token to the Phase 4 ticket service.

---

## 5. Verification & Test Results

### 5.1 Step 6 Orchestration Test Suite (`backend/tests/test_agent_graph.py`)

40 tests were implemented across 7 distinct categories. **All 40 tests passed (100% pass rate).**

| Category | Tests | Description | Result |
| :--- | :---: | :--- | :---: |
| **1. Graph Construction** | 1–4 | Graph compilation, node presence, edge connectivity, dependency injection | **4/4 PASS** |
| **2. Normal Workflow Progression** | 5–8 | End-to-end traversal, normal telemetry bypass, RCA handover, evidence preservation | **4/4 PASS** |
| **3. Failure & Degraded Routing** | 9–16 | Anomaly failure, missing channels, partial RCA, LLM downtime, malformed outputs | **8/8 PASS** |
| **4. Governance & Write Boundaries** | 17–24 | Forbidden channel enforcement, synthetic capping, self-verification blocks | **8/8 PASS** |
| **5. Human Approval Gate Lifecycle** | 25–29 | Halting on PENDING, APPROVED/REJECTED progression, invalid transitions | **5/5 PASS** |
| **6. Safety, Boundedness & Repeatability** | 30–35 | Acyclic execution, exception handling, ticket tool isolation | **6/6 PASS** |
| **7. Real Model & Interface Integration** | 36–40 | Live 5-channel ML inference, real RAG subprocess retrieval, state serialization | **5/5 PASS** |

### 5.2 Full Phase 5 Regression Suite

The complete Phase 5 test suite was executed across all 8 test modules:

| Test Module | Test Count | Pass Rate | Execution Duration |
| :--- | :---: | :---: | :---: |
| `backend/tests/test_agent_state.py` | 10 | 100% (10/10) | ~0.5s |
| `backend/tests/test_agent_reducers.py` | 11 | 100% (11/11) | ~0.6s |
| `backend/tests/test_agent_verification_governance.py` | 23 | 100% (23/23) | ~0.8s |
| `backend/tests/test_supervisor_agent.py` | 28 | 100% (28/28) | ~2.3s |
| `backend/tests/test_anomaly_agent.py` | 27 | 100% (27/27) | ~5.8s |
| `backend/tests/test_anomaly_agent_integration.py` | 6 | 100% (6/6) | ~16.5s |
| `backend/tests/test_rca_agent.py` | 40 | 100% (40/40) | ~38.4s |
| `backend/tests/test_agent_graph.py` | 40 | 100% (40/40) | ~45.5s |
| **Total Phase 5 Test Suite** | **185** | **100% (185/185)** | **~105s** |

---

## 6. Milestone Conclusion & Authorization

Phase 5 Step 6 has successfully achieved all architectural, functional, security, and verification requirements:
- Multi-Agent `StateGraph` compiled and operational.
- Human Approval Gate cleanly halts and isolates ticket execution.
- Verification governance enforces multi-source evidence corroboration and synthetic capping.
- 185/185 Phase 5 tests passing with zero failures and zero errors.
- Zero database mutations (Alembic head `f3a9082b1c42` verified).
- Zero uncommitted or staged Git changes (HEAD `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`).

**Final Verdict:** **SUCCESS**  
Phase 5 Step 6 is formally complete. Awaiting user authorization before proceeding to Phase 5 Step 7.
