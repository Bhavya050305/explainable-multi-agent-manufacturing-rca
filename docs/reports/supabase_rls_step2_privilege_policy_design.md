# ManuMind AI — Supabase RLS Remediation: Step 2 — Independent PostgreSQL Privilege and RLS Policy Design Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Audit Target:** PostgreSQL Catalog Privilege Verification & Row Level Security (RLS) Policy Design  
**Previous Milestone:** Step 1 — Connection Architecture Audit (`READY FOR RLS POLICY DESIGN`)  
**Scope:** Strictly Read-Only Audit of Six Flagged Tables (`machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, `tickets`)  
**Audit Date:** 2026-11-18  
**Final Verdict:** `READY FOR CONTROLLED RLS MIGRATION`

---

## 1. Executive Summary

Following Step 1's architecture audit, this independent Step 2 audit directly interrogated the live PostgreSQL system catalogs (`pg_roles`, `pg_auth_members`, `pg_class`, `pg_namespace`, `pg_tables`, `pg_policies`, `pg_default_acl`, and `information_schema.role_table_grants`) in Supabase.

### Primary Audit Findings
1. **Connection Role Attributes:** The backend's connecting role `postgres` is **not a superuser** (`rolsuper = False` in Supabase Cloud), but it possesses **`rolbypassrls = True`** and is the explicit **table owner** (`tableowner = postgres`) of all six tables.
2. **Root Cause of PostgREST Exposure:** In Supabase's default configuration (`pg_default_acl`), tables created in the `public` schema by the `postgres` role automatically receive a broad grant:
   `acl = {postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm}`.
   Because Row Level Security is currently disabled on all six tables (`relrowsecurity = False`), the PostgREST Data API (which executes as `authenticator` -> `anon`) currently has **unrestricted CRUD access** over HTTP using the public `anon` key.
3. **Safety of Enabling Standard RLS:** Because `postgres` has `rolbypassrls = True` and owns the tables, executing standard `ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;` **will not restrict backend SQLAlchemy queries**. PostgREST requests (which execute as non-bypass roles `anon` and `authenticated`) will immediately be subjected to default-deny (0 rows returned, mutations blocked).
4. **Strict Safety Prohibition:** `FORCE ROW LEVEL SECURITY` **must NEVER be enabled**. It would enforce RLS on the table owner and risk breaking the backend.

---

## 2. Verified PostgreSQL Role Details

The current connection was interrogated using live queries against `pg_roles` and PostgreSQL system functions:

```sql
SELECT 
    r.rolname,
    r.rolsuper,
    r.rolinherit,
    r.rolcreaterole,
    r.rolcreatedb,
    r.rolcanlogin,
    r.rolbypassrls,
    current_user,
    session_user,
    current_database(),
    inet_server_port()
FROM pg_roles r
WHERE r.rolname = current_user;
```

### Verified Attributes for Connecting Role (`postgres`)
| Attribute | Verified Value | Architectural Significance |
| :--- | :---: | :--- |
| **`rolname`** | `postgres` | Matches database username in `DATABASE_URL`. |
| **`rolsuper`** | `False` | In Supabase Cloud, `postgres` is a tenant admin, not a raw cluster superuser (`supabase_admin` holds `rolsuper=True`). |
| **`rolinherit`** | `True` | Inherits permissions from assigned parent roles. |
| **`rolcreaterole`** | `True` | Permitted to manage database roles. |
| **`rolcreatedb`** | `True` | Permitted to manage databases. |
| **`rolcanlogin`** | `True` | Valid login account. |
| **`rolbypassrls`** | **`True`** | **Critical:** The `postgres` role explicitly bypasses Row Level Security rules by default across the entire database. |
| **`current_user`** | `postgres` | Active execution role. |
| **`session_user`** | `postgres` | Active session authentication identity. |
| **`current_database`** | `postgres` | Target database catalog. |
| **`inet_server_port`** | `5432` | Connected via the Supabase Session Pooler. |

### Supabase Platform Roles Comparison
Interrogation of all platform roles via `pg_roles` and `pg_auth_members` confirmed:

| Role Name | `rolsuper` | `rolcanlogin` | `rolbypassrls` | Role Description / Member Of |
| :--- | :---: | :---: | :---: | :--- |
| **`postgres`** | `False` | `True` | **`True`** | Backend application connection user; table owner |
| **`service_role`** | `False` | `False` | **`True`** | Elevated API role for server-side trusted scripts |
| **`supabase_admin`** | `True` | `True` | **`True`** | Cloud infrastructure master administrative superuser |
| **`anon`** | `False` | `False` | `False` | Public unauthenticated PostgREST role |
| **`authenticated`** | `False` | `False` | `False` | Logged-in Supabase Auth user PostgREST role |
| **`authenticator`** | `False` | `True` | `False` | PostgREST entrypoint role (switches to `anon`/`authenticated`) |
| **`dashboard_user`** | `False` | `False` | `False` | Supabase Studio web dashboard role |

**Catalog Verification:** `pg_auth_members` confirms that `authenticator` is a member of `anon`, `authenticated`, and `service_role`. When an incoming API request hits PostgREST, `authenticator` executes `SET LOCAL ROLE <target_role>`.

---

## 3. Six-Table Ownership and Grants Matrix

A complete query across `pg_class`, `pg_namespace`, and `information_schema.role_table_grants` was executed for all six flagged tables.

### Table Ownership & ACL Matrix (`pg_class`)
```sql
SELECT 
    c.relname,
    pg_get_userbyid(c.relowner) AS owner,
    c.relrowsecurity,
    c.relforcerowsecurity,
    c.relacl
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('machines', 'sensor_readings', 'alembic_version', 'maintenance_history', 'alerts', 'tickets')
ORDER BY c.relname;
```

**Observed State:**
| Table Name | Owner | `relrowsecurity` | `relforcerowsecurity` | `relacl` (PostgreSQL Access Control List) |
| :--- | :---: | :---: | :---: | :--- |
| **`alembic_version`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |
| **`alerts`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |
| **`machines`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |
| **`maintenance_history`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |
| **`sensor_readings`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |
| **`tickets`** | `postgres` | `False` | `False` | `{postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` |

*Key to `arwdDxtm`:*
- `a` = `INSERT` (append)
- `r` = `SELECT` (read)
- `w` = `UPDATE` (write)
- `d` = `DELETE`
- `D` = `TRUNCATE`
- `x` = `REFERENCES`
- `t` = `TRIGGER`
- `m` = `MAINTAIN`

### Detailed Privilege Breakdown (`information_schema.role_table_grants`)
For every one of the six tables, `role_table_grants` lists 28 total grants (7 privileges across 4 roles = 168 total grants):
- **`postgres`:** Has `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` (`grantable = YES`).
- **`anon`:** Has `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` (`grantable = NO`).
- **`authenticated`:** Has `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` (`grantable = NO`).
- **`service_role`:** Has `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` (`grantable = NO`).

---

## 4. RLS and FORCE RLS Baseline Analysis

- **`relrowsecurity` (RLS Enabled):** Confirmed `False` on all six tables.
- **`relforcerowsecurity` (FORCE RLS):** Confirmed `False` on all six tables.

### Understanding the RLS Enforcement Boundary

```
                     Incoming SQL Statement
                               |
                               v
            +------------------------------------+
            |      Table-Level SQL Grants        |
            | (Does role have SELECT/INSERT etc?) |
            +-----------------+------------------+
                              | YES
                              v
            +------------------------------------+
            |        Is RLS Enabled on Table?    |
            +-----------------+------------------+
                     | NO               | YES
                     |                  v
                     |       +------------------------------------+
                     |       | Does Role Have BYPASSRLS or Owner? |
                     |       +-----------------+------------------+
                     |                | YES              | NO
                     |                v                  v
                     |        [ Bypass RLS ]     +----------------------------------+
                     |        (Direct Access)    | Do Permissive RLS Policies Exist?|
                     |                           +-----------------+----------------+
                     |                                    | NO             | YES
                     v                                    v                v
             [ Execute Query ]                     [ Default Deny ]   [ Filtered ]
                                                   (0 rows / error)   (Only matching)
```

1. **When RLS is Disabled (`relrowsecurity = False`):**
   PostgreSQL checks only table-level grants. Because `anon` was granted `arwdDxtm`, `anon` has complete read/write access.
2. **When Standard RLS is Enabled (`relrowsecurity = True`, `relforcerowsecurity = False`):**
   - Non-bypass roles (`anon`, `authenticated`) must satisfy an RLS policy. In the absence of policies, **default-deny** applies.
   - Roles with `BYPASSRLS` (`postgres`, `service_role`) bypass policy evaluation entirely.
3. **If FORCE RLS Were Enabled (`relforcerowsecurity = True`):**
   PostgreSQL subjects the table owner to RLS policies. This must be avoided to prevent accidental query breakage for the backend.

---

## 5. Existing Policy Inventory

A query was executed against `pg_policies`:
```sql
SELECT schemaname, tablename, policyname, roles, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';
```
**Result:** **0 policies found**. There are currently no active RLS policies in the `public` schema.

---

## 6. Supabase Data API Exposure Assessment

### 6.1 Why the Tables are Exposed
1. **Schema USAGE Grant:** `pg_namespace.nspacl` reveals that `public` grants `USAGE` to `anon`, `authenticated`, and `PUBLIC` (`=U/pg_database_owner`).
2. **Default Table Privileges:** `pg_default_acl` automatically assigns `ALL PRIVILEGES` to `anon` and `authenticated` on every table created by `postgres`.
3. **PostgREST Architecture:** PostgREST automatically inspects the OpenAPI schema of `public`. Any table in `public` with table-level grants and RLS disabled is exposed as an active REST endpoint.
4. **Current Vulnerability State:**
   - `GET /rest/v1/machines` => Returns all industrial machine definitions.
   - `GET /rest/v1/sensor_readings` => Returns all 40,000 industrial telemetry records.
   - `GET /rest/v1/maintenance_history` => Returns all 400 maintenance logs.
   - `GET /rest/v1/alerts` => Returns all plant alerts.
   - `GET /rest/v1/tickets` => Returns tickets, and permits unauthorized insertion bypassing the backend's HMAC human-approval gate!
   - `GET /rest/v1/alembic_version` => Leaks internal database schema version hash (`c742f9a1e0b5`).

---

## 7. Backend Compatibility Analysis

### Why the ManuMind Backend is 100% Immune to RLS Disruption
The backend application connects using SQLAlchemy through the session pooler:
- **Connection Role:** `postgres`.
- **Role Invariants Verified:**
  1. `rolbypassrls = True`: By PostgreSQL specification, any user with `BYPASSRLS` is completely exempt from row-level security checks.
  2. `tableowner = postgres`: `postgres` is the owner of `machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, and `tickets`.
- **Operational Reality:**
  - Standard `ENABLE ROW LEVEL SECURITY` has **zero impact** on queries issued by `postgres`.
  - Machine telemetry queries in `get_machine_data` will return identical records.
  - Anomaly detection, defect classification, and ticket proposal generation will run without permission errors.
  - Alembic migrations (`alembic upgrade head`) execute as `postgres` and will continue creating, modifying, and updating `alembic_version` unhindered.

---

## 8. Table-by-Table Target State Design

| Table Name | Target RLS State | Target FORCE RLS | `anon` Access | `authenticated` Access | `postgres` Access | Table Grants Remediation | Target Policy Requirement |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **`public.machines`** | **ENABLED** | **DISABLED** | Deny (0 rows) | Deny (0 rows) | Full Access (`BYPASSRLS`) | Retain standard Supabase table grants; rely on RLS default-deny. | **No policy needed** (Default-deny secures table; future Phase 6 will design read-only policies for authenticated operators). |
| **`public.sensor_readings`** | **ENABLED** | **DISABLED** | Deny (0 rows) | Deny (0 rows) | Full Access (`BYPASSRLS`) | Retain standard table grants; rely on RLS default-deny. | **No policy needed** (Default-deny prevents bulk scraping of proprietary manufacturing sensor data). |
| **`public.alembic_version`** | **ENABLED** | **DISABLED** | Deny | Deny | Full Access (`BYPASSRLS`) | **Revoke table grants:** `REVOKE ALL ON public.alembic_version FROM anon, authenticated;` | **No policy needed** (Internal DDL tooling table; completely isolated from Data API). |
| **`public.maintenance_history`** | **ENABLED** | **DISABLED** | Deny (0 rows) | Deny (0 rows) | Full Access (`BYPASSRLS`) | Retain standard table grants; rely on RLS default-deny. | **No policy needed** (Default-deny secures past repair and incident records). |
| **`public.alerts`** | **ENABLED** | **DISABLED** | Deny (0 rows) | Deny (0 rows) | Full Access (`BYPASSRLS`) | Retain standard table grants; rely on RLS default-deny. | **No policy needed** (Default-deny prevents external tampering with anomaly alert states). |
| **`public.tickets`** | **ENABLED** | **DISABLED** | Deny | Deny | Full Access (`BYPASSRLS`) | Retain standard table grants; rely on RLS default-deny. | **No policy needed** (CRITICAL: Prevents bypassing Phase 4 Step 6 HMAC human authorization gate). |

---

## 9. Proposed Migration Plan (Alembic Design)

The remediation should be implemented as an official, tracked Alembic migration:
`backend/alembic/versions/<revision>_enable_rls_on_public_tables.py`

### Proposed Migration Code (`upgrade()` and `downgrade()`)
```python
"""enable rls on public tables

Revision ID: e4b19082a5c1
Revises: c742f9a1e0b5
Create Date: 2026-11-18 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'e4b19082a5c1'
down_revision: Union[str, None] = 'c742f9a1e0b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AFFECTED_TABLES = [
    "machines",
    "sensor_readings",
    "alembic_version",
    "maintenance_history",
    "alerts",
    "tickets"
]

def upgrade() -> None:
    # 1. Enable standard Row Level Security on all six public tables
    for table in AFFECTED_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

    # 2. Defense-in-depth: Revoke Data API access from internal migration metadata
    op.execute("REVOKE ALL ON public.alembic_version FROM anon, authenticated;")


def downgrade() -> None:
    # 1. Restore table grants on alembic_version
    op.execute("GRANT ALL ON public.alembic_version TO anon, authenticated;")

    # 2. Disable Row Level Security on all six public tables
    for table in reversed(AFFECTED_TABLES):
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
```

---

## 10. Rollback and Verification Plan

### Pre-Migration Verification Query
```sql
SELECT tablename, rowsecurity, tableowner 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('machines', 'sensor_readings', 'alembic_version', 'maintenance_history', 'alerts', 'tickets')
ORDER BY tablename;
```
*Expected Pre-migration:* `rowsecurity = False` for all 6 tables.

### Post-Migration Verification Query
```sql
SELECT 
    c.relname,
    c.relrowsecurity,
    c.relforcerowsecurity,
    pg_get_userbyid(c.relowner) AS owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('machines', 'sensor_readings', 'alembic_version', 'maintenance_history', 'alerts', 'tickets')
ORDER BY c.relname;
```
*Expected Post-migration:*
- `relrowsecurity = True` (RLS active)
- `relforcerowsecurity = False` (Table owner retains bypass)
- `owner = postgres`

### Post-Migration Functional Integrity Check
Execute backend diagnostic and verification scripts:
```powershell
python backend/test_connection.py
python backend/verify_migration.py
```
*Pass Criteria:* All 40,416 rows must remain queryable with zero latency degradation or permissions errors.

---

## 11. Unknowns Requiring Dashboard Confirmation

The following settings reside in the Supabase Cloud Management Dashboard and cannot be configured via SQL alone:
1. **Exposed Schemas Configuration:** Confirm in *Supabase Dashboard > Project Settings > API* that `public` is listed under "Exposed schemas" and observe that the Security Advisor warnings drop from 6 to 0 once RLS is enabled.
2. **PostgREST API Exposure:** Verify whether the public `anon` key is exposed to any client or published documentation.
3. **Future Auth Architecture:** When frontend development begins (Phase 6), determine whether operators will authenticate via Supabase Auth (GoTrue) or whether the UI will strictly communicate through the FastAPI backend API.

---

## 12. Database Catalogs and Files Inspected

- **PostgreSQL System Catalogs Interrogated:**
  - `pg_roles`
  - `pg_auth_members`
  - `pg_class`
  - `pg_namespace`
  - `pg_tables`
  - `pg_policies`
  - `pg_default_acl`
  - `information_schema.role_table_grants`
  - `information_schema.role_column_grants`
  - `information_schema.schemata`
- **Source Files Inspected:**
  - `backend/app/config.py`
  - `backend/app/database.py`
  - `backend/app/models/` (`machine.py`, `sensor_reading.py`, `maintenance_history.py`, `alert.py`, `ticket.py`, `ticket_proposal.py`)
  - `backend/alembic/env.py`
  - `backend/requirements.txt`
  - `backend/verify_migration.py`
  - `backend/test_connection.py`

---

## 13. Confirmation of Read-Only Execution

- **Zero database mutations:** No `ALTER`, `CREATE`, `DROP`, `GRANT`, `REVOKE`, `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` queries were executed.
- **Zero code changes:** No source code, configuration files, environment variables, or migration files were created or modified.
- **Git state preserved:** Working tree remains completely intact.

---

## 14. Final Verdict

### Final Verdict: `READY FOR CONTROLLED RLS MIGRATION`

**Summary Statement:**  
The independent catalog audit confirmed that `postgres` holds `rolbypassrls = True` and owns all six affected tables. Standard `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` completely eliminates the PostgREST anonymous exposure while guaranteeing 100% backward compatibility and seamless operation for the ManuMind AI backend.
