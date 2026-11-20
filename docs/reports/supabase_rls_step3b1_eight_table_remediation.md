# ManuMind AI — Supabase RLS Remediation: Step 3B.1 — Eight-Table RLS Coverage Remediation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Target Migration:** `backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`  
**Preceding Migration:** `backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py`  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3B.1)  
**Date:** 2026-11-18  
**Final Verdict:** `READY FOR STEP 3B EXECUTION REVIEW`

---

## 1. Executive Summary

During the Step 3B.0 safety audit, an architectural security gap was identified: the pending migration `c742f9a1e0b5` creates two new tables (`ticket_proposals` and `consumed_tokens`) under Supabase default ACLs (`pg_default_acl`), which grant full access (`arwdDxtm`) to `anon` and `authenticated`. Because the original RLS migration `e4b19082a5c1` only covered the six pre-existing domain tables, executing `upgrade head` would have left both newly created tables with RLS disabled and exposed via PostgREST.

In this milestone (**Step 3B.1**), the unexecuted RLS migration `e4b19082a5c1` has been remediated and statically validated to provide comprehensive coverage across **all eight public tables**.

### Core Guarantees:
- **Zero Live Database Modifications:** The live Supabase instance was verified via read-only catalog queries to remain at baseline revision `1273f18b72a2`. Zero DDL, `upgrade`, `downgrade`, or data modifications occurred.
- **Eight-Table Coverage:** The migration now protects all six domain tables plus the two Phase 4 Step 6 ticket-proposal tables in the `public` schema.
- **Strict Grant & Revoke Protection:** Zero `GRANT` or `REVOKE` statements exist in `upgrade()` or `downgrade()`. Specifically, broad permission restoration (such as `GRANT ALL ON public.alembic_version TO anon, authenticated;`) is strictly prohibited.
- **Standard RLS & Default-Deny:** `FORCE ROW LEVEL SECURITY` is strictly avoided, and zero permissive policies are defined. Non-bypass roles (`anon`, `authenticated`) receive default-deny access via PostgREST, while direct backend queries by `postgres` (`rolbypassrls = True`) remain unobstructed.
- **Atomic Single-Transaction Execution Confirmed:** Inspection of `backend/alembic/env.py` confirmed that both pending revisions execute within a single atomic PostgreSQL transaction.

---

## 2. Pre-Editing Verification & Live Status Check

Read-only inspection of the live Supabase database and local migration files confirmed:

| Verification Item | Target Invariant | Actual State | Status |
| :--- | :--- | :--- | :--- |
| **Live Database Revision** | Must be at `1273f18b72a2` | `['1273f18b72a2']` | Verified |
| **RLS Migration Applied?** | Must NOT be applied anywhere | Unapplied (revision absent from `alembic_version`) | Verified |
| **Ticket Tables on Live DB** | Must NOT exist yet | `ticket_proposals_exists: False`, `consumed_tokens_exists: False` | Verified |
| **Live Tables RLS State** | Unchanged baseline | All 6 existing tables have `rls_enabled = False` | Verified |
| **Preceding Migration** | Defines both tables | `c742f9a1e0b5` creates `ticket_proposals` and `consumed_tokens` | Verified |
| **Schema Target** | `public` schema | Both tables target `public` schema | Verified |
| **Alembic DAG** | Linear chain | `<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1 (head)` | Verified |

Because `e4b19082a5c1` is strictly unapplied on live infrastructure, modifying the unexecuted migration file in place is completely safe and avoids unnecessary migration clutter.

---

## 3. Remediation Specification: Eight-Table RLS Coverage

**File:** [e4b19082a5c1_enable_rls_on_public_tables.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py)  
**Revision:** `e4b19082a5c1`  
**Down Revision:** `c742f9a1e0b5`

### Target Tables List (8 Tables Total)
```python
TARGET_TABLES: list[str] = [
    "machines",
    "sensor_readings",
    "alembic_version",
    "maintenance_history",
    "alerts",
    "tickets",
    "ticket_proposals",
    "consumed_tokens",
]
```

### 3.1 Upgrade Operations
Each table is schema-qualified with `public.` and enabled for standard Row Level Security:
```sql
ALTER TABLE public.machines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consumed_tokens ENABLE ROW LEVEL SECURITY;
```

### 3.2 Downgrade Operations (Symmetrical Reverse Order)
Downgrade disables standard RLS in exact reverse order:
```sql
ALTER TABLE public.consumed_tokens DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_proposals DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.sensor_readings DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.machines DISABLE ROW LEVEL SECURITY;
```

**Downgrade Security Warning:** Downgrading disables RLS and reopens the pre-migration access exposure for roles with table privileges (`anon`, `authenticated`). It must only be executed under emergency rollback protocols with prior authorization.

---

## 4. Strict Grant and Default ACL Security Analysis

Catalog inspection of `pg_default_acl` on the Supabase instance revealed:
```json
{
  "defaclrole": "postgres",
  "schema_name": "public",
  "defaclobjtype": "r",
  "defaclacl": "{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}"
}
```

### Architectural Distinctions & Insights:
1. **Separation of Table Grants and RLS:** In PostgreSQL, table privileges (`GRANT ... ON table`) and Row Level Security (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) are independent subsystems. Having `SELECT` or `INSERT` granted at the table level does not grant access to rows once RLS is enabled; without a matching permissive policy, PostgreSQL returns 0 rows (default-deny).
2. **Impact of Supabase Default ACLs:** Whenever role `postgres` creates a table in `public`, `pg_default_acl` automatically assigns `arwdDxtm` (ALL) to `anon`, `authenticated`, and `service_role`. This explains why `ticket_proposals` and `consumed_tokens` would have been exposed if created without RLS.
3. **No GRANT or REVOKE in Migration:** Modifying SQL grants inside an Alembic migration introduces schema migration drift and complicates rollback paths. By enabling standard RLS without permissive policies, PostgreSQL enforces default-deny at the row engine level, achieving immediate API lockdown without altering existing grant baselines.
4. **Least-Privilege Hardening Recommendation:** A subsequent, dedicated database hardening step is recommended to execute `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ...` and `REVOKE ALL ON ... FROM anon, authenticated`. This ensures defense-in-depth so that table privileges are aligned with least privilege.
5. **Credential Protection:** RLS protects against unauthorized API access, but does not mitigate leaks of privileged database credentials (`DATABASE_URL` or `service_role` key). Backend secrets must remain restricted to server-side environments.

---

## 5. PostgreSQL Role and Backend Compatibility

Live database catalog inspection verified the following backend connecting role attributes:

| Role Property | Live Database Value | Security / Compatibility Impact |
| :--- | :--- | :--- |
| **`current_user`** | `postgres` | Matches backend `DATABASE_URL` credentials |
| **`rolsuper`** | `False` | Tenant administrator in Supabase Cloud |
| **`rolbypassrls`** | `True` | Direct backend queries completely bypass standard RLS |
| **`rolcanlogin`** | `True` | Allowed to establish direct TCP sessions |
| **Table Ownership** | `postgres` owns all 8 tables | Authoritative owner of all schema objects |

### Query Compatibility Analysis:
- **Zero Query Disruption Mechanism:** Because `postgres` possesses `rolbypassrls = True`, PostgreSQL's RLS engine does not filter or restrict queries executed by this role. Direct backend operations (FastAPI endpoints, MCP tools, SQLAlchemy queries, Alembic runners) continue operating normally.
- **Preservation of Table-Owner Bypass:** If `FORCE ROW LEVEL SECURITY` were enabled, PostgreSQL would enforce RLS policies even against table owners and bypass roles. Because `e4b19082a5c1` strictly avoids `FORCE ROW LEVEL SECURITY`, `postgres` retains its native bypass behavior.
- **Future Hardening Note:** In a production defense-in-depth model, the backend application should ideally connect under a dedicated least-privilege role (`app_backend`) with explicit RLS policies rather than using a bypass role.

---

## 6. Alembic Transaction Behaviour Review

An independent source audit of `backend/alembic/env.py` lines 46–60 was conducted:
```python
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

### Findings:
1. **Single Transaction Block:** The `context.run_migrations()` call is wrapped inside a single `with context.begin_transaction():` context manager.
2. **No Per-Migration Commit:** `transaction_per_migration` is omitted in `context.configure()`, defaulting to `False`.
3. **PostgreSQL Transactional DDL:** PostgreSQL natively supports transactional DDL. Neither `c742f9a1e0b5` nor `e4b19082a5c1` contains non-transactional statements (such as `CREATE INDEX CONCURRENTLY` or `VACUUM`).
4. **Execution Guarantees:**
   - Both revisions `c742f9a1e0b5` and `e4b19082a5c1` execute within a **SINGLE ATOMIC POSTGRESQL TRANSACTION**.
   - If any statement in either migration fails, the entire transaction rolls back, leaving the database at revision `1273f18b72a2` with zero partial schema changes.

---

## 7. Static Validation Results

Static validation was performed via `scratch/validate_step3b1.py` and the Alembic CLI:

| Static Check | Target Requirement | Result | Evaluation |
| :--- | :--- | :--- | :--- |
| **Python Syntax** | Clean compilation | `py_compile.compile()` passed with 0 errors | **PASSED** |
| **AST Parse** | Clean AST parsing | Parsed without syntax warnings | **PASSED** |
| **Revision ID** | `e4b19082a5c1` | Exactly matches | **PASSED** |
| **Down Revision** | `c742f9a1e0b5` | Exactly matches | **PASSED** |
| **Target Tables Count** | Exactly 8 tables | `len(TARGET_TABLES) == 8` | **PASSED** |
| **Target Tables Parity** | Exact 8 tables specified | Matches expected 8 tables | **PASSED** |
| **Prohibited Tokens** | 0 occurrences of `GRANT`, `REVOKE`, `FORCE`, `POLICY`, `DROP TABLE`, `CREATE TABLE` in code | 0 found | **PASSED** |
| **Preceding Migration Integrity** | `c742f9a1e0b5` untouched | Verified untouched | **PASSED** |
| **Alembic Heads** | Exactly 1 head | `e4b19082a5c1 (head)` | **PASSED** |
| **Alembic History** | Linear chain | `<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1 (head)` | **PASSED** |

---

## 8. Post-Execution Verification Plan (Step 3B)

When live execution is authorized, the following verification sequence must be executed:

### Phase 1: Database Catalog Verification (Read-Only SQL)
Query `pg_class` to confirm RLS state across all eight tables:
```sql
SELECT 
    c.relname AS table_name,
    c.relrowsecurity AS rls_enabled,
    c.relforcerowsecurity AS force_rls_enabled,
    r.rolname AS table_owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r ON r.oid = c.relowner
WHERE n.nspname = 'public'
  AND c.relname IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  );
```
**Expected Catalog Outcome:**
- All 8 tables: `rls_enabled = True`
- All 8 tables: `force_rls_enabled = False`
- All 8 tables: `table_owner = postgres`

Query `public.alembic_version`:
```sql
SELECT version_num FROM public.alembic_version;
```
**Expected Outcome:** `['e4b19082a5c1']`.

### Phase 2: PostgREST API Security Verification (Read-Only HTTP Probes)
Verify the anonymous PostgREST interface using the public `anon` API key:

| Persona | Request | Target Table | Expected Response | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **`anon`** | `GET /rest/v1/machines` | `machines` | `200 OK` $\rightarrow$ `[]` | Default-deny filters all rows |
| **`anon`** | `GET /rest/v1/sensor_readings` | `sensor_readings` | `200 OK` $\rightarrow$ `[]` | Default-deny filters all rows |
| **`anon`** | `GET /rest/v1/ticket_proposals` | `ticket_proposals` | `200 OK` $\rightarrow$ `[]` | Default-deny filters all rows |
| **`anon`** | `GET /rest/v1/consumed_tokens` | `consumed_tokens` | `200 OK` $\rightarrow$ `[]` | Default-deny filters all rows |
| **`anon`** | `POST /rest/v1/ticket_proposals` | `ticket_proposals` | `401/403 Unauthorized` | Mutation rejected by RLS |
| **`postgres`** | SQLAlchemy connection | All 8 tables | Full row counts returned | `rolbypassrls = True` bypasses RLS |

*Note: Never execute PostgREST tests using the backend database connection. PostgREST tests must be executed via HTTP requests with the public `anon` key.*

---

## 9. Git Working Tree State and File Preservation

- **Active Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Files:** 0
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`, preserved from Phase 4)
- **Modified Untracked Files:** 1 (`backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`)
- **Untracked Historical Work:** All 18 previously existing files/directories remain completely untouched.

---

## 10. Remaining Risks & Mitigations

1. **Risk:** Single atomic transaction failure. If table creation in `c742f9a1e0b5` fails, RLS cannot be applied.  
   *Mitigation:* Pre-execution validation verified table constraints, FK targets, and syntax. Atomic rollback protects against inconsistent intermediate states.
2. **Risk:** Privileged credential leakage. Standard RLS does not protect against compromised `service_role` or `postgres` credentials.  
   *Mitigation:* Keep database credentials restricted to server-side environments; implement subsequent least-privilege role hardening.
3. **Risk:** Accidental state mutation by unit tests. Running tests like `test_mcp_ticket_creation.py` without environment isolation could pollute production data.  
   *Mitigation:* Post-migration verification must strictly use read-only scripts (`test_connection.py`, `verify_migration.py`).

---

## 11. Final Verdict

### Verdict: **`READY FOR STEP 3B EXECUTION REVIEW`**

### Verdict Justification:
1. The migration `e4b19082a5c1` was verified to be strictly unapplied on live infrastructure.
2. The preceding migration `c742f9a1e0b5` creates both `ticket_proposals` and `consumed_tokens`.
3. All eight public tables are now explicitly covered in `TARGET_TABLES`.
4. Upgrade and downgrade paths are completely symmetrical.
5. Zero `GRANT`, `REVOKE`, `FORCE ROW LEVEL SECURITY`, or permissive policies exist.
6. All static, AST, and Alembic DAG checks passed without errors.
7. Zero live database mutations occurred during Step 3B.1.

*Awaiting explicit human authorization before executing live database migration.*
