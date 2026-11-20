# ManuMind AI — Supabase RLS Remediation: Step 3C.3 Controlled Live Migration Preflight Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Live Revision:** `1273f18b72a2`  
**Pending Head:** `f3a9082b1c42`  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3C.3)  
**Date:** 2026-11-18  
**Audit Target:** Controlled Live Migration Preflight and Operational Execution Runbook  
**Final Verdict:** `READY FOR EXPLICIT HUMAN EXECUTION AUTHORIZATION`

---

## 1. Executive Summary

This preflight audit and operational runbook establish the final protocol for applying the three reviewed pending Alembic migrations to the live Supabase PostgreSQL database:

1. **`c742f9a1e0b5_ticket_proposals.py`:** Staged maintenance ticket proposals and replay prevention audit tables.
2. **`e4b19082a5c1_enable_rls_on_public_tables.py`:** Standard Row Level Security (RLS) activation across all eight public tables.
3. **`f3a9082b1c42_harden_least_privilege_grants.py`:** Least-privilege table, sequence, and future default privilege hardening.

### Core Preflight Confirmations:
- **Zero Live Mutations During Preflight:** Read-only queries confirmed that the live Supabase database remains strictly at baseline revision `1273f18b72a2`. No DDL or DML was executed.
- **Connection Identity Verified:** Both Alembic and the backend application connect as role `postgres` (`rolbypassrls = True`, table owner) via the direct session pooler (port 5432).
- **Single Atomic Transaction Architecture:** The entire sequence executes within a single PostgreSQL transaction block. Failure of any statement guarantees a complete automatic rollback to `1273f18b72a2`.
- **Zero Window of Exposure:** Tables are created, standard RLS is enabled, and default privileges are hardened simultaneously in one atomic commit.
- **Comprehensive Post-Migration SQL Suite:** Ten explicit read-only catalog queries have been prepared to verify table existence, RLS states, zero policies, privilege revocations, default privileges, and ownership post-migration.

---

## 2. Live Database Baseline Verification (Read-Only)

Live database catalog inspection via the Supabase session pooler confirmed the following:

| Baseline Property | Expected Invariant | Queried Live State | Evaluation |
| :--- | :--- | :--- | :--- |
| **Connecting Database** | `postgres` | `postgres` | Confirmed |
| **`current_user` / `session_user`** | `postgres` / `postgres` | `postgres` / `postgres` | Confirmed |
| **`rolbypassrls` Attribute** | Must be `True` | `rolbypassrls = True` | Confirmed |
| **`public.alembic_version`** | `['1273f18b72a2']` | `['1273f18b72a2']` | Confirmed |
| **`ticket_proposals` Exists?** | Must be `False` | `False` | Confirmed |
| **`consumed_tokens` Exists?** | Must be `False` | `False` | Confirmed |
| **RLS on 6 Existing Tables** | `rls_enabled = False` | `False` on all 6 tables | Confirmed |
| **Force RLS on 6 Existing Tables** | `force_rls_enabled = False` | `False` on all 6 tables | Confirmed |
| **Existing Table Owner** | `postgres` | `postgres` on all 6 tables | Confirmed |
| **Existing API Table Grants** | `arwdDxtm` to `anon`/`authenticated` | 84 grants on existing 6 tables | Confirmed |
| **Existing API Sequence Grants** | `rwU` to `anon`/`authenticated` | 4 grants on 2 sequences | Confirmed |

*Stop Condition Check: The live revision is confirmed to be exactly `1273f18b72a2`. No revision drift has occurred.*

---

## 3. Migration Execution Identity Verification

1. **Alembic Connection Configuration:**
   - Source inspection of `backend/alembic/env.py` (lines 26–30) and `backend/app/database.py` confirmed that Alembic retrieves its connection string via `get_normalized_database_url()`.
   - The connection string parses `settings.DATABASE_URL` from `.env`.
   - The connection connects to `aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres` as role `postgres`.
2. **Identity Alignment:**
   - The migration runner uses the exact same connection configuration and credentials as the application runtime backend.
   - Future Alembic migrations will continue executing as `postgres`.
3. **`supabase_admin` Default Privilege Limitation:**
   - Step 3C alters default privileges for `ROLE postgres IN SCHEMA public`.
   - It does not alter default privileges for `ROLE supabase_admin IN SCHEMA public` (Supabase Cloud internal management role).
   - **Operational Restriction:** All future application tables and schema objects must be created strictly through version-controlled Alembic migrations executing as `postgres`. Developers must not create application tables out-of-band via Supabase Studio dashboard using `supabase_admin`.

---

## 4. Recovery Readiness & Operational Prerequisites

| Recovery Domain | Assessment / Status | Operational Recommendation |
| :--- | :--- | :--- |
| **Supabase Cloud Backups** | Managed daily automated backups active | Verify latest backup timestamp in Supabase Dashboard prior to execution. |
| **Point-in-Time Recovery (PITR)** | Cloud-managed WAL archiving | Available via Supabase Project Dashboard. |
| **Local Authoritative Data** | SQLite `manumind.db` identical baseline | Verified: 10 machines, 40000 readings, 400 history, 5 alerts, 1 ticket. |
| **Application Process Disruption** | Negligible (<2 seconds execution) | Pause background telemetry ingest workers briefly during execution. |
| **Maintenance Window** | Recommended (5 minutes) | Execute during a low-activity window as standard DBA practice. |

---

## 5. Exact Execution Runbook

### 5.1 Environment Prerequisites
- **Working Directory:** `D:\Desktop\FInal year project\manumind-ai`
- **Shell:** Windows PowerShell
- **Python Binary:** `C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe`
- **Network Access:** Outbound TCP port 5432 allowed to `aws-0-ap-southeast-2.pooler.supabase.com`.
- **Sandbox Mode:** Must run with network access (`BypassSandbox: true` in agent tooling).

### 5.2 Pre-Execution Sanity Check Commands
```powershell
# 1. Verify working directory
Set-Location "D:\Desktop\FInal year project\manumind-ai"

# 2. Verify Git HEAD
git rev-parse HEAD
# Target output: a1e7e77fa550724f812cc2a1024a6ff7d194bc20

# 3. Verify Alembic heads
& "C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe" -m alembic -c backend/alembic.ini heads
# Target output: f3a9082b1c42 (head)
```

### 5.3 Live Migration Execution Command
```powershell
& "C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe" -m alembic -c backend/alembic.ini upgrade head
```

### 5.4 Expected Illustrative Output
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 1273f18b72a2 -> c742f9a1e0b5, ticket_proposals and consumed_tokens tables
INFO  [alembic.runtime.migration] Running upgrade c742f9a1e0b5 -> e4b19082a5c1, enable standard rls on eight public tables
INFO  [alembic.runtime.migration] Running upgrade e4b19082a5c1 -> f3a9082b1c42, harden least privilege grants on public tables and sequences
```

### 5.5 Stop Conditions & Immediate Actions
- **Stop Condition 1:** If the command raises any exception or timeout, **DO NOT re-run the command immediately**.
- **Stop Condition 2:** In the event of an ambiguous network disconnection, immediately execute Query 1 (Section 6) to inspect `public.alembic_version`.

---

## 6. Post-Migration Verification Queries (Exact Read-Only SQL)

Execute the following read-only SQL queries via Python/SQLAlchemy immediately post-migration:

### Query 1: Alembic Revision Check
```sql
SELECT version_num FROM public.alembic_version;
```
- **Expected Result:** Exactly `['f3a9082b1c42']`.

### Query 2: Table Existence Check
```sql
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('ticket_proposals', 'consumed_tokens')
ORDER BY tablename;
```
- **Expected Result:** 2 rows: `consumed_tokens`, `ticket_proposals`.

### Query 3: Standard RLS Activation Check (All 8 Tables)
```sql
SELECT c.relname, c.relrowsecurity 
FROM pg_class c 
JOIN pg_namespace n ON n.oid = c.relnamespace 
WHERE n.nspname = 'public' 
  AND c.relname IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  )
ORDER BY c.relname;
```
- **Expected Result:** Exactly 8 rows, all with `relrowsecurity = True`.

### Query 4: Force RLS Invariance Check
```sql
SELECT count(*) 
FROM pg_class c 
JOIN pg_namespace n ON n.oid = c.relnamespace 
WHERE n.nspname = 'public' 
  AND c.relforcerowsecurity = true 
  AND c.relname IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  );
```
- **Expected Result:** `0` (FORCE RLS remains strictly disabled).

### Query 5: Zero Permissive Policies Check
```sql
SELECT count(*) 
FROM pg_policy p 
JOIN pg_class c ON c.oid = p.polrelid 
JOIN pg_namespace n ON n.oid = c.relnamespace 
WHERE n.nspname = 'public' 
  AND c.relname IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  );
```
- **Expected Result:** `0` (PostgreSQL default-deny is strictly active).

### Query 6: Table Privileges Revocation Check (API Roles)
```sql
SELECT count(*) 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND table_name IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  ) 
  AND grantee IN ('anon', 'authenticated');
```
- **Expected Result:** `0` (Zero table privileges remain for API roles).

### Query 7: Sequence Privileges Revocation Check (API Roles)
```sql
SELECT count(*) 
FROM information_schema.role_usage_grants 
WHERE object_schema = 'public' 
  AND object_name IN ('sensor_readings_id_seq', 'maintenance_history_id_seq') 
  AND grantee IN ('anon', 'authenticated');
```
- **Expected Result:** `0` (Zero sequence privileges remain for API roles).

### Query 8: Retained Privileges Check (`postgres` & `service_role`)
```sql
SELECT grantee, table_name, count(privilege_type) 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND table_name IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
  ) 
  AND grantee IN ('postgres', 'service_role')
GROUP BY grantee, table_name 
ORDER BY table_name, grantee;
```
- **Expected Result:** Both `postgres` and `service_role` retain full privileges across all 8 tables.

### Query 9: Future Default Privileges Check
```sql
SELECT d.defaclobjtype, d.defaclacl 
FROM pg_default_acl d 
JOIN pg_namespace n ON n.oid = d.defaclnamespace 
WHERE pg_get_userbyid(d.defaclrole) = 'postgres' 
  AND n.nspname = 'public' 
  AND d.defaclobjtype IN ('r', 'S');
```
- **Expected Result:** Neither `defaclacl` string contains `anon=` or `authenticated=`.

### Query 10: Ownership Invariance Check
```sql
SELECT c.relname, r.rolname as owner 
FROM pg_class c 
JOIN pg_namespace n ON n.oid = c.relnamespace 
JOIN pg_roles r ON r.oid = c.relowner 
WHERE n.nspname = 'public' 
  AND c.relname IN (
    'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
    'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens',
    'sensor_readings_id_seq', 'maintenance_history_id_seq'
  )
ORDER BY c.relname;
```
- **Expected Result:** Exactly 10 rows, all owned by `postgres`.

---

## 7. Failure Handling Protocol

| Failure Scenario | Database Engine State | Recovery Protocol |
| :--- | :--- | :--- |
| **Migration Fails Before Commit** | PostgreSQL rolls back entire transaction | State remains at `1273f18b72a2`. Inspect error log, resolve syntax/constraint issue, re-run upgrade. |
| **Connection Drops During Migration** | PostgreSQL server aborts open transaction | Automatic rollback to `1273f18b72a2`. Verify connectivity with `backend/test_connection.py`, re-run upgrade. |
| **Connection Drops Post-Commit** | Transaction committed on database | Run Query 1 (`public.alembic_version`). If `f3a9082b1c42`, execute verification queries. Do NOT re-run upgrade. |
| **Success Reported but Version Mismatched** | Partial or aborted state | Run Query 1. Inspect PostgreSQL logs. Do not attempt manual DDL. |
| **Unexpected Grants Detected Post-Migration** | Privilege revocation was incomplete | Review specific table ACL in `pg_class.relacl`. Execute targeted revocation query. Do NOT downgrade. |
| **Backend Connectivity Fails Post-Migration** | Connection pooler or network issue | Verify `test_connection.py`. Ensure pooler did not drop sessions. Do NOT downgrade. |

### Strict Rollback Warning:
- **Never execute `alembic downgrade`:** Downgrading `f3a9082b1c42` is blocked by design (`NotImplementedError`).
- **Never execute manual `GRANT ALL`:** Restoring broad privileges re-exposes the database to the `TRUNCATE` vulnerability.

---

## 8. Git Preservation Audit

- **Active Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Changes:** 0
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`, preserved from Phase 4)
- **Untracked Historical Work:** All 21 previously existing untracked files/directories remain intact.
- **New Deliverables Created:** Only the two Step 3C.3 preflight reports. Zero migration or source files were modified.

---

## 9. Deliverables Generated

- **Preflight & Runbook Report (Markdown):**  
  [supabase_rls_step3c3_live_migration_preflight.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c3_live_migration_preflight.md)
- **Structured Preflight Report (JSON):**  
  [supabase_rls_step3c3_live_migration_preflight.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c3_live_migration_preflight.json)

---

## 10. Final Verdict

### Verdict: **`READY FOR EXPLICIT HUMAN EXECUTION AUTHORIZATION`**

### Verdict Justification:
1. The live database baseline is verified at `1273f18b72a2` with 0 uncommitted mutations.
2. The complete three-migration chain is linear, unified, and statically validated.
3. The execution runbook and stop conditions are established.
4. Ten comprehensive post-migration verification queries are prepared.
5. All failure scenarios have been analyzed with a strict fail-closed rollback protocol.

*This report completes preflight preparations. No live database changes have occurred. Awaiting explicit human authorization to execute live migration.*
