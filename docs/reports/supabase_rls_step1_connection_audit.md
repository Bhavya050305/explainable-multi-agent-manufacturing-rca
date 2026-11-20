# ManuMind AI — Supabase RLS Remediation: Step 1 Connection Architecture Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Audit Target:** Supabase PostgreSQL Connection Architecture and Row Level Security (RLS) Baseline  
**Scope:** Strictly Read-Only Audit of Six Affected Tables Flagged by Supabase Security Advisor  
**Audit Date:** 2026-11-18  
**Overall Verdict:** `READY FOR RLS POLICY DESIGN`

---

## 1. Executive Summary

Supabase Security Advisor identified six public schema tables in the ManuMind AI database where Row Level Security (RLS) is currently disabled:
1. `public.machines`
2. `public.sensor_readings`
3. `public.alembic_version`
4. `public.maintenance_history`
5. `public.alerts`
6. `public.tickets`

When RLS is disabled in Supabase, any table residing in the `public` schema is exposed through Supabase's automatic PostgREST Data API (`https://<project-ref>.supabase.co/rest/v1/`). Consequently, anyone possessing the project's public `anon` API key could potentially perform unauthenticated read, write, update, or delete operations over HTTP.

This audit conducted an exhaustive, read-only inspection of the ManuMind AI backend codebase, configuration, models, migration scripts, and live database metadata to determine:
- How the backend connects to Supabase.
- Whether access occurs via PostgREST, direct PostgreSQL, or both.
- Which modules touch the six affected tables.
- The runtime database role and privilege level.
- Whether enabling RLS introduces any compatibility or operational risks to the backend application.

### Key Finding
**The ManuMind AI backend connects exclusively via direct PostgreSQL connections (port 5432 session pooler) using the administrative `postgres` table-owner role via SQLAlchemy.** It does **not** use the Supabase Python SDK (`create_client`), does **not** query PostgREST, does **not** use Supabase Auth, and the frontend currently contains no code.

Because PostgreSQL table owners and superusers bypass RLS by default (`BYPASSRLS`), **enabling standard Row Level Security on all six tables will immediately seal the public PostgREST attack surface with zero breakage or regression to the backend application.**

---

## 2. Supabase Connection Architecture & Driver Analysis

### 2.1 Configuration & Environment Invariants
- **Configuration File:** [`backend/app/config.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/config.py#L36-L38)
  - Line 37: `DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/manumind.db")`
  - Sensitive password credentials are masked via regex in `Settings.get_masked_database_url()` (lines 65–72).
  - No Supabase client environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) exist in `backend/app/config.py`, `.env.example`, or `.env`.

### 2.2 Connection String & Session Pooler Routing
- **Database Engine Implementation:** [`backend/app/database.py`](file:///D:/Desktop/FInal year project/manumind-ai/backend/app/database.py#L15-L68)
  - **Normalization:** `get_normalized_database_url()` (lines 15–43) automatically normalizes `postgres://` to `postgresql://`, checks driver availability between `psycopg` (v3) and `psycopg2`, and strictly appends `sslmode=require` if connecting to `pooler.supabase.com`.
  - **Host Domain:** `aws-0-ap-southeast-2.pooler.supabase.com`
  - **Port:** `5432` (Supabase Session Pooler)
  - **Protocol / Dialect:** `postgresql+psycopg://` / `postgresql+psycopg2://`
  - **Engine Optimization:**
    - `pool_pre_ping=True` (line 54) — validates active connection health before query execution.
    - `pool_recycle=300` (line 63) — recycles connections every 5 minutes to prevent pooler idle disconnects.
    - `pool_size=10`, `max_overflow=20` (lines 64–65).
    - `connect_timeout=10` (line 62).
  - **Session Factory:** `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)` (line 73).
  - **FastAPI Session Dependency:** `get_db() -> Generator[Session, None, None]` (lines 77–84).

### 2.3 PostgREST / Supabase Client SDK Inspection
A full repository codebase scan was executed:
- **`create_client` references:** `0 found`.
- **`supabase` SDK imports:** `0 found`.
- **`postgrest` client calls:** `0 found`.
- **`backend/requirements.txt`:** Does not include `supabase`, `postgrest`, or `gotrue`. It strictly specifies standard Python database drivers:
  - Line 4: `sqlalchemy>=2.0.0`
  - Line 5: `alembic>=1.12.0`
  - Line 6: `psycopg[binary]>=3.1.0`
  - Line 7: `psycopg2-binary>=2.9.0`

**Conclusion:** Access occurs **100% via direct PostgreSQL connection**. The PostgREST Data API is completely unused by the application.

---

## 3. Table-to-Module Access Mapping

The table below maps the six affected tables to their ORM models, accessing backend modules, operations, and file references:

| Table Name | ORM Model | Accessing Backend Modules | Access Nature | Source Locations |
| :--- | :--- | :--- | :--- | :--- |
| **`public.machines`** | `Machine` | • `backend/app/mcp_server/tools.py`<br>• `backend/app/mcp_server/server.py`<br>• `backend/app/mcp_server/schemas.py`<br>• `backend/migrate_sqlite_to_supabase.py`<br>• `backend/verify_migration.py`<br>• `backend/verify_step1.py` | Read telemetry metadata; validate machine IDs; migration and verification scripts | [`machine.py#L10-L25`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/machine.py#L10-L25)<br>[`tools.py#L212`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/tools.py#L212)<br>[`migrate_sqlite_to_supabase.py#L170-L184`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/migrate_sqlite_to_supabase.py#L170-L184) |
| **`public.sensor_readings`** | `SensorReading` | • `backend/app/mcp_server/tools.py`<br>• `backend/migrate_sqlite_to_supabase.py`<br>• `backend/verify_migration.py`<br>• `backend/verify_step1.py` | Query time-series telemetry window; batch insert 40,000 records; parity checks | [`sensor_reading.py#L11-L32`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/sensor_reading.py#L11-L32)<br>[`tools.py#L235-L265`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/tools.py#L235-L265)<br>[`migrate_sqlite_to_supabase.py#L186-L218`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/migrate_sqlite_to_supabase.py#L186-L218) |
| **`public.alembic_version`** | *None (Alembic DDL)* | • `backend/alembic/env.py`<br>• `backend/verify_step1.py` | Track active schema migration revision (`c742f9a1e0b5`); read version via raw SQL | [`alembic/env.py#L26-L30`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/alembic/env.py#L26-L30)<br>[`verify_step1.py#L21`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/verify_step1.py#L21) |
| **`public.maintenance_history`** | `MaintenanceHistory` | • `backend/app/mcp_server/tools.py`<br>• `backend/app/mcp_server/schemas.py`<br>• `backend/app/database.py`<br>• `backend/migrate_sqlite_to_supabase.py`<br>• `backend/verify_migration.py`<br>• `backend/verify_step1.py` | Read past maintenance records by machine; insert 400 historical records | [`maintenance_history.py#L11-L24`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/maintenance_history.py#L11-L24)<br>[`tools.py#L425-L450`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/tools.py#L425-L450)<br>[`migrate_sqlite_to_supabase.py#L221-L239`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/migrate_sqlite_to_supabase.py#L221-L239) |
| **`public.alerts`** | `Alert` | • `backend/app/mcp_server/tools.py`<br>• `backend/app/services/ticket_service.py`<br>• `backend/migrate_sqlite_to_supabase.py`<br>• `backend/verify_migration.py`<br>• `backend/verify_step1.py` | Read pending alerts; update alert status upon ticket authorization; insert 5 seed alerts | [`alert.py#L11-L29`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/alert.py#L11-L29)<br>[`ticket_service.py#L38-L41`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/services/ticket_service.py#L38-L41)<br>[`tools.py#L708-L720`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/tools.py#L708-L720) |
| **`public.tickets`** | `Ticket` | • `backend/app/services/ticket_service.py`<br>• `backend/app/mcp_server/tools.py`<br>• `backend/app/mcp_server/server.py`<br>• `backend/app/mcp_server/approval.py`<br>• `backend/migrate_sqlite_to_supabase.py`<br>• `backend/verify_migration.py`<br>• `backend/verify_step1.py` | Check existing tickets; insert approved maintenance tickets with human approval gate | [`ticket.py#L11-L26`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/models/ticket.py#L11-L26)<br>[`ticket_service.py#L43-L68`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/services/ticket_service.py#L43-L68)<br>[`tools.py#L901-L933`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/tools.py#L901-L933) |

---

## 4. Database Role & Runtime Privilege Audit

A live read-only diagnostic query was executed against the Supabase database:
```sql
SELECT current_user, session_user, current_database();
```
**Diagnostic Results:**
- `current_user`: **`postgres`**
- `session_user`: **`postgres`**
- `current_database`: **`postgres`**

A live metadata query was executed against `pg_tables` and `pg_policies`:
```sql
SELECT schemaname, tablename, tableowner, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('machines', 'sensor_readings', 'alembic_version', 'maintenance_history', 'alerts', 'tickets')
ORDER BY tablename;
```
**Live Status Table:**
| Table | Table Owner | `rowsecurity` (RLS Enabled?) | Active Policies in `pg_policies` |
| :--- | :---: | :---: | :---: |
| `public.alembic_version` | `postgres` | `False` | 0 |
| `public.alerts` | `postgres` | `False` | 0 |
| `public.machines` | `postgres` | `False` | 0 |
| `public.maintenance_history` | `postgres` | `False` | 0 |
| `public.sensor_readings` | `postgres` | `False` | 0 |
| `public.tickets` | `postgres` | `False` | 0 |

### Privilege Analysis
1. In PostgreSQL, the `postgres` user is a superuser and the explicit owner of all six tables (`tableowner = postgres`).
2. By default in PostgreSQL, table owners and superusers have the `BYPASSRLS` attribute.
3. Therefore, standard `ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;` **does NOT apply to the table owner (`postgres`)** unless `FORCE ROW LEVEL SECURITY` is explicitly turned on.
4. Conversely, PostgREST requests authenticate as the `anon` or `authenticated` roles. These roles do NOT have `BYPASSRLS`. Once RLS is enabled, any request via PostgREST without a matching policy receives default-deny (0 rows returned on SELECT, error on mutation).

---

## 5. Supabase Auth & JWT Implementation Status

### 5.1 Supabase Auth Inspection
- **GoTrue / Supabase Auth:** Physically absent from the repository.
- **Supabase User Sessions:** None.
- **Supabase JWT Verification:** The backend does not validate Supabase JWT tokens.

### 5.2 Application-Level Authorization Gate
In Phase 4 Step 6, an application-level human-authorization gate was implemented:
- **Module:** [`backend/app/mcp_server/approval.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/mcp_server/approval.py#L154-L334)
- **Token Format:** HS256 JWT-structured token signed with `HMAC-SHA256` using the environment secret `MANUMIND_APPROVAL_SECRET_KEY`.
- **Purpose:** Cryptographically binds a human engineer's approval to a specific `proposal_id` and canonical `payload_hash` before a maintenance ticket can be created.
- **Independence:** This token mechanism is completely decoupled from Supabase Auth and operates purely at the application service layer.

---

## 6. Frontend vs. Backend Access Analysis

1. **Frontend Repository State:**
   - The directory `frontend/` was inspected: it is currently **completely empty** (0 files, uninitialized).
   - No React, Next.js, or Supabase client code exists in the repository.
2. **API Routing:**
   - In `.env.example` and `.env`, `NEXT_PUBLIC_API_URL` is set to `http://localhost:8000`.
   - The planned architecture routes all UI traffic through the FastAPI backend gateway, which in turn coordinates with the database and MCP multi-agent tools.
3. **Frontend Direct Access:**
   - There is **no frontend direct connection** to Supabase or PostgREST.

---

## 7. `alembic_version` Isolation Analysis

- `public.alembic_version` is created and used exclusively by Alembic (`backend/alembic/env.py`) to record the applied migration version hash (currently `c742f9a1e0b5`).
- The only other query in the codebase is in `backend/verify_step1.py` (line 21), which reads `SELECT version_num FROM alembic_version;` for deployment verification.
- **Exposure Risk:** Exposing `alembic_version` over the public PostgREST API leaks internal database schema version numbers and migration metadata to unauthenticated external actors.
- **Safety of Enabling RLS:** Enabling RLS on `alembic_version` prevents unauthenticated PostgREST scraping while Alembic continues running migrations unimpeded as role `postgres`.

---

## 8. Compatibility Risk Assessment of Enabling RLS

```
   [ External Internet / PostgREST ]                  [ ManuMind AI Backend ]
               |                                                 |
         Anon API Key                                   SQLAlchemy Session Pooler
               |                                                 |
         Role: `anon`                                     Role: `postgres`
               |                                                 |
               v                                                 v
    +-------------------------------------------------------------------------+
    |                    PostgreSQL Row Level Security (RLS)                  |
    |                                                                         |
    |  • Role `anon`: Subject to RLS (Default Deny -> 0 rows / Blocked)       |
    |  • Role `postgres`: BYPASSRLS / Table Owner (Full Access Unhindered)     |
    +-------------------------------------------------------------------------+
                                       |
                                       v
                             [ Public Schema Tables ]
                     machines | sensor_readings | alerts
                     tickets  | maintenance_history | alembic_version
```

### Risk Evaluation Matrix

| Action / Configuration | Impact on PostgREST (Internet) | Impact on Backend Application | Risk Level |
| :--- | :--- | :--- | :---: |
| **`ENABLE ROW LEVEL SECURITY`** (Recommended) | **Blocked** (Default Deny: 0 rows returned, no mutations allowed) | **Zero Impact** (`postgres` role bypasses RLS) | **LOW (Safe)** |
| **`FORCE ROW LEVEL SECURITY`** (DO NOT USE) | Blocked | **Critical Failure** (Backend queries fail unless explicit policies for `postgres` exist) | **HIGH (Dangerous)** |
| **Do Nothing** (Current State) | **Open Vulnerability** (Unauthenticated anon can read/write all 6 tables) | Works normally | **CRITICAL (Security Risk)** |

---

## 9. Recommended Access-Control Architecture & Policy Strategy

For Step 2 (Policy Design and Migration Execution), the following architecture is recommended:

1. **Execute Standard Enable RLS on All Six Tables:**
   ```sql
   ALTER TABLE public.machines ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.sensor_readings ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.maintenance_history ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
   ```
2. **Strictly Avoid `FORCE ROW LEVEL SECURITY`:**
   Ensure table owner `postgres` maintains seamless access through the session pooler.
3. **Explicit Default-Deny Policy for PostgREST Roles (`anon`, `authenticated`):**
   In Supabase, enabling RLS with no policies produces an automatic default-deny for `anon` and `authenticated`. To be formally explicit and satisfy strict security audits, create restrictive policies denying access or granting access strictly to `service_role` (if PostgREST API access is ever needed internally).
4. **Implementation via Alembic Migration:**
   Package the remediation into a standard Alembic migration script in `backend/alembic/versions/` so that the change is version-controlled, repeatable, and reversible.

---

## 10. Dashboard Verification Items

Before executing Step 2 remediation, the following items should be verified in the Supabase Management Console:
1. **API Settings:** Navigate to *Project Settings > API*. Confirm that the Data API (PostgREST) is active and note whether the public `anon` key has been distributed anywhere.
2. **Database Users:** Navigate to *Project Settings > Database*. Verify that the connection user in `DATABASE_URL` matches the administrative table owner `postgres`.
3. **Third-Party Integrations:** Confirm that no external third-party tools, dashboards, or webhooks currently read from Supabase via PostgREST URLs.

---

## 11. Final Milestone Verdict

### Verdict: `READY FOR RLS POLICY DESIGN`

**Justification:**
1. The backend connection architecture has been comprehensively mapped and verified against both source files and the live Supabase database.
2. The application relies 100% on direct PostgreSQL connections as the table owner `postgres`, with zero dependence on PostgREST, Supabase Client SDK, or Supabase Auth.
3. Enabling standard Row Level Security on the six affected tables will completely remediate the Supabase Security Advisor findings without causing regressions or breaking existing backend functionality.
