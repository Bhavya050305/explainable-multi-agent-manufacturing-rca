# ManuMind AI — Supabase RLS Remediation: Step 3A — Controlled Migration Preparation and Security Validation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main`  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3A)  
**Date:** 2026-11-18  
**Final Verdict:** `READY FOR MIGRATION REVIEW`

---

## 1. Executive Summary

This milestone executes **Step 3A (Controlled Migration Preparation and Security Validation)** to address the six Supabase Security Advisor findings.

A dedicated, version-controlled Alembic migration was prepared and statically verified to enable standard PostgreSQL Row Level Security (RLS) on all six flagged tables:
1. `public.machines`
2. `public.sensor_readings`
3. `public.alembic_version`
4. `public.maintenance_history`
5. `public.alerts`
6. `public.tickets`

In accordance with strict safety mandates:
- **Zero changes were made to the live Supabase database.**
- **No `alembic upgrade`, `alembic downgrade`, or raw DDL was executed.**
- **The migration contains exactly six standard `ENABLE ROW LEVEL SECURITY` statements in `upgrade()` and six corresponding `DISABLE ROW LEVEL SECURITY` statements in `downgrade()`.**
- **Strict grant and revoke protection is enforced:** Zero `GRANT` or `REVOKE` statements exist in the migration. Broad API permissions are not restored or altered.
- **`FORCE ROW LEVEL SECURITY` is strictly avoided.**
- **No permissive or custom RLS policies are created**, allowing PostgreSQL's default-deny rule to secure the PostgREST Data API while preserving backend compatibility for the connecting `postgres` role (`rolbypassrls = True`).

---

## 2. Preflight Audit Results

Prior to authoring the migration, repository and migration-chain preflight checks were conducted:

| Preflight Check | Target Specification | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Git Branch** | `main` | `main` | **MATCH** |
| **HEAD Commit** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | **MATCH** |
| **Tracked Changes** | `backend/app/models/__init__.py` | Preserved (uncommitted) | **PRESERVED** |
| **Untracked Artifacts** | Phase 4/5 test files, reports, migrations | Preserved (uncommitted) | **PRESERVED** |
| **Existing Migrations on Disk** | 2 files in `backend/alembic/versions/` | `1273f18b72a2_initial_tables.py`<br>`c742f9a1e0b5_ticket_proposals.py` | **VERIFIED** |
| **Alembic Repository Head** | Single head: `c742f9a1e0b5` | `c742f9a1e0b5 (head)` | **MATCH** |
| **Live Database Active Revision** | Read-only probe on `alembic_version` | `1273f18b72a2` | **VERIFIED** |
| **Existing RLS in Migrations** | Zero existing RLS statements | 0 occurrences across all migration files | **VERIFIED** |
| **Preflight Stop Conditions** | None triggered | No branches, duplicate revisions, or missing parents | **PASS** |

*Note on Revision State:* The live Supabase database currently sits at revision `1273f18b72a2`. The repository migration history defines revision `c742f9a1e0b5` (ticket proposals). By pinning the new migration's `down_revision = 'c742f9a1e0b5'`, a completely continuous, single-path migration DAG is maintained:  
`<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1`.

---

## 3. Previous and New Alembic Revisions

- **Previous Migration Revision:** `c742f9a1e0b5`  
  *File:* [`backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py)  
  *Description:* `ticket_proposals and consumed_tokens tables`  
  *Down Revision:* `1273f18b72a2`

- **New Migration Revision:** `e4b19082a5c1`  
  *File:* [`backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py)  
  *Description:* `enable standard rls on public tables`  
  *Down Revision:* `c742f9a1e0b5`

---

## 4. Six-Table RLS Migration Summary

The migration targets strictly the six tables in schema `public` flagged by Supabase Security Advisor:

| Table Name | Schema | Owner | Purpose in ManuMind AI | RLS Action (Upgrade) |
| :--- | :--- | :--- | :--- | :--- |
| **`machines`** | `public` | `postgres` | Industrial machine registry and metadata | `ENABLE ROW LEVEL SECURITY` |
| **`sensor_readings`** | `public` | `postgres` | High-frequency telemetry (40,000 records) | `ENABLE ROW LEVEL SECURITY` |
| **`alembic_version`** | `public` | `postgres` | Internal migration tracking metadata | `ENABLE ROW LEVEL SECURITY` |
| **`maintenance_history`** | `public` | `postgres` | Historical machine maintenance & incident logs | `ENABLE ROW LEVEL SECURITY` |
| **`alerts`** | `public` | `postgres` | Predictive anomaly and failure risk alerts | `ENABLE ROW LEVEL SECURITY` |
| **`tickets`** | `public` | `postgres` | Authorised maintenance work orders | `ENABLE ROW LEVEL SECURITY` |

---

## 5. Upgrade and Downgrade Design

### 5.1 Upgrade Design
The `upgrade()` function executes standard `ENABLE ROW LEVEL SECURITY` on each table using fixed, explicit schema-qualified identifiers:
```python
TARGET_TABLES = [
    "machines",
    "sensor_readings",
    "alembic_version",
    "maintenance_history",
    "alerts",
    "tickets",
]

def upgrade() -> None:
    for table_name in TARGET_TABLES:
        op.execute(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;")
```

### 5.2 Downgrade Design
The `downgrade()` function symmetrically reverses the operation by executing `DISABLE ROW LEVEL SECURITY` in reverse order:
```python
def downgrade() -> None:
    for table_name in reversed(TARGET_TABLES):
        op.execute(f"ALTER TABLE public.{table_name} DISABLE ROW LEVEL SECURITY;")
```

### 5.3 Downgrade Safety Warning
> [!WARNING]
> Downgrading disables RLS and reopens the previous RLS-disabled exposure for roles with existing table privileges (`anon`, `authenticated`). It must only be executed with explicit authorization and a security review.

---

## 6. Strict Grant and Revoke Protection

In strict adherence to Section 5 and Section 6 instructions:

1. **No `GRANT` Statements:**  
   The migration does **NOT** contain any statement resembling:
   ```sql
   GRANT ALL ON public.alembic_version TO anon, authenticated;
   GRANT ALL ON public.machines TO anon, authenticated;
   ```
   Broad API privileges are permanently excluded from restoration.
2. **No `REVOKE` Statements:**  
   To prevent unexpected schema side-effects or permission state mutations during RLS remediation, the migration makes **zero SQL grant changes**. The existing grant baseline is preserved unchanged.
3. **Symmetry:**  
   Because `upgrade()` makes no grant changes, `downgrade()` also makes zero grant changes.

---

## 7. Security Architecture & Backend Compatibility Reasoning

### 7.1 Default-Deny RLS
Under PostgreSQL's security model:
- When RLS is enabled on a table, all access requests from non-exempt roles are evaluated against the table's RLS policies.
- If **no policies exist** on the table, PostgreSQL applies an automatic **default-deny**:
  - `SELECT`: Returns 0 rows (empty result set).
  - `INSERT` / `UPDATE` / `DELETE`: Fails with an RLS permission denied error.
- Therefore, enabling RLS without creating any policies completely seals the PostgREST Data API for `anon` and `authenticated` roles without needing redundant custom deny policies.

### 7.2 Backend Compatibility via `BYPASSRLS`
The backend connects via SQLAlchemy using the connection user `postgres`:
- **Catalog Fact:** In Supabase, the `postgres` role has `rolbypassrls = True`.
- **Table Ownership:** The `postgres` role is the explicit owner (`tableowner = postgres`) of all six tables.
- **Result:** Because `postgres` has `BYPASSRLS`, it completely bypasses row-level security evaluations. Direct SQLAlchemy queries, FastAPI dependency sessions (`get_db`), and background ML runners operate with 100% throughput and zero permission friction.

### 7.3 FORCE ROW LEVEL SECURITY Prohibition
Standard RLS does not apply to table owners or roles with `BYPASSRLS`. `FORCE ROW LEVEL SECURITY` (`ALTER TABLE ... FORCE ROW LEVEL SECURITY;`) strips the table owner's bypass privilege and forces policy evaluation on the owner.  
**Prohibition:** `FORCE ROW LEVEL SECURITY` is **strictly excluded** from both `upgrade()` and `downgrade()`.

---

## 8. Supabase Auth Considerations

The previous audits confirmed:
- Supabase Auth (GoTrue) is **not implemented** in the repository.
- There are no user sessions, JWT claims, or `auth.uid()` dependencies in the backend.
- Designing speculative user-ownership policies (e.g., `auth.uid() = user_id`) would be artificial and untestable.
- Authenticated user policies are formally deferred to Phase 6 (Frontend and User Role Architecture).

---

## 9. Static Validation Results

Static analysis and AST inspection were executed using [`scratch/validate_step3a.py`](file:///C:/Users/PR%20BHAYA%20SREE/.gemini/antigravity/brain/f1d66973-caec-4f3f-8429-74660421600e/scratch/validate_step3a.py):

```text
=== 1. STATIC CODE ANALYSIS ===
AST parse successful: True
Prohibited check [GRANT]: 0 occurrences
Prohibited check [REVOKE]: 0 occurrences
Prohibited check [FORCE]: 0 occurrences
Prohibited check [POLICY]: 0 occurrences
Prohibited check [DROP TABLE]: 0 occurrences
Prohibited check [CREATE TABLE]: 0 occurrences
All prohibited code checks PASSED.
Revision metadata and target tables verified: SUCCESS

=== 2. LIVE DATABASE INTEGRITY (CONFIRM UNCHANGED) ===
 - alembic_version: rls_enabled=False
 - alerts: rls_enabled=False
 - machines: rls_enabled=False
 - maintenance_history: rls_enabled=False
 - sensor_readings: rls_enabled=False
 - tickets: rls_enabled=False
All 6 tables in live DB remain rls_enabled=False (Zero mutations confirmed).
```

### Alembic DAG Validation
```powershell
python -m alembic -c backend/alembic.ini heads
# Output: e4b19082a5c1 (head)

python -m alembic -c backend/alembic.ini history
# Output:
# c742f9a1e0b5 -> e4b19082a5c1 (head), enable standard rls on public tables
# 1273f18b72a2 -> c742f9a1e0b5, ticket_proposals and consumed_tokens tables
# <base> -> 1273f18b72a2, initial_tables
```

---

## 10. Git Working-Tree Preservation

| Metric | Preflight Value | Post-Step 3A Value | Status |
| :--- | :---: | :---: | :---: |
| **Git Branch** | `main` | `main` | Preserved |
| **HEAD Commit** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Preserved |
| **Staged Files** | 0 | 0 | Preserved |
| **Modified Tracked Files** | 1 (`backend/app/models/__init__.py`) | 1 (`backend/app/models/__init__.py`) | Preserved |
| **New Migration File** | None | 1 (`e4b19082a5c1_enable_rls_on_public_tables.py`) | Created |
| **New Report Files** | None | 2 (`step3a_migration_preparation.md/.json`) | Created |
| **Repository Safety** | Zero commits, pushes, stashes, or resets executed | Verified | **CLEAN** |

---

## 11. Exact Files Created

1. **Alembic Migration:**  
   [`backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py)
2. **Markdown Audit Report:**  
   [`docs/reports/supabase_rls_step3a_migration_preparation.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3a_migration_preparation.md)
3. **Structured JSON Audit Report:**  
   [`docs/reports/supabase_rls_step3a_migration_preparation.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3a_migration_preparation.json)

---

## 12. Explicit Confirmation: Live Database Unchanged

> [!IMPORTANT]
> **Live Database Integrity Confirmation:**  
> A read-only verification query against `pg_tables` in the live Supabase instance confirmed that **all six tables remain at `rowsecurity = False`**. No DDL was executed, no migration was applied, and no live database permissions were altered. The migration exists solely as a validated source file on disk awaiting authorized execution.

---

## 13. Remaining Risks & Next Steps

### Remaining Considerations
1. **Live Execution Prerequisite (Step 3B):** When executing Step 3B (`alembic upgrade head`), Alembic will first apply `c742f9a1e0b5` (creating `ticket_proposals` and `consumed_tokens`), and then immediately apply `e4b19082a5c1` (enabling RLS on the six public tables). Both operations must be verified in a single controlled execution turn.
2. **PostgREST Re-indexing:** Once RLS is enabled on the live database, PostgREST will reload its schema cache within seconds and immediately enforce default-deny for all `anon` requests.

### Next Step
Await explicit human authorization to proceed to **Step 3B — Controlled Supabase RLS Migration Execution**.

---

## 14. Final Verdict

### Final Verdict: `READY FOR MIGRATION REVIEW`

**Summary:**  
The migration file `e4b19082a5c1_enable_rls_on_public_tables.py` satisfies all structural, security, and grant-protection requirements. Static AST and DAG checks passed with 100% compliance. Zero live database mutations occurred. The task is complete and ready for human review.
