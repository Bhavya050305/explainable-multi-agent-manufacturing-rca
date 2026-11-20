# ManuMind AI — Supabase RLS Remediation: Step 3C.4 Independent Post-Migration Privilege Verification Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Live Alembic Revision:** `f3a9082b1c42`  
**Database Engine:** PostgreSQL 17.11 on x86_64-pc-linux-gnu (Server Version: `170011`)  
**Audit Type:** Strictly Read-Only Independent Post-Migration Privilege and Catalog Audit  
**Execution Timestamp:** 2026-11-18 21:45:00 IST  
**Final Verdict:** `PASS — ALL PRIVILEGES INDEPENDENTLY VERIFIED`

---

## 1. Executive Summary

This independent, strictly read-only security audit independently inspected the post-migration PostgreSQL privileges, catalog ACLs, role memberships, default ACLs, and Row Level Security (RLS) configurations on the live Supabase database following Step 3C.3 live migration execution (`f3a9082b1c42`).

### Key Audit Confirmations:
1. **Zero Table Privileges for API Roles:** `has_table_privilege()` evaluations across all eight public tables confirmed `False` for both `anon` and `authenticated` across all eight supported privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`, and `MAINTAIN`).
2. **Zero Sequence Privileges for API Roles:** `has_sequence_privilege()` confirmed `False` for both `anon` and `authenticated` across both sequences for `SELECT`, `USAGE`, and `UPDATE`.
3. **Discrepancy Reconciled:** The difference between the 8 ACL letters (`arwdDxtm`) and the 7 `information_schema` privilege types (112 rows) is conclusively explained by PostgreSQL 17's native `MAINTAIN` privilege (`m`), which is tracked in `pg_class.relacl` (yielding 128 total native grants across 8 tables) but omitted from SQL-standard `information_schema.role_table_grants` (which lists 112 grants).
4. **Zero Indirect Privilege Paths:** Role membership inspection of `pg_auth_members` and catalog analysis of `pg_class.relacl` via `aclexplode` confirmed zero grants to role `PUBLIC` and no indirect privilege inheritance for `anon` or `authenticated`.
5. **Standard RLS & Invariance Confirmed:** All eight public tables have `relrowsecurity = True`, `relforcerowsecurity = False`, and 0 RLS policies (PostgreSQL default-deny is active).
6. **Future Default Privileges Hardened:** Creator role `postgres` in schema `public` has hardened default ACLs for tables and sequences granting privileges only to `postgres` and `service_role`.

---

## 2. Table Privilege Verification (All Eight Public Tables)

### 2.1 Scope of Inspection
The eight public tables inspected:
1. `machines`
2. `sensor_readings`
3. `alembic_version`
4. `maintenance_history`
5. `alerts`
6. `tickets`
7. `ticket_proposals`
8. `consumed_tokens`

### 2.2 Effective Privileges via `has_table_privilege`
Each privilege was queried individually using `has_table_privilege(role, table, privilege)` for all four key database roles:

| Privilege Evaluated | PostgreSQL Letter | `anon` Effective Privilege | `authenticated` Effective Privilege | `postgres` Effective Privilege | `service_role` Effective Privilege | Evaluation Status |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| **SELECT** | `r` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **INSERT** | `a` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **UPDATE** | `w` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **DELETE** | `d` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **TRUNCATE** | `D` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **REFERENCES** | `x` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **TRIGGER** | `t` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |
| **MAINTAIN** | `m` | `False` (0/8 tables) | `False` (0/8 tables) | `True` (8/8 tables) | `True` (8/8 tables) | **PASS** |

*Result: Both `anon` and `authenticated` possess zero effective privileges on all eight tables.*

### 2.3 Indirect Privilege Path & Role Membership Audit
1. **Public Grants:** Inspection of `aclexplode(c.relacl)` for `grantee = 0` (role `PUBLIC`) returned `0` rows across all eight tables. No privileges are granted to `PUBLIC`.
2. **Role Inheritance (`pg_auth_members`):**
   - `postgres` is a member of `authenticated`, `anon`, `service_role`, `authenticator`, `pg_read_all_data`, `pg_monitor`, `pg_signal_backend`, `pg_create_subscription`, and `supabase_privileged_role`.
   - `authenticator` (PostgREST connection pool role) is a member of `anon`, `authenticated`, and `service_role` (allowing it to `SET ROLE` based on JWT claims).
   - `supabase_realtime_admin` is a member of `anon`, `authenticated`, and `service_role`.
   - **Crucial Invariant:** Neither `anon` nor `authenticated` is a member of any privileged role (`postgres` or `service_role`). No indirect privilege inheritance path exists.

---

## 3. Privilege-Count Discrepancy Reconciliation

### 3.1 The Question
The Step 3C.3 execution report noted that the raw catalog ACL string is `arwdDxtm` (8 letters), while reporting 7 privilege types and 112 total grants in `information_schema.role_table_grants`.

### 3.2 Database Engine Version Evidence
- **Queried Engine Version:**  
  `PostgreSQL 17.11 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 15.2.0, 64-bit`
- **Server Version Num:** `170011` (PostgreSQL 17.11)

### 3.3 Identification of the Eighth Privilege: `MAINTAIN`
- In PostgreSQL 16+, PostgreSQL introduced the table-level privilege **`MAINTAIN`** (ACL letter `m`).
- `MAINTAIN` allows roles to execute maintenance commands: `VACUUM`, `ANALYZE`, `CLUSTER`, `REFRESH MATERIALIZED VIEW`, and `REINDEX`.
- The letters in `arwdDxtm` map exactly as follows:
  1. `a` = `INSERT` ("append")
  2. `r` = `SELECT` ("read")
  3. `w` = `UPDATE` ("write")
  4. `d` = `DELETE`
  5. `D` = `TRUNCATE`
  6. `x` = `REFERENCES`
  7. `t` = `TRIGGER`
  8. `m` = `MAINTAIN` (PostgreSQL 16+ addition)

### 3.4 Catalog vs. Information Schema Comparison
| Inspection Dimension | Native Catalog (`pg_class.relacl` / `aclexplode`) | SQL-Standard (`information_schema.role_table_grants`) | Explanation |
| :--- | :--- | :--- | :--- |
| **Privileges Included** | 8: `DELETE`, `INSERT`, `MAINTAIN`, `REFERENCES`, `SELECT`, `TRIGGER`, `TRUNCATE`, `UPDATE` | 7: `DELETE`, `INSERT`, `REFERENCES`, `SELECT`, `TRIGGER`, `TRUNCATE`, `UPDATE` | `MAINTAIN` is a PostgreSQL vendor extension not included in the ANSI SQL standard definition of `information_schema.table_privileges`. |
| **Grantees per Table** | 2: `postgres`, `service_role` | 2: `postgres`, `service_role` | `anon` and `authenticated` have 0 grants in both. |
| **Privileges per Role/Table** | 8 grants | 7 grants | 8 native vs. 7 SQL standard. |
| **Grants per Table** | $8 \times 2 = 16$ grants | $7 \times 2 = 14$ grants | Difference of 2 (`MAINTAIN` for `postgres` and `service_role`). |
| **Total Grants Across 8 Tables** | $16 \times 8 = \mathbf{128}$ **grants** | $14 \times 8 = \mathbf{112}$ **grants** | Both counts are completely accurate within their respective catalog representations. |

*Reconciliation Verdict: Confirmed. The 112 grants in information-schema represent the 7 ANSI SQL privileges, while the 128 grants in aclexplode represent all 8 PostgreSQL 17 native privileges including MAINTAIN.*

---

## 4. Sequence Privilege Verification

### 4.1 Scope of Inspection
Sequences inspected:
1. `public.sensor_readings_id_seq`
2. `public.maintenance_history_id_seq`

### 4.2 Effective Sequence Privileges via `has_sequence_privilege`
Queried individually for all key roles:

| Sequence Name | Role | `SELECT` | `USAGE` | `UPDATE` | Status |
| :--- | :--- | :-: | :-: | :-: | :-: |
| `sensor_readings_id_seq` | `anon` | `False` | `False` | `False` | **PASS** |
| `sensor_readings_id_seq` | `authenticated` | `False` | `False` | `False` | **PASS** |
| `sensor_readings_id_seq` | `postgres` | `True` | `True` | `True` | **PASS** |
| `sensor_readings_id_seq` | `service_role` | `True` | `True` | `True` | **PASS** |
| `maintenance_history_id_seq` | `anon` | `False` | `False` | `False` | **PASS** |
| `maintenance_history_id_seq` | `authenticated` | `False` | `False` | `False` | **PASS** |
| `maintenance_history_id_seq` | `postgres` | `True` | `True` | `True` | **PASS** |
| `maintenance_history_id_seq` | `service_role` | `True` | `True` | `True` | **PASS** |

### 4.3 Native Sequence Catalog ACL (`pg_class.relacl`)
- `sensor_readings_id_seq`: `{postgres=rwU/postgres,service_role=rwU/postgres}`
- `maintenance_history_id_seq`: `{postgres=rwU/postgres,service_role=rwU/postgres}`
  - `r` = `SELECT`
  - `w` = `UPDATE`
  - `U` = `USAGE`
- Zero sequence privileges exist for `anon` or `authenticated`.

---

## 5. RLS and Ownership Invariance Verification

| Object Name | Kind | Owner | `relrowsecurity` | `relforcerowsecurity` | Active Policies | Status |
| :--- | :---: | :---: | :-: | :-: | :-: | :-: |
| `machines` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `sensor_readings` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `alembic_version` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `maintenance_history` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `alerts` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `tickets` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `ticket_proposals` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `consumed_tokens` | Table | `postgres` | `True` | `False` | 0 | **PASS** |
| `sensor_readings_id_seq` | Sequence | `postgres` | N/A | N/A | N/A | **PASS** |
| `maintenance_history_id_seq` | Sequence | `postgres` | N/A | N/A | N/A | **PASS** |

- **Alembic Version Query:** `SELECT version_num FROM public.alembic_version;` $\rightarrow$ `['f3a9082b1c42']` (**PASS**).

---

## 6. Future Default Privileges Verification

Inspection of `pg_default_acl` on the live database:

| Creator Role | Target Schema | Object Type | Catalog ACL (`defaclacl`) | Assessment | Status |
| :--- | :--- | :-: | :--- | :--- | :-: |
| `postgres` | `public` | Tables (`r`) | `{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` | Hardened. Zero grants to `anon` or `authenticated`. | **PASS** |
| `postgres` | `public` | Sequences (`S`) | `{postgres=rwU/postgres,service_role=rwU/postgres}` | Hardened. Zero grants to `anon` or `authenticated`. | **PASS** |
| `postgres` | `public` | Functions (`f`) | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` | Standard function execution. Unmodified by Step 3C. | Informational |
| `supabase_admin` | `public` | Tables (`r`) | `{postgres=arwdDxtm/supabase_admin,anon=arwdDxtm/supabase_admin,authenticated=arwdDxtm/supabase_admin,service_role=arwdDxtm/supabase_admin}` | Cloud system defaults. Preserved as documented limitation. | Documented |
| `supabase_admin` | `public` | Sequences (`S`) | `{postgres=rwU/supabase_admin,anon=rwU/supabase_admin,authenticated=rwU/supabase_admin,service_role=rwU/supabase_admin}` | Cloud system defaults. Preserved as documented limitation. | Documented |

### Architectural Limitation & Policy:
As established in Steps 3C.0–3C.3, default privileges for Supabase's internal administrative role `supabase_admin` were intentionally not altered. All future schema migrations must be applied through version-controlled Alembic migrations executing as `postgres`. Creating application tables manually via Supabase Studio UI as `supabase_admin` would grant privileges to `anon`/`authenticated` and is strictly prohibited.

---

## 7. Deliverables Generated

- **Markdown Audit Report:**  
  [supabase_rls_step3c4_privilege_verification.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c4_privilege_verification.md)
- **Structured JSON Audit Report:**  
  [supabase_rls_step3c4_privilege_verification.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c4_privilege_verification.json)

---

## 8. Final Verdict

### Final Verdict: **`PASS — ALL PRIVILEGES INDEPENDENTLY VERIFIED`**

### Verdict Justification:
1. All eight tables have been independently verified via `has_table_privilege()`: `anon` and `authenticated` possess zero privileges across all eight privilege types (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`, `MAINTAIN`).
2. Both sequences have been independently verified: `anon` and `authenticated` possess zero privileges (`SELECT`, `USAGE`, `UPDATE`).
3. The discrepancy between 8 ACL letters (`arwdDxtm`) and 7 information-schema privileges (112 grants) was conclusively reconciled by the PostgreSQL 17 `MAINTAIN` privilege (`m`), which yields 128 total native grants in `aclexplode` vs. 112 SQL-standard grants in `information_schema`.
4. Role membership and `PUBLIC` grant audits confirmed zero indirect privilege paths.
5. Standard RLS is active on all eight tables with 0 policies (default-deny), FORCE RLS is disabled, and all objects remain owned by `postgres`.
6. Future default privileges for role `postgres` in schema `public` are hardened, ensuring future Alembic objects do not inherit API role grants.
7. Zero database mutations or Git state modifications occurred during this audit.
