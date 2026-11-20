# ManuMind AI — Supabase RLS Remediation: Step 3C.1 Least-Privilege Migration Preparation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Live Revision:** `1273f18b72a2`  
**Current Head:** `f3a9082b1c42`  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3C.1)  
**Date:** 2026-11-18  
**Audit Target:** Preparation and Static Validation of Least-Privilege Privilege-Hardening Migration  
**Final Verdict:** `READY FOR STEP 3C.2 INDEPENDENT MIGRATION REVIEW`

---

## 1. Executive Summary

In accordance with the approved Step 3C.0 solution architecture, a dedicated least-privilege privilege-hardening Alembic migration has been authored and statically validated.

The migration closes the database-level privilege gap identified during the security review:
1. **TRUNCATE Vulnerability Eliminated:** PostgreSQL Row Level Security (RLS) does not apply to `TRUNCATE`. The new migration revokes all table-level privileges (`arwdDxtm`) from `anon` and `authenticated` across all eight application tables in schema `public`.
2. **Sequence Counter Hardening:** Revokes sequence privileges (`rwU`: USAGE, SELECT, UPDATE) on both public sequences from `anon` and `authenticated`, preventing sequence enumeration or exhaustion attacks.
3. **Future Default Privilege Hardening:** Alters default privileges for objects created by role `postgres` in schema `public`, preventing future tables and sequences from inheriting automatic grants to API roles.
4. **Security-Preserving Fail-Closed Downgrade:** Implements a strict fail-closed `downgrade()` that raises `NotImplementedError`, preventing automated restoration of broad privileges (specifically prohibiting `GRANT ALL`).
5. **Zero Live Database Mutations:** Read-only inspection verified that the live Supabase database remains strictly at baseline revision `1273f18b72a2`. No DDL, `upgrade`, `downgrade`, or data modifications were executed.
6. **Transaction Atomicity Verified:** Verified that the entire migration chain (`c742f9a1e0b5` $\rightarrow$ `e4b19082a5c1` $\rightarrow$ `f3a9082b1c42`) executes inside a single atomic PostgreSQL transaction.

---

## 2. Baseline Verification

Preflight checks confirmed repository and live database baselines:

| Verification Item | Target Requirement | Actual Verified State | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Tree** | Branch `main`, HEAD `a1e7e77` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Confirmed |
| **Live Database Active Revision** | `1273f18b72a2` | `['1273f18b72a2']` (query on `public.alembic_version`) | Confirmed |
| **Alembic Heads Prior to Edit** | Sole head `e4b19082a5c1` | `e4b19082a5c1 (head)` verified | Confirmed |
| **Alembic DAG Ancestry** | Linear single chain | `<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1` | Confirmed |
| **RLS Scope in `e4b19082a5c1`** | Exactly 8 public tables | Verified: `machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, `tickets`, `ticket_proposals`, `consumed_tokens` | Confirmed |
| **Preceding Migrations** | Untouched | `c742f9a1e0b5` and `e4b19082a5c1` strictly unmodified | Confirmed |

---

## 3. New Migration Specification: `f3a9082b1c42`

**File:** [f3a9082b1c42_harden_least_privilege_grants.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/f3a9082b1c42_harden_least_privilege_grants.py)  
**Revision:** `f3a9082b1c42`  
**Down Revision:** `e4b19082a5c1`  
**Create Date:** `2026-11-18 21:20:00`

### 3.1 Upgrade Operations
The migration defines four explicit schema-qualified operations:

```python
def upgrade() -> None:
    # 1. Revoke all table privileges on all 8 tables from API roles
    tables_list = ", ".join(TARGET_TABLES)
    op.execute(f"REVOKE ALL ON TABLE {tables_list} FROM anon, authenticated;")

    # 2. Revoke all sequence privileges on both sequences from API roles
    sequences_list = ", ".join(TARGET_SEQUENCES)
    op.execute(f"REVOKE ALL ON SEQUENCE {sequences_list} FROM anon, authenticated;")

    # 3. Alter future default table privileges in schema public for role postgres
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON TABLES FROM anon, authenticated;"
    )

    # 4. Alter future default sequence privileges in schema public for role postgres
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON SEQUENCES FROM anon, authenticated;"
    )
```

### 3.2 Exact Scope Targets

#### 1. Eight Schema-Qualified Tables (`TARGET_TABLES`):
1. `public.machines`
2. `public.sensor_readings`
3. `public.alembic_version`
4. `public.maintenance_history`
5. `public.alerts`
6. `public.tickets`
7. `public.ticket_proposals`
8. `public.consumed_tokens`

#### 2. Two Schema-Qualified Sequences (`TARGET_SEQUENCES`):
1. `public.sensor_readings_id_seq`
2. `public.maintenance_history_id_seq`

#### 3. Default Privileges:
- Creator Role: `postgres`
- Schema: `public`
- Object Types: `TABLES` and `SEQUENCES`
- Target Roles: `anon`, `authenticated`

### 3.3 Scope Restrictions & Security Invariants
- **Privilege Integrity:** Zero privileges are revoked from `postgres` or `service_role`.
- **Ownership Invariance:** Table and sequence ownership remain with `postgres`.
- **No Broad Restorations:** Zero `GRANT` statements exist in executable code.
- **No RLS / Policy Interferences:** Zero `FORCE ROW LEVEL SECURITY`, `CREATE POLICY`, or `DROP POLICY` statements.
- **No Schema Mutations:** Zero tables or sequences are dropped, altered, or created.

---

## 4. Downgrade Safety Design

In alignment with least-privilege security mandates, automated rollback is intentionally blocked:

```python
def downgrade() -> None:
    """
    Downgrade is intentionally blocked to protect the least-privilege security baseline.

    SECURITY WARNING:
    Automated rollback must NEVER restore broad privileges to 'anon' or 'authenticated',
    as broad permissions reintroduce critical database-level vulnerabilities (including
    unrestricted TRUNCATE capabilities).

    Any emergency restoration requires a separately authorized, manually reviewed
    administrative procedure based on the exact original ACL baseline.
    """
    raise NotImplementedError(
        "Automated downgrade of least-privilege privilege hardening is prohibited. "
        "Restoring broad table privileges reintroduces critical security "
        "vulnerabilities (including TRUNCATE exposure for anon and authenticated). "
        "Any emergency privilege restoration must be performed via a separately "
        "authorized DBA procedure."
    )
```

### Rationale:
- Restoring `GRANT ALL` on tables would reintroduce unrestricted `TRUNCATE` capabilities to API roles.
- Least-privilege privilege hardening is an architectural security invariant. In the event of an operational need to restore specific read-only access, an authorized DBA must execute a documented, selective grant procedure rather than an automated bulk restoration.

---

## 5. Transaction and Unified-Upgrade Analysis

An independent inspection of `backend/alembic/env.py`, `backend/alembic.ini`, and all three pending migration files confirmed the transaction architecture for `python -m alembic -c backend/alembic.ini upgrade head`:

```
[ PostgreSQL Transaction BEGIN ]
  ├── 1. Apply c742f9a1e0b5: Create ticket_proposals & consumed_tokens tables
  ├── 2. Apply e4b19082a5c1: Enable standard RLS on all eight tables
  ├── 3. Apply f3a9082b1c42: Revoke table/sequence privileges & alter default privileges
  └── 4. Update public.alembic_version to 'f3a9082b1c42'
[ PostgreSQL Transaction COMMIT ]
```

### Verified Transaction Properties:
1. **Transactional DDL Support:** PostgreSQL natively supports transactional DDL. `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE ENABLE ROW LEVEL SECURITY`, `REVOKE`, and `ALTER DEFAULT PRIVILEGES` are fully transactional.
2. **Alembic Context Configuration:** In `backend/alembic/env.py`, the entire migration sequence is enclosed within `with context.begin_transaction(): context.run_migrations()`.
3. **No Intermediate Commits:** Neither `alembic.ini` nor `env.py` sets `transaction_per_migration`, and none of the three migration scripts contains explicit `commit()` or autocommit flags.
4. **Guaranteed Atomic Rollback:** If any statement in any of the three migrations fails, PostgreSQL will automatically roll back the entire transaction. The live database will remain cleanly at baseline revision `1273f18b72a2` with zero partial schema modifications.
5. **Zero Window of Exposure:** Applying all three migrations in a single upgrade run guarantees that the tables are created, RLS is enabled, and privileges are hardened simultaneously within the same atomic transaction.

---

## 6. Static Validation Results

Static analysis was performed using AST inspection, compilation checks, and the Alembic CLI:

| Check Category | Target Invariant | Static Check Result | Status |
| :--- | :--- | :--- | :--- |
| **Python Syntax Compilation** | Clean compilation | `py_compile.compile()` passed with 0 errors | **PASSED** |
| **AST Tree Parsing** | Valid AST syntax tree | AST parsed cleanly with 0 warnings | **PASSED** |
| **Revision Identifier** | `f3a9082b1c42` | Matches `revision = 'f3a9082b1c42'` | **PASSED** |
| **Down Revision Identifier** | `e4b19082a5c1` | Matches `down_revision = 'e4b19082a5c1'` | **PASSED** |
| **Table Target Count** | Exactly 8 public tables | `len(TARGET_TABLES) == 8` (exact match) | **PASSED** |
| **Sequence Target Count** | Exactly 2 public sequences | `len(TARGET_SEQUENCES) == 2` (exact match) | **PASSED** |
| **Default Privilege Scope** | Role `postgres`, Schema `public` | Explicitly targets `postgres` in `public` | **PASSED** |
| **Prohibited Tokens Scan** | 0 `GRANT ALL`, `FORCE RLS`, `CREATE POLICY` in code | 0 found | **PASSED** |
| **Downgrade Exception** | Raises `NotImplementedError` | Verified raises `NotImplementedError` | **PASSED** |
| **Preceding Migrations** | `c742f9a1e0b5` & `e4b19082a5c1` untouched | Verified untouched | **PASSED** |
| **Alembic Heads** | Exactly 1 head | `f3a9082b1c42 (head)` | **PASSED** |
| **Alembic DAG Linearity** | Continuous linear history | `<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1 -> f3a9082b1c42 (head)` | **PASSED** |
| **Live Database State** | No mutations | Active revision remains `['1273f18b72a2']` | **PASSED** |

---

## 7. Git Preservation Audit

- **Active Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Changes:** 0
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`, preserved from Phase 4)
- **New Migration Created:** `backend/alembic/versions/f3a9082b1c42_harden_least_privilege_grants.py`
- **Untracked Historical Work:** All 20 previously existing untracked files/directories remain intact.
- **Zero Files Staged, Committed, or Discarded.**

---

## 8. Deliverables Generated

- **Alembic Migration Script:**  
  [f3a9082b1c42_harden_least_privilege_grants.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/f3a9082b1c42_harden_least_privilege_grants.py)
- **Comprehensive Audit Report (Markdown):**  
  [supabase_rls_step3c1_migration_preparation.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c1_migration_preparation.md)
- **Structured Audit Report (JSON):**  
  [supabase_rls_step3c1_migration_preparation.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c1_migration_preparation.json)

---

## 9. Final Verdict & Next Steps

### Verdict: **`READY FOR STEP 3C.2 INDEPENDENT MIGRATION REVIEW`**

### Verdict Justification:
1. Migration `f3a9082b1c42` has been prepared with complete DAG continuity (`down_revision = 'e4b19082a5c1'`).
2. The migration explicitly revokes table privileges on all eight tables and sequence privileges on both sequences from `anon` and `authenticated`.
3. Default privileges for future tables and sequences created by `postgres` in `public` are hardened.
4. Downgrade fails closed with an explicit descriptive error.
5. All static AST and Alembic CLI validations passed cleanly.
6. Zero live database mutations occurred; the live database remains at baseline revision `1273f18b72a2`.

*Awaiting explicit human authorization for Step 3C.2 independent review before proceeding to any live migration execution.*
