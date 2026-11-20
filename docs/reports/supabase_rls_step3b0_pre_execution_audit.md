# ManuMind AI — Supabase RLS Remediation: Step 3B.0 — Independent Pre-Execution Safety Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Audit Target:** Pre-Execution Safety Audit of Proposed Alembic Migration Command: `python -m alembic -c backend/alembic.ini upgrade head`  
**Audit Type:** Strictly Read-Only, Independent Pre-Execution Security and Operational Audit  
**Date:** 2026-11-18  
**Final Verdict:** `APPROVED WITH CONDITIONS`

---

## 1. Executive Summary

This independent pre-execution safety audit was conducted prior to authorizing any live database modifications on the Supabase PostgreSQL cluster.

The audit analyzed the exact consequences of executing:
```bash
python -m alembic -c backend/alembic.ini upgrade head
```

### Critical High-Level Findings:
1. **Multi-Migration Execution Detected:** The live Supabase database is currently at revision `1273f18b72a2` (the initial schema from Phase 1). The local repository head is `e4b19082a5c1` (`enable_rls_on_public_tables`). Therefore, running `upgrade head` will **NOT** apply solely the RLS remediation; it will apply **two migrations in sequence**:
   - **Step 1:** `c742f9a1e0b5` (`ticket_proposals and consumed_tokens tables` — Phase 4 Step 6 capability)
   - **Step 2:** `e4b19082a5c1` (`enable standard rls on public tables` — Phase 5 Step 3A remediation)
2. **Schema Safety & Compatibility Confirmed:** Both migrations are syntactically and structurally valid. Foreign key references in `c742f9a1e0b5` to `machines.id`, `alerts.id`, and `tickets.id` align with existing production tables. No destructive operations, table drops, or column alterations occur on existing tables.
3. **Severe Default ACL Security Risk Identified:** Supabase cloud default ACLs (`pg_default_acl`) automatically grant full read, write, delete, and truncate privileges (`arwdDxtm`) on newly created public tables to roles `anon` and `authenticated`. Because `c742f9a1e0b5` creates two new tables (`ticket_proposals` and `consumed_tokens`) and `e4b19082a5c1` only targets the six pre-existing tables (`machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, `tickets`), **the two new tables will be left in Supabase with RLS DISABLED**. This would expose staged ticket proposals and token replay hashes to the public PostgREST API unless remediated.
4. **Backend Role Compatibility Verified:** The backend connects as `postgres`, which is the table owner and possesses `rolbypassrls = True`. Direct SQLAlchemy connections bypass standard RLS completely, ensuring zero query degradation.

---

## 2. Actual Migration Source Review: `e4b19082a5c1`

**File:** `backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`

| Check Item | Target Requirement | Actual Source State | Evaluation |
| :--- | :--- | :--- | :--- |
| **1. Revision ID** | `e4b19082a5c1` | `revision = 'e4b19082a5c1'` | Verified |
| **2. Down Revision** | Pinned to `c742f9a1e0b5` | `down_revision = 'c742f9a1e0b5'` | Verified |
| **3. Upgrade Operations** | Iterates target tables to enable RLS | `ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;` | Verified |
| **4. Downgrade Operations** | Symmetrical reverse disable | `ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;` | Verified |
| **5. Exact Six Tables Included** | 6 flagged tables only | `machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, `tickets` | Verified |
| **6. Unexpected SQL** | Zero arbitrary SQL | Only schema-qualified `ALTER TABLE ... ENABLE/DISABLE RLS` | Verified |
| **7. GRANT Statements** | Zero GRANT statements | 0 occurrences | Verified |
| **8. REVOKE Statements** | Zero REVOKE statements | 0 occurrences | Verified |
| **9. FORCE ROW LEVEL SECURITY** | Zero FORCE RLS statements | 0 occurrences | Verified |
| **10. CREATE POLICY** | Zero CREATE POLICY statements | 0 occurrences (default-deny enforced) | Verified |
| **11. Privilege Restoration** | No broad permission grants | None | Verified |
| **12. Unrelated Schema Changes** | No column/table modifications | None | Verified |

**Comparison with Step 3A Report:** The implementation matches the Step 3A specification with 100% fidelity. There are zero discrepancies.

---

## 3. Pending Ticket-Proposals Migration Review: `c742f9a1e0b5`

**File:** `backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py`  
**Revision:** `c742f9a1e0b5`  
**Down Revision:** `1273f18b72a2`  
**Create Date:** `2026-11-16 21:55:00`

### 3.1 Tables and Schema Objects Created

#### 1. Table `ticket_proposals`
- **Columns:**
  - `id` (`VARCHAR(50)`, Primary Key, NOT NULL, indexed)
  - `machine_id` (`VARCHAR(50)`, NOT NULL, indexed, FK $\rightarrow$ `machines.id`)
  - `alert_id` (`VARCHAR(50)`, NULLABLE, indexed, FK $\rightarrow$ `alerts.id`)
  - `recommendation` (`TEXT`, NOT NULL)
  - `evidence` (`JSON`, NOT NULL)
  - `confidence` (`FLOAT`, NOT NULL)
  - `payload_hash` (`VARCHAR(64)`, NOT NULL, indexed)
  - `status` (`VARCHAR(50)`, NOT NULL, indexed)
  - `created_at` (`TIMESTAMP`, NOT NULL, indexed)
  - `expires_at` (`TIMESTAMP`, NOT NULL, indexed)
  - `approved_by` (`VARCHAR(100)`, NULLABLE)
  - `approved_at` (`TIMESTAMP`, NULLABLE)
  - `token_id` (`VARCHAR(100)`, NULLABLE, UNIQUE, indexed)
  - `ticket_id` (`VARCHAR(50)`, NULLABLE, UNIQUE, indexed, FK $\rightarrow$ `tickets.id`)
- **Foreign Key Constraints:**
  - `ticket_proposals.machine_id` $\rightarrow$ `machines.id`
  - `ticket_proposals.alert_id` $\rightarrow$ `alerts.id`
  - `ticket_proposals.ticket_id` $\rightarrow$ `tickets.id`
- **Unique Constraints:**
  - `ticket_proposals_token_id_key` (`token_id`)
  - `ticket_proposals_ticket_id_key` (`ticket_id`)

#### 2. Table `consumed_tokens`
- **Columns:**
  - `jti` (`VARCHAR(100)`, Primary Key, NOT NULL, indexed)
  - `proposal_id` (`VARCHAR(50)`, NOT NULL, indexed, FK $\rightarrow$ `ticket_proposals.id`)
  - `approver_id` (`VARCHAR(100)`, NOT NULL)
  - `consumed_at` (`TIMESTAMP`, NOT NULL, indexed)
  - `token_exp` (`TIMESTAMP`, NOT NULL)
- **Foreign Key Constraints:**
  - `consumed_tokens.proposal_id` $\rightarrow$ `ticket_proposals.id`

### 3.2 Safety and Impact Assessment of `c742f9a1e0b5`
- **Existing Table Alterations:** None. No columns added, dropped, or modified on existing tables (`machines`, `alerts`, `tickets`, `sensor_readings`, `maintenance_history`).
- **Data Migration / Mutation:** None. No `INSERT`, `UPDATE`, or `DELETE` statements.
- **Destructive Operations:** None.
- **Reversibility:** Downgrade cleanly drops `consumed_tokens` first, then `ticket_proposals`, honoring foreign key hierarchy.
- **Integrity with Existing Data:** All foreign key parent tables (`machines`, `alerts`, `tickets`) exist in the live database with matching primary key data types (`VARCHAR(50)`).
- **Security Deficit:** The migration does not contain `ENABLE ROW LEVEL SECURITY` for `ticket_proposals` or `consumed_tokens`.

---

## 4. Alembic DAG and Execution Sequence

### 4.1 DAG Topology
```
[ <base> ]
    │
    ▼
[ 1273f18b72a2 ]  <-- Current Live Supabase Revision (initial_tables)
    │
    ▼
[ c742f9a1e0b5 ]  <-- Pending Migration (ticket_proposals & consumed_tokens)
    │
    ▼
[ e4b19082a5c1 ]  <-- Local Repository Head (enable standard rls on public tables)
```

- **Live Database Active Revision:** `1273f18b72a2`
- **Repository Head:** `e4b19082a5c1`
- **Number of Branches / Multiple Heads:** 0 (strictly 1 head)
- **Missing or Duplicate Revisions:** None

### 4.2 Exact Execution Sequence
When `python -m alembic -c backend/alembic.ini upgrade head` is invoked, Alembic will execute the following operations in exact sequential order:

1. **Transaction 1 — Revision `c742f9a1e0b5`:**
   - `CREATE TABLE ticket_proposals (...);`
   - `CREATE INDEX ... ON ticket_proposals (...);` (9 indices)
   - `CREATE TABLE consumed_tokens (...);`
   - `CREATE INDEX ... ON consumed_tokens (...);` (3 indices)
   - `UPDATE public.alembic_version SET version_num = 'c742f9a1e0b5';`
2. **Transaction 2 — Revision `e4b19082a5c1`:**
   - `ALTER TABLE public.machines ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE public.sensor_readings ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE public.maintenance_history ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;`
   - `UPDATE public.alembic_version SET version_num = 'e4b19082a5c1';`

---

## 5. Live Database State Verification (Read-Only)

Live database inspection via the Supabase session pooler confirmed the following:

| Catalog Attribute | Queried Value | Security / Operational Implication |
| :--- | :--- | :--- |
| **`current_user`** | `postgres` | Matches backend connecting credentials |
| **`session_user`** | `postgres` | Session pooler does not demote user role |
| **`rolsuper`** | `False` | Tenant admin in Supabase managed cloud |
| **`rolbypassrls`** | `True` | Direct backend queries completely bypass RLS |
| **`rolcanlogin`** | `True` | Direct authentication permitted |
| **`public.alembic_version`** | `['1273f18b72a2']` | Exactly 1 pending step before RLS migration |
| **`ticket_proposals` exists?** | `False` | Table does not exist yet on Supabase |
| **`consumed_tokens` exists?** | `False` | Table does not exist yet on Supabase |
| **`tickets` constraints** | `tickets_pkey` (id), `tickets_alert_id_key` (alert_id UNIQUE), `tickets_alert_id_fkey` | Clean FK references available for `c742f9a1e0b5` |
| **Current RLS State (6 tables)**| `rls_enabled = False` on all 6 | Remediation has not yet been applied |
| **Current Force RLS (6 tables)**| `force_rls_enabled = False` on all 6 | Table owner bypass preserved |
| **Table Owner (6 tables)** | `postgres` on all 6 | Backend user owns all domain tables |

---

## 6. Database Schema and Grant Baseline Inspection

Inspection of `pg_default_acl` revealed Supabase's default access control configuration:
```json
{
  "defaclrole": "postgres",
  "schema_name": "public",
  "defaclobjtype": "r",
  "defaclacl": "{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}"
}
```

### Risk Implication:
When revision `c742f9a1e0b5` executes `CREATE TABLE ticket_proposals` and `CREATE TABLE consumed_tokens`, PostgreSQL automatically applies this default ACL rule. Consequently:
- `anon` will be granted `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`.
- `authenticated` will be granted identical full privileges.
- Because `e4b19082a5c1` does not include `ticket_proposals` or `consumed_tokens` in its `TARGET_TABLES`, these two tables will remain with `relrowsecurity = False`.
- **Outcome:** PostgREST will expose these two tables to the public internet with full anonymous read/write capabilities unless RLS is enabled on them.

---

## 7. Backend Role Compatibility and Query Safety

1. **Role Identification:** The backend application and Alembic connect to Supabase via `DATABASE_URL` as user `postgres`.
2. **RLS Bypass Guarantee:** PostgreSQL documentation guarantees that roles with `rolbypassrls = True` bypass all row-level security checks unless `FORCE ROW LEVEL SECURITY` is applied. Live queries confirmed `postgres.rolbypassrls = True`.
3. **No Force RLS Invariant:** Both `upgrade()` and `downgrade()` in `e4b19082a5c1` use standard `ENABLE ROW LEVEL SECURITY`. They do not execute `FORCE ROW LEVEL SECURITY`. Therefore, backend queries executed as `postgres` will never be restricted or filtered by RLS.
4. **`alembic_version` Access:** Alembic requires read and write access to `public.alembic_version`. Because Alembic connects as `postgres`, enabling standard RLS on `alembic_version` will not impair future Alembic migrations.
5. **Assumptions Requiring Live Verification:**
   - Verified that the Supabase transaction pooler (port 6543) or session pooler (port 5432) does not reset `rolbypassrls` during connection pooling.
   - Live query non-regression must be verified immediately post-migration via `backend/verify_migration.py`.

---

## 8. Test Safety and Verification Command Review

Proposed verification tools were audited for database safety:

| Command / Script | Classification | Mutates State? | Safe for Production? | Operational Context |
| :--- | :--- | :--- | :--- | :--- |
| `python backend/test_connection.py` | **SAFE READ-ONLY** | No | **YES** | Runs `SELECT 1` and `SELECT version()`. Zero mutations. |
| `python backend/verify_migration.py` | **SAFE READ-ONLY** | No | **YES** | Connects to SQLite (`?mode=ro`) and Supabase via SELECT queries, checking counts, PK ranges, aggregates, and sequence metadata. Zero sequence numbers consumed. |
| `pytest backend/tests/test_mcp_defect_image.py` | **SAFE WITH ISOLATED FIXTURES** | No | **YES (Isolated)** | Uses mock defect images in temp directories. No database writes. |
| `pytest backend/tests/test_mcp_maintenance_history.py` | **SAFE READ-ONLY (LOCAL SQLITE)** | No | **YES (Local)** | Connects to local `manumind.db` (SQLite). Never connects to Supabase. |
| `pytest backend/tests/test_mcp_manufacturing_tools.py` | **SAFE READ-ONLY (LOCAL SQLITE)** | No | **YES (Local)** | Connects to local `manumind.db` (SQLite). Never connects to Supabase. |
| `pytest backend/tests/test_mcp_rag_retrieval.py` | **SAFE WITH ISOLATED FIXTURES** | No | **YES (Local)** | Tests isolated ChromaDB subprocess bridge. |
| `pytest backend/tests/test_mcp_server_skeleton.py` | **SAFE READ-ONLY** | No | **YES (Local)** | Tests MCP protocol schemas and tool declarations. |
| `pytest backend/tests/test_mcp_ticket_creation.py` | **SAFE ONLY WITH TEST DATABASE** | **YES (in test DB)** | **NOT SAFE FOR PRODUCTION** | Creates in-memory SQLite tables, populates alerts, consumes tokens, and generates test tickets. **Must NEVER be executed against production Supabase.** |

### Recommended Safe Verification Sequence:
1. **Pre-Execution:** `python backend/test_connection.py`
2. **Execution:** `python -m alembic -c backend/alembic.ini upgrade head`
3. **Catalog Verification:** Read-only query against `pg_class.relrowsecurity` and `public.alembic_version`.
4. **Data Fidelity Verification:** `python backend/verify_migration.py`
5. **PostgREST Security Verification:** Anonymous REST probe (Section 9).
6. **Local MCP Suite:** `pytest backend/tests/test_mcp_*.py` executed strictly in a test environment with `DATABASE_URL` unlinked from Supabase.

---

## 9. PostgREST Security Verification Plan

This test plan defines how to verify anonymous API access post-migration without exposing secrets or credentials.

### 9.1 Database Access Personas

| Persona | Connection Medium | Database Role | Bypass RLS? | Expected Access Under Default-Deny |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Engine** | TCP Port 5432 / Pooler | `postgres` | **YES** (`rolbypassrls = True`) | Full CRUD across all tables. Zero degradation. |
| **Public PostgREST API** | HTTPS REST / GraphQL | `anon` | **NO** (`rolbypassrls = False`) | Default-Deny: Empty arrays `[]` on SELECT; 401/403 on writes. |
| **Authenticated Users** | HTTPS REST / GraphQL | `authenticated` | **NO** (`rolbypassrls = False`) | Default-Deny: Empty arrays `[]` on SELECT; 401/403 on writes. |
| **Administrative API** | HTTPS REST / GraphQL | `service_role` | **YES** (Supabase internal) | Full administrative access. **Must be kept strictly secret.** |

### 9.2 Expected Behavior per Table After Migration

| Table Name | Anonymous `GET /rest/v1/{table}` | Anonymous `POST /rest/v1/{table}` | Status / Notes |
| :--- | :--- | :--- | :--- |
| `public.machines` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.sensor_readings` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.alembic_version` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.maintenance_history` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.alerts` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.tickets` | `200 OK` $\rightarrow$ `[]` (0 rows) | `401/403 Unauthorized` | Secured by Default-Deny |
| `public.ticket_proposals` | `200 OK` $\rightarrow$ `[...]` (ROWS EXPOSED) | `201 Created` (UNPROTECTED) | **SECURITY VULNERABILITY (RLS not enabled)** |
| `public.consumed_tokens` | `200 OK` $\rightarrow$ `[...]` (ROWS EXPOSED) | `201 Created` (UNPROTECTED) | **SECURITY VULNERABILITY (RLS not enabled)** |

---

## 10. Git Working Tree State and File Preservation

- **Active Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Files:** 0
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`, preserved from Phase 4)
- **Untracked Deliverables (Step 3A & Step 3B.0):**
  - `backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`
  - `docs/reports/supabase_rls_step3a_migration_preparation.md`
  - `docs/reports/supabase_rls_step3a_migration_preparation.json`
  - `docs/reports/supabase_rls_step3b0_pre_execution_audit.md` (this report)
  - `docs/reports/supabase_rls_step3b0_pre_execution_audit.json`
- **Untracked Historical Work Preserved:** All 18 previously existing files/directories remain completely untouched.

---

## 11. Unresolved Risks

1. **Risk 1 — Dual Migration Execution:** Running `alembic upgrade head` applies both `c742f9a1e0b5` and `e4b19082a5c1`. This creates two new database tables in addition to enabling RLS on the original six tables.
2. **Risk 2 — Exposure of `ticket_proposals` and `consumed_tokens`:** Due to Supabase default ACLs, newly created tables grant `ALL` privileges to `anon` and `authenticated`. Because `e4b19082a5c1` was scoped only to the six tables flagged in the Step 1/2 audits, `ticket_proposals` and `consumed_tokens` will be created with RLS disabled, creating an immediate security vulnerability on PostgREST.
3. **Risk 3 — Test Suite Contamination:** Executing `pytest backend/tests/test_mcp_ticket_creation.py` without environment isolation risks polluting persistent database state. It must only be run against in-memory SQLite.

---

## 12. Final Verdict & Authorization Conditions

### Verdict: **`APPROVED WITH CONDITIONS`**

### Justification:
The migration scripts and execution sequence are fully understood, syntactically verified, and schema-compatible with zero risk of production data destruction. However, because running `upgrade head` creates `ticket_proposals` and `consumed_tokens` without enabling RLS on them, proceeding to live execution without addressing this gap would introduce new security findings.

### Mandatory Pre-Conditions for Step 3B Live Execution:
1. **Explicit Human Authorization for Dual Migration:** The engineering team must acknowledge and authorize that `upgrade head` will apply `c742f9a1e0b5` (creating `ticket_proposals` and `consumed_tokens`) immediately prior to `e4b19082a5c1`.
2. **RLS Coverage Remediation for New Tables:** Either:
   - *Option A (Recommended):* Amend `backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py` to include `ticket_proposals` and `consumed_tokens` in `TARGET_TABLES` (raising target tables from 6 to 8), ensuring all public tables are secured in the same migration step; OR
   - *Option B:* Authorize an immediate follow-up migration revision to enable standard RLS on `ticket_proposals` and `consumed_tokens` immediately after `e4b19082a5c1`.
3. **Test Suite Isolation Mandate:** Verification following live execution must strictly use read-only scripts (`test_connection.py`, `verify_migration.py`, read-only SQL queries). Mutating pytest suites (`test_mcp_ticket_creation.py`) must be executed solely in a local, isolated environment with an explicit SQLite database URL.

---

## 13. Audit Sign-Off
- **Auditor:** Antigravity Independent Security and Quality Auditor
- **Status:** Awaiting explicit human authorization on pre-conditions before live execution.
