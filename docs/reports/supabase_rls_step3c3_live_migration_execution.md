# ManuMind AI — Supabase RLS Remediation: Step 3C.3 Live Migration Execution Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Live Revision Before Execution:** `1273f18b72a2`  
**Live Revision After Execution:** `f3a9082b1c42`  
**Execution Timestamp:** 2026-11-18 21:35:10 IST  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3C.3 Execution)  
**Execution Status:** Completed successfully with 0 errors  
**Final Verdict:** `SUCCESS — ALL MIGRATIONS AND VERIFICATIONS PASSED`

---

## 1. Explicit Authorization Acknowledgment

This live database migration was executed under explicit project owner authorization granted in the Step 3C.3 Live Migration Execution directive.

The authorization specifically approved:
1. Executing the reviewed live Supabase PostgreSQL migration using `alembic upgrade head`.
2. Applying the three reviewed pending migrations in their established DAG order:
   - `1273f18b72a2 -> c742f9a1e0b5` (`ticket_proposals` and `consumed_tokens` tables)
   - `c742f9a1e0b5 -> e4b19082a5c1` (Standard RLS activation across eight public tables)
   - `e4b19082a5c1 -> f3a9082b1c42` (Least-privilege API role grant revocation and default privilege hardening)
3. Executing the ten prepared read-only post-migration catalog and privilege verification checks.
4. Authoring comprehensive execution reports in Markdown and structured JSON.

---

## 2. Pre-Execution Baseline Verification

Immediately prior to execution, all mandatory baseline preconditions were queried and confirmed against the live database and local repository:

| Pre-Execution Parameter | Required Baseline | Queried Pre-Execution Value | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Directory** | `D:\Desktop\FInal year project\manumind-ai` | `D:\Desktop\FInal year project\manumind-ai` | Confirmed |
| **Git Branch** | `main` | `main` | Confirmed |
| **Git HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Confirmed |
| **Local Alembic DAG Head** | Exactly one head: `f3a9082b1c42` | `f3a9082b1c42 (head)` | Confirmed |
| **Live Database Revision** | `1273f18b72a2` | `['1273f18b72a2']` | Confirmed |
| **Connecting Role** | `postgres` (`rolbypassrls = True`) | `postgres` (`rolbypassrls = True`) | Confirmed |
| **Target Tables Existence** | `ticket_proposals`, `consumed_tokens` absent | Absent (`[]`) | Confirmed |
| **Existing Table Row Counts** | 40,416 rows across 6 tables | 40,416 rows across 6 tables | Confirmed |

### Migration Source File Integrity (SHA256 Hashes):
- `backend/alembic/versions/c742f9a1e0b5_ticket_proposals.py`:  
  `55661883B8D870CB44AD84F398C4D653FBDE8A8F798CC5F90C23BF18676A7BB7`
- `backend/alembic/versions/e4b19082a5c1_enable_rls_on_public_tables.py`:  
  `D360F941071FFDFCBA04CC40D5553E69274C4FB5EA70C76CC08CE1A0E1BD4EC6`
- `backend/alembic/versions/f3a9082b1c42_harden_least_privilege_grants.py`:  
  `C1A06ABCBA932106C8C7A1402E728B9CF5AAAE28980C676F825898E9569D07F7`

---

## 3. Live Migration Execution Protocol

### 3.1 Executed Command
```powershell
Set-Location "D:\Desktop\FInal year project\manumind-ai"

& "C:\Users\PR BHAYA SREE\AppData\Local\Programs\Python\Python311\python.exe" -m alembic -c backend/alembic.ini upgrade head
```

### 3.2 Actual Alembic Execution Output
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 1273f18b72a2 -> c742f9a1e0b5, ticket_proposals and consumed_tokens tables
INFO  [alembic.runtime.migration] Running upgrade c742f9a1e0b5 -> e4b19082a5c1, enable standard rls on eight public tables
INFO  [alembic.runtime.migration] Running upgrade e4b19082a5c1 -> f3a9082b1c42, harden least privilege grants on public tables and sequences
```
- **Exit Code:** `0` (Success)
- **Transaction Model:** Enclosed in a single PostgreSQL transactional block (`with context.begin_transaction():`).
- **Duration:** <2 seconds.
- **Failures / Ambiguities Encountered:** Zero.

---

## 4. Post-Migration Verification Results (Ten Prepared Catalog Checks)

All ten verification checks were executed via direct read-only PostgreSQL catalog queries immediately following migration completion:

### Check 1: Alembic Revision Check
- **SQL Query:**
  ```sql
  SELECT version_num FROM public.alembic_version;
  ```
- **Expected Result:** Exactly `['f3a9082b1c42']`
- **Actual Result:** `['f3a9082b1c42']`
- **Status:** **PASS**

---

### Check 2: Table Existence Check
- **SQL Query:**
  ```sql
  SELECT tablename 
  FROM pg_tables 
  WHERE schemaname = 'public' 
    AND tablename IN ('ticket_proposals', 'consumed_tokens')
  ORDER BY tablename;
  ```
- **Expected Result:** `['consumed_tokens', 'ticket_proposals']`
- **Actual Result:** `['consumed_tokens', 'ticket_proposals']`
- **Status:** **PASS**

---

### Check 3: Standard RLS Activation Check (All Eight Tables)
- **SQL Query:**
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
- **Expected Result:** `relrowsecurity = True` on all 8 tables.
- **Actual Result:**
  - `alembic_version`: `True`
  - `alerts`: `True`
  - `consumed_tokens`: `True`
  - `machines`: `True`
  - `maintenance_history`: `True`
  - `sensor_readings`: `True`
  - `ticket_proposals`: `True`
  - `tickets`: `True`
- **Status:** **PASS**

---

### Check 4: Force RLS Invariance Check
- **SQL Query:**
  ```sql
  SELECT c.relname, c.relforcerowsecurity 
  FROM pg_class c 
  JOIN pg_namespace n ON n.oid = c.relnamespace 
  WHERE n.nspname = 'public' 
    AND c.relname IN (
      'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
      'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
    )
  ORDER BY c.relname;
  ```
- **Expected Result:** `relforcerowsecurity = False` on all 8 tables (FORCE RLS remains strictly disabled).
- **Actual Result:** `False` across all 8 tables.
- **Status:** **PASS**

---

### Check 5: Zero Permissive Policies Check
- **SQL Query:**
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
- **Expected Result:** `0` (PostgreSQL default-deny is active).
- **Actual Result:** `0` policies.
- **Status:** **PASS**

---

### Check 6: Table Privileges Revocation Check (API Roles)
- **SQL Query:**
  ```sql
  SELECT grantee, table_name, privilege_type 
  FROM information_schema.role_table_grants 
  WHERE table_schema = 'public' 
    AND table_name IN (
      'machines', 'sensor_readings', 'alembic_version', 'maintenance_history',
      'alerts', 'tickets', 'ticket_proposals', 'consumed_tokens'
    ) 
    AND grantee IN ('anon', 'authenticated');
  ```
- **Expected Result:** `0` rows (Zero table privileges remain for `anon` and `authenticated`).
- **Actual Result:** `0` rows (`[]`).
- **Status:** **PASS** (Eliminates the `TRUNCATE` vulnerability and PostgREST API exposure).

---

### Check 7: Sequence Privileges Revocation Check (API Roles)
- **SQL Query:**
  ```sql
  SELECT grantee, object_name, privilege_type 
  FROM information_schema.role_usage_grants 
  WHERE object_schema = 'public' 
    AND object_name IN ('sensor_readings_id_seq', 'maintenance_history_id_seq') 
    AND grantee IN ('anon', 'authenticated');
  ```
- **Expected Result:** `0` rows (Zero sequence usage grants remain for `anon` and `authenticated`).
- **Actual Result:** `0` rows (`[]`).
- **Status:** **PASS** (Prevents sequence enumeration and ID exhaustion).

---

### Check 8: Retained Privileges Check (`postgres` & `service_role`)
- **SQL Query:**
  ```sql
  SELECT grantee, table_name, count(privilege_type) as priv_count 
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
- **Expected Result:** Both `postgres` and `service_role` retain all 7 privilege types (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`) across all 8 tables (16 groups of 7 privileges = 112 grants).
- **Actual Result:** All 8 tables show exactly 7 privileges for `postgres` and 7 privileges for `service_role`.
- **Status:** **PASS**

---

### Check 9: Future Default Privileges Check
- **SQL Query:**
  ```sql
  SELECT d.defaclobjtype, d.defaclacl::text 
  FROM pg_default_acl d 
  JOIN pg_namespace n ON n.oid = d.defaclnamespace 
  WHERE pg_get_userbyid(d.defaclrole) = 'postgres' 
    AND n.nspname = 'public' 
    AND d.defaclobjtype IN ('r', 'S');
  ```
- **Expected Result:** Default ACLs exist for relations (`r`) and sequences (`S`) for creator role `postgres` in schema `public` granting privileges only to `postgres` and `service_role`, with zero grants to `anon` or `authenticated`.
- **Actual Result:**
  - Relations (`r`): `{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}`
  - Sequences (`S`): `{postgres=rwU/postgres,service_role=rwU/postgres}`
- **Status:** **PASS**

---

### Check 10: Ownership Invariance Check
- **SQL Query:**
  ```sql
  SELECT c.relname, r.rolname as owner, c.relkind 
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
- **Expected Result:** All 10 objects owned by `postgres`.
- **Actual Result:** Exactly 10 rows returned, all owned by `postgres`:
  - `alembic_version`: `postgres` (table)
  - `alerts`: `postgres` (table)
  - `consumed_tokens`: `postgres` (table)
  - `machines`: `postgres` (table)
  - `maintenance_history`: `postgres` (table)
  - `maintenance_history_id_seq`: `postgres` (sequence)
  - `sensor_readings`: `postgres` (table)
  - `sensor_readings_id_seq`: `postgres` (sequence)
  - `ticket_proposals`: `postgres` (table)
  - `tickets`: `postgres` (table)
- **Status:** **PASS**

---

## 5. Cross-Database Data Integrity Audit (`backend/verify_migration.py`)

A non-destructive cross-database verification between SQLite (`manumind.db`) and Supabase PostgreSQL was conducted immediately following migration:

```text
===========================================================================
ManuMind AI — Cross-Database Migration Verification Audit
===========================================================================
Source (SQLite - Read-Only): D:\Desktop\FInal year project\manumind-ai\manumind.db
Destination (Supabase):       postgresql://postgres.hgmadjxfrlkpyxvdqpqb:********@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
---------------------------------------------------------------------------

[CHECK 1/8] Table Row Counts Parity:
  - machines              : SQLite =     10 | Supabase =     10 | Target =     10 -> [MATCH]
  - sensor_readings       : SQLite = 40,000 | Supabase = 40,000 | Target = 40,000 -> [MATCH]
  - maintenance_history   : SQLite =    400 | Supabase =    400 | Target =    400 -> [MATCH]
  - alerts                : SQLite =      5 | Supabase =      5 | Target =      5 -> [MATCH]
  - tickets               : SQLite =      1 | Supabase =      1 | Target =      1 -> [MATCH]

[CHECK 2/8] Primary Key Ranges & Machine IDs:
  - machines IDs match (10/10):        [MATCH]
  - sensor_readings ID range (1..40000): SQLite=[1..40000] Supabase=[1..40000] -> [MATCH]
  - maintenance_history ID range (1..400): SQLite=[1..400] Supabase=[1..400] -> [MATCH]

[CHECK 3/8] Referential Integrity & Orphan Records Check:
  - sensor_readings orphans:            0 -> [PASS]
  - maintenance_history orphans:        0 -> [PASS]
  - alerts orphans:                     0 -> [PASS]
  - tickets orphans:                    0 -> [PASS]

[CHECK 4/8] Timestamp Ranges Parity:
  - sensor_readings start: SQLite=2026-10-22 14:40:00.000000 | Supabase=2026-10-22 14:40:00
  - sensor_readings end:   SQLite=2026-11-05 11:55:00.000000 | Supabase=2026-11-05 11:55:00
  - Timestamp match:                    [MATCH]

[CHECK 5/8] Sensor Telemetry Channel Aggregates Parity:
  - Vibration     : SQLite avg=1.9616  min=0.816  max=10.984 | Supabase avg=1.9616  min=0.816  max=10.984 -> [MATCH]
  - Temperature   : SQLite avg=49.3902 min=41.03  max=96.56  | Supabase avg=49.3902 min=41.03  max=96.56  -> [MATCH]
  - Pressure      : SQLite avg=6.1723  min=2.17   max=8.35   | Supabase avg=6.1723  min=2.17   max=8.35   -> [MATCH]
  - Current       : SQLite avg=14.8784 min=11.62  max=32.25  | Supabase avg=14.8784 min=11.62  max=32.25  -> [MATCH]
  - RPM           : SQLite avg=1799.32 min=1700.4 max=1832.4 | Supabase avg=1799.32 min=1700.4 max=1832.4 -> [MATCH]

[CHECK 6/8] JSON Field Parsing & Content Integrity:
  - Alert M104 shap_json valid:         [PASS] (vibration driver = 0.54)
  - Alert M104 sensor_contrib valid:    [PASS] (vibration contrib = 0.62)
  - Ticket TCK-2026-001 evidence valid: [PASS] (authorized by 'Lead Engineer S. Raman')

[CHECK 7/8] Priority Alerts & Tickets Domain State:
  - Priority #1 Alert: ALT-M104-001 on M104 with Score=22.0 (risk=0.88, crit=5, impact=5, status='PENDING_APPROVAL') -> [PASS]

[CHECK 8/8] Non-Destructive PostgreSQL Sequence State Inspection:
  - 'sensor_readings_id_seq' state    : last_value=40000 (Target 40000), is_called=True (Target True) -> [PASS]
  - 'maintenance_history_id_seq' state: last_value=400 (Target 400), is_called=True (Target True) -> [PASS]

===========================================================================
[AUDIT RESULT: ALL CHECKS PASSED] Supabase matches SQLite with 100% data fidelity!
===========================================================================
```

---

## 6. Git & Workspace Preservation Audit

- **Git Branch:** `main`
- **Git HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Changes:** Exactly 0 files staged.
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`), unmodified since Phase 4.
- **Untracked Historical Work:** All historical test suites, reports, and migration files remain preserved.
- **Zero Git mutations:** No `git add`, `git commit`, `git push`, `git checkout`, or `git reset` commands were executed.

---

## 7. Remaining Security Architecture & Limitations

1. **`supabase_admin` Default Privilege Limitation:**
   - PostgreSQL default privileges were altered for role `postgres`, which is the role used by Alembic and backend SQLAlchemy connections.
   - It does not modify default privileges for `supabase_admin` (Supabase Cloud internal system role).
   - **Architectural Policy:** All future database objects must be created strictly through version-controlled Alembic migrations executing as `postgres`. Creating application tables manually via Supabase Studio UI as `supabase_admin` would inherit Supabase cloud default grants and is prohibited.
2. **`service_role` Administrative Access:**
   - The `service_role` retains administrative privileges (`arwdDxtm`) across all tables.
   - This role is strictly intended for trusted backend administrative automation and must never be exposed to clients, browser environments, or public repositories.
3. **Fail-Closed Downgrade Policy:**
   - As designed, `alembic downgrade` for `f3a9082b1c42` is permanently disabled via `NotImplementedError` to prevent accidental restoration of public table/sequence grants.

---

## 8. Deliverables Generated

- **Execution Markdown Report:**  
  [supabase_rls_step3c3_live_migration_execution.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c3_live_migration_execution.md)
- **Structured JSON Report:**  
  [supabase_rls_step3c3_live_migration_execution.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c3_live_migration_execution.json)

---

## 9. Final Verdict

### Final Verdict: **`SUCCESS — ALL MIGRATIONS AND VERIFICATIONS PASSED`**

### Verdict Justification:
1. All three authorized migrations (`c742f9a1e0b5`, `e4b19082a5c1`, `f3a9082b1c42`) executed cleanly in a single atomic transaction without error.
2. The live database revision advanced from `1273f18b72a2` to `f3a9082b1c42`.
3. Standard Row Level Security is active (`relrowsecurity = True`) across all eight public tables.
4. All API role (`anon` and `authenticated`) table privileges (`arwdDxtm` including `TRUNCATE`) and sequence usage privileges (`rwU`) have been completely revoked.
5. Future default privileges for `postgres` in `public` have been hardened to exclude API roles.
6. All ten catalog and privilege verification checks returned `PASS`.
7. All 40,416 rows across all domain tables remain 100% intact with verified referential and numeric parity.
8. Zero Git changes were staged, committed, or pushed.
