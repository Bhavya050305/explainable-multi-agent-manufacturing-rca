# ManuMind AI — Phase 4 Step 6: Secure Maintenance Ticket Creation MCP Tool Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` | **Target Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` (`ahead 0, behind 0`)  
**Previous Milestone:** Phase 4 Step 5.1 — Independent Defect Image MCP Tool Audit (`APPROVED FOR STEP 6`)  
**Milestone:** Phase 4 Step 6 — Secure Maintenance Ticket Creation MCP Tool Implementation  
**Execution Timestamp:** 2026-11-16T22:42:00+05:30  
**Implementation Verdict:** **`READY FOR STEP 6.1 INDEPENDENT AUDIT`**

---

## 1. Executive Summary

Phase 4 Step 6 has been completed successfully. We have implemented and verified the final MCP server capability: secure, auditable maintenance-ticket creation governed by a strict human-in-the-loop authorization boundary.

Under this architecture, **an AI agent is physically and cryptographically prevented from authorizing its own ticket creation**. Supplying an arbitrary `approved_by` string is rejected at both the Pydantic schema layer (`extra="forbid"`) and the tool handler signature. Active ticket creation is strictly contingent upon presenting a valid, short-lived, HMAC-SHA256 authorization token cryptographically bound to an immutable proposal and signed by a trusted Human Approval Gate.

### The Two-Stage Approval Architecture
1. **Stage A — Proposal (`propose_maintenance_ticket`):**
   - AI supervisory agents prepare a structured proposal containing target `machine_id`, actionable `recommendation`, and supporting telemetry/defect/RAG `evidence`.
   - Computes a deterministic canonical SHA-256 payload hash (`payload_hash`).
   - Persists a `TicketProposal` record with status `PENDING_APPROVAL`.
   - **Zero active tickets are created.** Zero database alerts or ticket counters are modified.
2. **Stage B — Trusted Human Authorization:**
   - Authenticated plant engineers review the exact proposal via an external approval interface or development adapter (`HumanApprovalProvider`).
   - The provider authenticates the engineer independently of the AI agent, verifies the canonical proposal hash, and issues an HMAC-SHA256 signed token (`approval_token`) bound to `proposal_id` and `payload_hash`.
3. **Stage C — Ticket Creation (`create_maintenance_ticket`):**
   - The agent or pipeline submits `proposal_id` and `approval_token`.
   - The server verifies token signature, issuer, algorithm (`HS256`), expiry, proposal binding, and tamper-evident payload hash.
   - Replay protection verifies that token `jti` has not been consumed in `consumed_tokens`.
   - Upon successful verification, creates the ticket via the existing authoritative service (`create_ticket_with_approval_gate`), marks the proposal `CONSUMED`, and records token consumption atomically.

### Server Tool Inventory
With the addition of tools 8 and 9, the ManuMind AI MCP Server now exposes **exactly nine production tools**:
1. `ping` — Diagnostic echo tool.
2. `get_machine_data` — Asset metadata profile and historical 5-channel sensor telemetry.
3. `detect_anomaly` — Dual-model manufacturing anomaly inference (Isolation Forest & LSTM-Autoencoder).
4. `predict_failure_risk` — Formal capability stub (`NOT_AVAILABLE`).
5. `search_manuals` — Process bridge to ChromaDB RAG vector retrieval in `.venv-rag`.
6. `get_maintenance_history` — Read-only chronological maintenance records from SQLite.
7. `check_defect_image` — Process bridge to Compact ResNet-18 visual defect classifier.
8. `propose_maintenance_ticket` — Staged maintenance ticket proposal awaiting human approval.
9. `create_maintenance_ticket` — Authorized ticket creation with cryptographic human approval token verification.

Across all 11 test suites (Step 6 dedicated suite + 10 regression suites), all **154 automated tests passed** (100% pass rate, 0 failures, 0 regressions). All protected database, ML model, and vector-store invariants remain 100% intact.

---

## 2. Baseline Git State & Governance

Preflight and post-implementation Git governance was verified:

| Parameter | Observed Value | Expected Baseline | Status |
| :--- | :--- | :--- | :---: |
| **Working Directory** | `D:\Desktop\FInal year project\manumind-ai` | `D:\Desktop\FInal year project\manumind-ai` | PASS |
| **Git Branch** | `main` | `main` | PASS |
| **Commit HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | PASS |
| **Remote Synchronization** | `ahead 0, behind 0` (Up to date with origin/main) | Synchronized | PASS |
| **Staged Files** | `0 files` | `0 files` (No staging allowed) | PASS |
| **Tracked Modifications** | `1 file` (`backend/app/models/__init__.py`) | Unstaged model exports | PASS |

---

## 3. Existing Ticket-Service Architecture

The existing ticket infrastructure was audited before design:
- **Model (`backend/app/models/ticket.py`):** `Ticket` table with `id`, `alert_id` (ForeignKey to `alerts.id`, `unique=True`), `recommendation`, `evidence` (JSON), `confidence`, `approval_status`, `approved_by`, and `created_at`.
- **Authoritative Service (`backend/app/services/ticket_service.py`):**
  - Function: `create_ticket_with_approval_gate(db, alert_id, recommendation, evidence, confidence, approved_by, ticket_id=None)`
  - Enforces: If `approved_by` is empty or None, raises `TicketApprovalError`.
  - Verifies: Alert exists in database. If alert already has an active ticket, returns existing ticket.
  - Updates: Sets `alert.status = "APPROVED"`.
  - Creates: Inserts `Ticket` record into database.
- **Architectural Gap Identified:** The Phase 1 gate required non-empty `approved_by`, but could not distinguish whether the string was supplied by an agent or a genuine human engineer. Step 6 resolves this gap by wrapping the service behind cryptographic token verification.

---

## 4. Threat Model & Security Architecture

| Threat Vector | Attack Scenario | Defense & Mitigation Mechanism | Verified in Test |
| :--- | :--- | :--- | :---: |
| **Agent Self-Approval** | Agent attempts to authorize ticket creation directly by passing `approved_by="Lead Engineer S. Raman"` or setting a boolean flag. | `create_maintenance_ticket` schema strictly forbids `approved_by` (`extra="forbid"`). Tool handler signature does not accept approver strings. Only valid signed cryptographic tokens are accepted. | `test_23` |
| **Arbitrary `approved_by` Strings** | Caller invents an approver identity without external verification. | Approver identity is extracted exclusively from the decoded claims of a cryptographically verified token signed by `MANUMIND_APPROVAL_SECRET_KEY`. | `test_23`, `test_24` |
| **Forged Approval Tokens** | Attacker crafts a token with fake claims and signature. | Tokens use HMAC-SHA256. Signatures are verified using constant-time comparison (`hmac.compare_digest`). Forged signatures trigger `InvalidTokenError`. | `test_12` |
| **Modified Recommendation After Approval** | Attacker alters proposal recommendation (e.g. from inspection to plant shutdown) after human approval. | Token is cryptographically bound to canonical `payload_hash`. Handler re-computes the hash from stored proposal fields before execution; any alteration causes hash mismatch rejection. | `test_19` |
| **Modified Machine ID After Approval** | Attacker redirects ticket to a different machine. | `machine_id` is incorporated into the canonical payload hash. Mismatched target machine breaks cryptographic binding. | `test_13`, `test_14` |
| **Modified Supporting Evidence After Approval** | Attacker modifies or strips telemetry evidence after approval. | Evidence is recursively key-sorted and hashed into `payload_hash`. Any alteration triggers `TokenPayloadMismatchError`. | `test_20` |
| **Expired Approval Tokens** | Attacker replays a stale token captured from past communications. | Tokens enforce short validity (default 15 minutes / 900 seconds). Verifier strictly rejects expired tokens (`TokenExpiredError`). | `test_16` |
| **Replayed Approval Tokens** | Attacker re-submits an already-used token to create duplicate tickets. | Token `jti` is permanently stored in `consumed_tokens` table with a primary key constraint. Replayed `jti` triggers immediate rejection. | `test_17`, `test_26` |
| **Duplicate Ticket Creation** | Submitting creation requests repeatedly for the same proposal. | Proposal status transitions from `PENDING_APPROVAL` to `CONSUMED`. Subsequent creation requests fail immediately (`status is 'CONSUMED'`). | `test_18`, `test_28` |
| **Concurrent Approval Requests** | Race condition where concurrent threads submit creation requests simultaneously. | SQLite / PostgreSQL uniqueness constraints on `consumed_tokens.jti` and `tickets.alert_id` ensure exactly one transaction commits; concurrent attempts roll back. | `test_29` |
| **Secret Key Exposure / Leakage** | Signing secret exposed through logs, tool outputs, or tracebacks. | Secret is loaded strictly from environment variable `MANUMIND_APPROVAL_SECRET_KEY`. Never logged, never returned in tool responses, never stored in DB. Missing secret fails closed. | `test_22` |
| **Missing / Malformed Claims** | Attacker omits mandatory claims (e.g. missing `jti`, `v`, `iss`, `action`). | Verifier validates all required claims, algorithm (`HS256`), issuer, and version (`v=1`). Malformed tokens are rejected. | `test_11`, `test_15`, `test_21` |
| **SQL Injection & Invalid Identifiers** | Injection attempts via `machine_id` or proposal IDs. | `machine_id` validated against strict regex `^M1(0[1-9]|10)$`. SQLAlchemy ORM parameterized queries used exclusively. | `test_2` |
| **Accidental Ticket Creation in Proposal** | Agent calls `propose_maintenance_ticket` and unintentionally creates active ticket. | Proposal handler writes strictly to `ticket_proposals` table. Has zero write interactions with `tickets` table. | `test_8` |

---

## 5. Two-Stage Approval Design & Workflow

```
+-----------------------------------------------------------------------------------------+
|                                    STAGE A: PROPOSAL                                    |
|                                                                                         |
|   +-------------------+  propose_maintenance_ticket(machine_id, rec, ev)                |
|   |    AI Agent       |--------------------------------------------------+              |
|   +-------------------+                                                 |              |
|                                                                         v              |
|                                                     +-------------------------------+   |
|                                                     | Compute Canonical SHA-256 Hash|   |
|                                                     +-------------------------------+   |
|                                                                         |              |
|                                                                         v              |
|                                                     +-------------------------------+   |
|                                                     | Insert ticket_proposals       |   |
|                                                     | status: PENDING_APPROVAL      |   |
|                                                     | (ZERO Tickets Created)        |   |
|                                                     +-------------------------------+   |
+-----------------------------------------------------------------------------------------+
                                          |
                                          | Proposal ID & Payload Hash
                                          v
+-----------------------------------------------------------------------------------------+
|                               STAGE B: HUMAN AUTHORIZATION                              |
|                                                                                         |
|   +-------------------+  Authenticate with independent credentials                     |
|   |  Human Engineer   |--------------------------------------------------+              |
|   +-------------------+                                                 |              |
|             |                                                           v              |
|             | Review exact recommendation & evidence        +-----------------------+   |
|             +---------------------------------------------->| HumanApprovalProvider |   |
|                                                             | (Development Adapter) |   |
|                                                             +-----------------------+   |
|                                                                         |              |
|                                                                         v              |
|                                                             +-----------------------+   |
|                                                             | Issue HMAC-SHA256     |   |
|                                                             | Signed Token (15 min) |   |
|                                                             +-----------------------+   |
+-----------------------------------------------------------------------------------------+
                                          |
                                          | Signed approval_token
                                          v
+-----------------------------------------------------------------------------------------+
|                               STAGE C: TICKET CREATION                                  |
|                                                                                         |
|   +-------------------+  create_maintenance_ticket(proposal_id, token)                  |
|   |  Agent / Pipeline |--------------------------------------------------+              |
|   +-------------------+                                                 |              |
|                                                                         v              |
|                                                     +-------------------------------+   |
|                                                     | 1. Verify HMAC Signature      |   |
|                                                     | 2. Check Expiry (exp)         |   |
|                                                     | 3. Verify Proposal Binding    |   |
|                                                     | 4. Verify Payload Hash        |   |
|                                                     | 5. Check Token Replay (jti)   |   |
|                                                     +-------------------------------+   |
|                                                                         |              |
|                                                                         v              |
|                                                     +-------------------------------+   |
|                                                     | Atomic Database Transaction:  |   |
|                                                     | - create_ticket_with_approval |   |
|                                                     | - Mark proposal: CONSUMED     |   |
|                                                     | - Insert consumed_tokens      |   |
|                                                     +-------------------------------+   |
+-----------------------------------------------------------------------------------------+
```

---

## 6. Token Format and Cryptographic Validation

### 6.1 Compact Token Specification
The authorization token uses a standard 3-part base64url-encoded JWT format:
`header_b64.claims_b64.signature_b64`

- **Header:**
  ```json
  {"alg": "HS256", "typ": "JWT"}
  ```
- **Claims:**
  ```json
  {
    "jti": "5e20d563-c761-4623-819c-dc37d232f0e0",
    "proposal_id": "PROP-2026-0001",
    "payload_hash": "b057f89352606e1dc6a55d394370557473de6af0904b5a254d47038a7fb9f532",
    "approver_id": "Lead Engineer S. Raman",
    "approver_role": "Lead Reliability Engineer",
    "action": "APPROVE_MAINTENANCE_TICKET",
    "iat": 1731776500,
    "exp": 1731777400,
    "v": 1,
    "iss": "manumind-human-approval-gate"
  }
  ```

### 6.2 Cryptographic Verification Guarantees
1. **Algorithm Lockdown:** Only `HS256` is permitted. Tokens specifying `alg: "none"` or unexpected algorithms are rejected immediately.
2. **Constant-Time Verification:** Signature verification uses `hmac.compare_digest(expected, actual)` to protect against timing side-channel attacks.
3. **Temporal Validity:** Enforces `now <= exp + clock_skew`. Expired tokens raise `TokenExpiredError`.
4. **Cryptographic Binding:** Tokens are strictly bound to `proposal_id` and canonical `payload_hash`. Alterations to proposal fields break verification.
5. **Replay Invalidation:** Token `jti` is recorded in `consumed_tokens`. Replayed tokens raise `ValueError: Token replay detected`.

---

## 7. Secret Management Approach

- **Configuration:** Signing secret is loaded from `MANUMIND_APPROVAL_SECRET_KEY`.
- **Fail-Closed Behavior:** If the environment variable is missing or empty, all signing and verification attempts raise `ApprovalConfigurationError` and fail closed.
- **Isolation:** Secrets are never hardcoded in source files, never stored in Git, never written to database tables, never returned in MCP tool outputs, and never included in log statements.
- **Rotation:** Key rotation is supported by updating `MANUMIND_APPROVAL_SECRET_KEY`. Active tokens expire in 15 minutes, allowing zero-downtime rotation.

---

## 8. Database Architecture & Alembic Migrations

### 8.1 Schema Design
Two new tables were added via reversible Alembic migration:

1. **`ticket_proposals`:**
   ```sql
   CREATE TABLE ticket_proposals (
       id VARCHAR(50) NOT NULL PRIMARY KEY,
       machine_id VARCHAR(50) NOT NULL REFERENCES machines(id),
       alert_id VARCHAR(50) REFERENCES alerts(id),
       recommendation TEXT NOT NULL,
       evidence JSON NOT NULL,
       confidence FLOAT NOT NULL,
       payload_hash VARCHAR(64) NOT NULL,
       status VARCHAR(50) NOT NULL,
       created_at DATETIME NOT NULL,
       expires_at DATETIME NOT NULL,
       approved_by VARCHAR(100),
       approved_at DATETIME,
       token_id VARCHAR(100) UNIQUE,
       ticket_id VARCHAR(50) UNIQUE REFERENCES tickets(id)
   );
   ```

2. **`consumed_tokens`:**
   ```sql
   CREATE TABLE consumed_tokens (
       jti VARCHAR(100) NOT NULL PRIMARY KEY,
       proposal_id VARCHAR(50) NOT NULL REFERENCES ticket_proposals(id),
       approver_id VARCHAR(100) NOT NULL,
       consumed_at DATETIME NOT NULL,
       token_exp DATETIME NOT NULL
   );
   ```

### 8.2 Migration Reversibility
- Migration file: `backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py`
- Down revision: `1273f18b72a2` (initial tables)
- Upgrades and downgrades were tested on an isolated temporary SQLite database before migrating `manumind.db`.
- The migration was executed on `manumind.db`. Zero existing rows in `machines`, `sensor_readings`, `maintenance_history`, `alerts`, or `tickets` were modified or dropped.

---

## 9. MCP Tool Contracts

### 9.1 Tool 8: `propose_maintenance_ticket`
```python
@server.tool(name="propose_maintenance_ticket")
def propose_maintenance_ticket(
    machine_id: Annotated[str, Field(pattern=r"^M1(0[1-9]|10)$")],
    recommendation: Annotated[str, Field(min_length=5, max_length=1000)],
    evidence: Annotated[Dict[str, Any], Field(...)],
    alert_id: Annotated[Optional[str], Field(None)] = None,
    confidence: Annotated[float, Field(0.85, ge=0.0, le=1.0)] = 0.85,
) -> Dict[str, Any]: ...
```

### 9.2 Tool 9: `create_maintenance_ticket`
```python
@server.tool(name="create_maintenance_ticket")
def create_maintenance_ticket(
    proposal_id: Annotated[str, Field(min_length=1, max_length=100)],
    approval_token: Annotated[str, Field(min_length=1, max_length=2000)],
) -> Dict[str, Any]: ...
```
*Note: Neither `approved_by` nor any bypass flag is accepted as a parameter. `extra="forbid"` rejects extra fields.*

---

## 10. Automated Test Results (154 / 154 Passed)

### 10.1 Dedicated Step 6 Test Suite (`test_mcp_ticket_creation.py`)
All **32 tests passed in 5.58s**:

| Category | Tests | Description | Result |
| :--- | :---: | :--- | :---: |
| **Proposal Validation** | T1–T9 | Input bounds, machine regex, empty/oversized rec, non-dict evidence, schema `extra="forbid"`, proposal stays pending, zero tickets created, synthetic disclaimer | **PASSED** |
| **Approval Security** | T10–T23 | Missing token, malformed token, invalid signature, proposal ID mismatch, payload hash mismatch, untrusted issuer, expired token, replayed token, consumed proposal, tampered recommendation/evidence, invalid alg (`none`), missing secret fails closed, agent self-approval rejection | **PASSED** |
| **Transactions & Concurrency** | T24–T30 | Authorized creation, bidirectional linkage, token consumption record, proposal status transition, duplicate creation rejection, concurrent creation safety, atomic rollback on failure | **PASSED** |
| **MCP Integration** | T31–T32 | All 9 tools registered, real stdio subprocess JSON-RPC handshake, tool discovery, proposal submission, human token issuance, ticket creation | **PASSED** |

### 10.2 Full Regression Suite Execution Summary

| Suite File | Scope / Purpose | Tests | Passed | Failed | Duration | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `backend/tests/test_mcp_ticket_creation.py` | Step 6 Dedicated Suite | 32 | 32 | 0 | 5.58s | **PASS** |
| `backend/tests/test_mcp_defect_image.py` | Step 5 ResNet-18 Defect Classifier | 25 | 25 | 0 | 185.97s | **PASS** |
| `backend/tests/test_mcp_maintenance_history.py` | Step 4 Maintenance History | 14 | 14 | 0 | 12.61s | **PASS** |
| `backend/tests/test_mcp_manufacturing_tools.py` | Step 2 Manufacturing Tools 1–3 | 20 | 20 | 0 | 80.61s | **PASS** |
| `backend/tests/test_mcp_rag_retrieval.py` | Step 3 RAG Semantic Retrieval | 15 | 15 | 0 | 88.96s | **PASS** |
| `backend/tests/test_mcp_server_skeleton.py` | Step 1C MCP Server Lifecycle | 4 | 4 | 0 | 8.91s | **PASS** |
| `backend/tests/test_sensor_preprocessing.py` | Phase 2 Telemetry Preprocessing | 8 | 8 | 0 | 7.61s | **PASS** |
| `backend/tests/test_rag_source_resolver.py` | Phase 3 Source Resolvers (`.venv-rag`) | 9 | 9 | 0 | 0.004s | **PASS** |
| `backend/tests/test_rag_retrieval.py` | Phase 3 ChromaDB Vector Retrieval | 14 | 14 | 0 | 1.741s | **PASS** |
| `backend/tests/test_phase1_audit_and_expansion.py` | Phase 1 Expansion & Approval Gate | 9 | 9 | 0 | 8.39s | **PASS** |
| `backend/tests/test_phase1_db_and_generator.py` | Phase 1 Models & Generators | 4 | 4 | 0 | 5.74s | **PASS** |
| **Total Automated Tests** | **Comprehensive Full Regression** | **154** | **154** | **0** | **406.12s** | **100% PASS** |

---

## 11. Protected Invariant Audit

All 14 baseline invariants and cryptographic hashes were independently verified:

| Invariant Parameter | Expected Baseline | Measured Value | Verification Source | Status |
| :--- | :---: | :---: | :--- | :---: |
| **Machines** | 10 | 10 | SQLite `machines` table | **PASS** |
| **Sensor Readings** | 40,000 | 40,000 | SQLite `sensor_readings` table | **PASS** |
| **Maintenance Records** | 400 | 400 | SQLite `maintenance_history` table | **PASS** |
| **Alerts** | 5 | 5 | SQLite `alerts` table | **PASS** |
| **Existing Tickets** | 1 | 1 | SQLite `tickets` table (`TCK-2026-001`) | **PASS** |
| **Ticket Proposals in DB** | 0 | 0 | SQLite `ticket_proposals` table | **PASS** |
| **Consumed Tokens in DB** | 0 | 0 | SQLite `consumed_tokens` table | **PASS** |
| **ChromaDB Vectors** | 564 | 564 | SQLite `chroma.sqlite3` | **PASS** |
| **Embedding Dimensions** | 384 | 384 | BAAI/bge-small-en-v1.5 vectors | **PASS** |
| **Source Documents** | 418 | 418 | `corpus_manifest.json` | **PASS** |
| **Canonical Chunks** | 564 | 564 | Ingestion pipeline manifest | **PASS** |
| **Synthetic Placeholders** | 123 | 123 | Synthetic demonstration tags | **PASS** |
| **Isolation Forest Threshold** | 0.0269 | 0.0269 | Frozen model artifact baseline | **PASS** |
| **LSTM Autoencoder Threshold** | 0.901464 | 0.901464 | Frozen model artifact baseline | **PASS** |
| **Defect Images in Manifest** | 600 | 600 | `defect_manifest.json` | **PASS** |
| **Defect Image Classes** | 4 | 4 | ResNet-18 classes | **PASS** |
| **RAG Lockfile SHA-256** | `778fde76...` | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Hash comparison | **PASS** |
| **ResNet Checkpoint SHA-256** | `aac4b1c2...` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | Hash comparison | **PASS** |
| **ResNet Metadata SHA-256** | `e7e95b80...` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | Hash comparison | **PASS** |
| **Base Python Dependency Health** | Clean | "No broken requirements found." (`pip check`) | Package dependency audit | **PASS** |
| **`.venv-rag` Dependency Health** | Clean | "No broken requirements found." (`pip check`) | Package dependency audit | **PASS** |

---

## 12. Security Review & Severity Findings

| Finding ID | Severity | Component & Function | Finding Summary | Impact | Blocks Verdict | Recommended Remediation |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FINDING-P4S6-01` | **INFO** | `approval.py:DevelopmentHumanApprovalAdapter` | The human approval interface currently uses a local mock registry of authorized plant engineers (`DevelopmentHumanApprovalAdapter`) with pre-shared PIN credentials for development and testing. | Suitable for local prototype verification; must not be treated as production enterprise authentication. | **NO** | Disclose missing enterprise SSO / WebAuthn provider as a production deployment prerequisite. |
| `FINDING-P4S6-02` | **INFO** | `tools.py:get_mcp_db_session` | Local database session provider checks `DATABASE_URL` before falling back to `manumind.db`. | Enables automated test suites to run against isolated temporary SQLite databases while preserving authoritative database isolation. | **NO** | Preserved as designed. |
| `FINDING-P4S6-03` | **INFO** | `schemas.py:CreateMaintenanceTicketResponse` | Schema enforces `is_synthetic: bool = True` and operational safety disclaimers reminding personnel that AI recommendations are advisory. | Transparent supervisory governance without misleading operators into treating AI advice as certified engineering directives. | **NO** | Preserved as designed. |

---

## 13. Production Deployment Prerequisites

Before deploying the maintenance ticket creation capability to a live manufacturing facility:
1. **Enterprise Identity Provider Integration:** Replace `DevelopmentHumanApprovalAdapter` with an enterprise identity provider supporting multi-factor authentication (e.g. RMK College SSO, OAuth2/OIDC, or WebAuthn/FIDO2 hardware security keys).
2. **Hardware Security Module (HSM) / KMS:** Store and rotate `MANUMIND_APPROVAL_SECRET_KEY` inside a dedicated Key Management Service (AWS KMS, Azure Key Vault, or HashiCorp Vault) rather than plain environment variables.
3. **Audit Log Export:** Stream `consumed_tokens` and `ticket_proposals` audit records to an immutable, append-only SIEM / compliance log.

---

## 14. Final Acceptance Criteria Evaluation

- [x] `propose_maintenance_ticket` stages proposals without creating active tickets.
- [x] Authoritative ticket service (`create_ticket_with_approval_gate`) is reused safely.
- [x] Cryptographic authorization token is mandatory for `create_maintenance_ticket`.
- [x] Arbitrary `approved_by` strings cannot authorize ticket creation.
- [x] Tokens are cryptographically bound to exact proposal ID and canonical payload hash.
- [x] Short-lived expiration (15 min) and replay protection are persistently enforced.
- [x] Ticket creation and token consumption are transactionally atomic.
- [x] Concurrent creation attempts produce at most one ticket.
- [x] All 154 automated regression tests pass (100%).
- [x] All 14 protected invariants remain 100% intact.
- [x] Reversible Alembic migration implemented and verified.
- [x] Git changes remain completely unstaged.

---

## 15. Final Verdict

**`READY FOR STEP 6.1 INDEPENDENT AUDIT`**
