# ManuMind AI — Supabase RLS Remediation: Step 3C.0 Independent Least-Privilege Privilege-Hardening Design Audit Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Live Revision:** `1273f18b72a2`  
**Pending Head:** `e4b19082a5c1`  
**Milestone:** Phase 5 — Supabase Security Remediation (Step 3C.0)  
**Date:** 2026-11-18  
**Audit Target:** Independent Design and Catalog Verification for Step 3C Least-Privilege Hardening  
**Audit Type:** Strictly Read-Only Architectural and Catalog Audit  
**Final Verdict:** `APPROVED FOR STEP 3C MIGRATION PREPARATION`

---

## 1. Executive Summary

This independent read-only audit evaluated the proposed **Step 3C least-privilege privilege-hardening strategy** following the completion of the Step 3B pre-execution reviews.

While the Step 3B.1 remediation establishes Row Level Security (RLS) across all eight public tables, PostgreSQL catalog inspection revealed that Supabase cloud default access controls (`pg_default_acl`) have assigned broad table privileges (`arwdDxtm`: SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN) to API roles `anon` and `authenticated`.

### Crucial Architectural Insights:
1. **The RLS TRUNCATE Blindspot:** PostgreSQL documentation explicitly specifies that **`TRUNCATE` is not subject to Row Level Security**. RLS controls row-level DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), but table-level `TRUNCATE` completely bypasses row filtering. As long as `D` (`TRUNCATE`) is granted to `anon` and `authenticated`, the database remains vulnerable to table clearing via internal procedures or direct SQL access.
2. **Complete Sequence Inventory Established:** Deep catalog queries established that schema `public` contains **exactly two sequences**: `sensor_readings_id_seq` and `maintenance_history_id_seq`. Both currently grant `rwU` (USAGE, SELECT, UPDATE) to `anon` and `authenticated`.
3. **Zero Public Grants & Zero Global Defaults:** Live inspection confirmed that zero grants exist to pseudo-role `PUBLIC` on tables or sequences, and zero global default ACLs exist (`defaclnamespace = 0`). Consequently, revoking direct grants from `anon` and `authenticated` eliminates 100% of their table and sequence access without residual inherited paths.
4. **Backend Application Zero Disruption:** The ManuMind backend connects exclusively over direct TCP/SQLAlchemy as role `postgres` (`rolbypassrls = True`, table owner). The backend has zero dependency on PostgREST, Supabase Python SDK, or roles `anon`/`authenticated`. Revoking privileges from API roles is 100% non-breaking for backend operations.
5. **Unified Atomic Execution Opportunity:** Because Alembic runs migrations within a single atomic PostgreSQL transaction, preparing the Step 3C migration now allows applying all three pending migrations (`c742f9a1e0b5`, `e4b19082a5c1`, and Step 3C) in a **single atomic transaction**, ensuring zero window of exposure.

---

## 2. Baseline Verification

Read-only inspection of repository files, Alembic configuration, and the live Supabase catalog confirmed:

| Verification Item | Target Requirement | Actual State | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Tree** | Branch `main`, HEAD `a1e7e77` | Verified clean; HEAD matches `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | Confirmed |
| **Live Database Revision** | Must be baseline `1273f18b72a2` | Query on `public.alembic_version` returned `['1273f18b72a2']` | Confirmed |
| **Alembic Heads** | Exactly 1 head | `e4b19082a5c1 (head)` | Confirmed |
| **Alembic DAG Ancestry** | Linear single chain | `<base> -> 1273f18b72a2 -> c742f9a1e0b5 -> e4b19082a5c1 (head)` | Confirmed |
| **RLS Scope in `e4b19082a5c1`** | Exactly 8 public tables | Verified: `machines`, `sensor_readings`, `alembic_version`, `maintenance_history`, `alerts`, `tickets`, `ticket_proposals`, `consumed_tokens` | Confirmed |
| **Pending Migration Invariants** | Zero transaction anomalies | No explicit `commit()`, autocommit blocks, or transaction boundary alterations in either pending migration | Confirmed |

---

## 3. Comprehensive Table Privilege Inspection

### 3.1 Live Catalog Audit (`pg_class.relacl`, `pg_roles`, `pg_auth_members`)
Direct read-only queries against PostgreSQL catalogs confirmed privileges for all eight target tables:

| Table Name | Role | SELECT (`r`) | INSERT (`a`) | UPDATE (`w`) | DELETE (`d`) | TRUNCATE (`D`) | REFERENCES (`x`) | TRIGGER (`t`) | Owner | `rolbypassrls` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`machines`** | `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`sensor_readings`** | `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`alembic_version`** | `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`maintenance_history`**| `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`alerts`** | `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`tickets`** | `postgres` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `postgres` | **YES** |
| | `anon` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `authenticated` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | NO |
| | `service_role` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | - | **YES** |
| **`ticket_proposals`** *(pending)* | *(Inherits `arwdDxtm` upon creation via `pg_default_acl`)* | | | | | | | | `postgres` | *(Same)* |
| **`consumed_tokens`** *(pending)* | *(Inherits `arwdDxtm` upon creation via `pg_default_acl`)* | | | | | | | | `postgres` | *(Same)* |

### 3.2 Indirect & Inherited Privilege Analysis
- **Grants to Pseudo-Role `PUBLIC`:** Queried `information_schema.role_table_grants WHERE grantee = 'PUBLIC'`. Returned **`[]` (0 rows)**. No table privileges are granted to `PUBLIC`.
- **Role Memberships (`pg_auth_members`):**
  - Queried role memberships for `anon` and `authenticated`.
  - Roles `anon` and `authenticated` are **NOT members of any privileged role**.
  - `authenticator` (used by PostgREST) is a member of `anon`, `authenticated`, and `service_role` (allowing it to switch role via `SET LOCAL ROLE`).
  - Neither `anon` nor `authenticated` inherits permissions from `postgres`, `pg_database_owner`, or `supabase_admin`.
- **Conclusion:** Revoking table privileges directly from `anon` and `authenticated` cleanly and completely strips all permissions. There are no secondary or shadow privilege paths.

---

## 4. Sequence Catalog Inventory

A complete catalog scan of `pg_class WHERE relkind = 'S'` across schema `public` discovered **exactly two sequences**:

| Sequence Name | Owning Table & Column | Sequence Owner | Active ACL | Privileges Granted to `anon` & `authenticated` |
| :--- | :--- | :--- | :--- | :--- |
| **`public.sensor_readings_id_seq`** | `sensor_readings.id` | `postgres` | `{postgres=rwU, anon=rwU, authenticated=rwU, service_role=rwU}` | `USAGE`, `SELECT`, `UPDATE` |
| **`public.maintenance_history_id_seq`** | `maintenance_history.id` | `postgres` | `{postgres=rwU, anon=rwU, authenticated=rwU, service_role=rwU}` | `USAGE`, `SELECT`, `UPDATE` |

### Sequence Hardening Requirements:
- The other six tables (`machines`, `alembic_version`, `alerts`, `tickets`, `ticket_proposals`, `consumed_tokens`) use alphanumeric identifiers (`VARCHAR(50)`, UUIDs, or strings) and have no underlying sequences.
- `anon` and `authenticated` possess `rwU` on both sequences. This permits calling `nextval()`, `currval()`, or `setval()`, exposing sequences to denial-of-service sequence exhaustion.
- **Both sequences must be included in the Step 3C revocation scope.**

---

## 5. Comprehensive Default Privileges Analysis

Inspection of `pg_default_acl` across all catalog entries confirmed:
1. **Global Default ACLs:** Exactly **0 global default ACLs** exist (`defaclnamespace = 0` returned 0 rows).
2. **Schema-Scoped Default ACLs for `public`:**
   - **Creator Role `postgres`:**
     - Tables (`r`): `{postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm}`
     - Sequences (`S`): `{postgres=rwU, anon=rwU, authenticated=rwU, service_role=rwU}`
     - Functions (`f`): `{postgres=X, anon=X, authenticated=X, service_role=X}`
   - **Creator Role `supabase_admin`:**
     - Tables (`r`), Sequences (`S`), Functions (`f`) replicate the same default ACL grants.

### Default Privilege Hardening Evaluation:
Executing:
```sql
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
```
- **Sufficiency Analysis:** Because all application migrations and tables in ManuMind AI are created by role `postgres` (via `DATABASE_URL`), altering default privileges for `ROLE postgres IN SCHEMA public` guarantees that any table or sequence created in future phases will start with **zero privileges** for `anon` and `authenticated`.
- Because there are zero global default ACLs, no global rule can override or bypass this schema-specific revocation.

---

## 6. Least-Privilege Migration Design (Step 3C)

### 6.1 Proposed Migration Specification
- **Revision Identifier:** Pinned to follow `e4b19082a5c1` (e.g. `f3a9082b1c42`).
- **Down Revision:** `e4b19082a5c1`.
- **Target Schema:** `public`.

### 6.2 Proposed `upgrade()` Statements and Justification

```python
def upgrade() -> None:
    # 1. Revoke all table-level privileges on all eight public tables from API roles
    op.execute(
        "REVOKE ALL ON TABLE "
        "public.machines, "
        "public.sensor_readings, "
        "public.alembic_version, "
        "public.maintenance_history, "
        "public.alerts, "
        "public.tickets, "
        "public.ticket_proposals, "
        "public.consumed_tokens "
        "FROM anon, authenticated;"
    )

    # 2. Revoke all sequence-level privileges on all public sequences from API roles
    op.execute(
        "REVOKE ALL ON SEQUENCE "
        "public.sensor_readings_id_seq, "
        "public.maintenance_history_id_seq "
        "FROM anon, authenticated;"
    )

    # 3. Alter future default privileges for role postgres on tables in schema public
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON TABLES FROM anon, authenticated;"
    )

    # 4. Alter future default privileges for role postgres on sequences in schema public
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON SEQUENCES FROM anon, authenticated;"
    )
```

### Detailed Statement Justifications:
1. **Revoke Table Privileges:** Removes `arwdDxtm`. Directly eliminates the `TRUNCATE` vulnerability and denies any table-level operations to API roles.
2. **Revoke Sequence Privileges:** Removes `rwU`. Prevents unauthorized sequence consumption, reading, or tampering.
3. **Alter Default Privileges (Tables):** Prevents future tables created by `postgres` from automatically inheriting grants for `anon` or `authenticated`.
4. **Alter Default Privileges (Sequences):** Prevents future sequences from granting automatic permissions to API roles.

### 6.3 Downgrade Strategy (Rollback Considerations)
- **Strict Downgrade Security Mandate:** Downgrading must **NEVER** blindly execute `GRANT ALL ON ... TO anon, authenticated;`. Restoring `GRANT ALL` reintroduces the `TRUNCATE` vulnerability.
- **Recommended Architectural Rollback Design:**
  - Least-privilege hardening is an architectural security baseline. In Alembic, `downgrade()` should either:
    - Log an explicit warning that privilege hardening remains in place for security reasons; **OR**
    - Raise an exception (`NotImplementedError`) requiring explicit administrative authorization if table grants ever need to be restored.
  - If emergency operational rollback is mandated, default privileges can be re-aligned symmetrically:
    ```python
    def downgrade() -> None:
        # Re-align default privileges if operational rollback is authorized
        op.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
            "GRANT ALL ON TABLES TO anon, authenticated;"
        )
        op.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
            "GRANT ALL ON SEQUENCES TO anon, authenticated;"
        )
        # Table-level grants are intentionally NOT broadly restored to prevent TRUNCATE exposure.
    ```

---

## 7. Supabase API and RLS Compatibility Assessment

### Access Layer Architecture:

```
[ HTTP Client / Browser ]
           │
           ▼
[ Supabase PostgREST ]
           │ (authenticator role performs SET LOCAL ROLE)
           ├───────────────────────────────┬───────────────────────────────┐
           ▼                               ▼                               ▼
       Role: anon                 Role: authenticated              Role: service_role
   (rolbypassrls = False)        (rolbypassrls = False)          (rolbypassrls = True)
           │                               │                               │
   ┌───────┴───────────────────────┬───────┴───────────────────────┐       │
   ▼                               ▼                               ▼       ▼
[ SQL Grants Check ]       [ SQL Grants Check ]                    [ Bypasses RLS ]
   ├── If REVOKED:            ├── If REVOKED:                      [ Full Admin ]
   │   HTTP 403 Forbidden     │   HTTP 403 Forbidden                       │
   │                          │                                            │
   └── If Granted + RLS:      └── If Granted + RLS:                        │
       Default-Deny               Default-Deny                             │
       (HTTP 200, [])             (HTTP 200, [])                           │
```

### Response Code Realities:
- When privileges are revoked at the SQL table level, PostgREST returns **`403 Forbidden` / `401 Unauthorized`** ("permission denied for table ...") rather than `200 OK` with an empty array `[]`.
- This provides stronger security than RLS alone, as unauthorized requests are rejected at the table grant layer before reaching the row-level policy evaluation engine.

---

## 8. Backend Impact Analysis

| Proposed Permission Removal | Target Objects | Backend Application Impact | Impact Classification |
| :--- | :--- | :--- | :--- |
| **`REVOKE ALL ON TABLE ... FROM anon, authenticated`** | All 8 tables | None. Application connects exclusively as `postgres`. | **SAFE FOR CURRENT BACKEND** |
| **`REVOKE ALL ON SEQUENCE ... FROM anon, authenticated`** | Both sequences | None. Application executes `nextval()` as `postgres`. | **SAFE FOR CURRENT BACKEND** |
| **`ALTER DEFAULT PRIVILEGES ... REVOKE ALL ON TABLES`** | Future tables | None. Application connects as `postgres`. | **SAFE FOR CURRENT BACKEND** |
| **`ALTER DEFAULT PRIVILEGES ... REVOKE ALL ON SEQUENCES`**| Future sequences | None. Application connects as `postgres`. | **SAFE FOR CURRENT BACKEND** |

**Verification:** Source code search across the entire backend confirmed zero imports of `create_client` or Supabase SDK, zero calls to PostgREST endpoints, and zero connections using roles other than `postgres`.

---

## 9. Recommended Execution Sequence: Unified Atomic Upgrade

Alembic wraps the entire migration run inside `with context.begin_transaction():` and PostgreSQL natively supports transactional DDL.

### Architectural Recommendation:
Rather than applying Step 3B (RLS enablement) and Step 3C (privilege hardening) in separate fragmented runs:
1. **Prepare Step 3C Migration File:** Author the Step 3C migration script `f3a9082b1c42_harden_least_privilege_grants.py` with `down_revision = 'e4b19082a5c1'`.
2. **Execute Unified Upgrade:** Invoke `python -m alembic -c backend/alembic.ini upgrade head`.
   - Revisions applied in sequence: `c742f9a1e0b5` $\rightarrow$ `e4b19082a5c1` $\rightarrow$ `Step 3C`.
   - **All three revisions execute within a SINGLE ATOMIC TRANSACTION.**
   - **Zero Window of Exposure:** Tables are created, standard RLS is enabled, and default privileges are hardened simultaneously.
   - If any statement fails, the entire transaction rolls back cleanly to `1273f18b72a2`.

---

## 10. Git Preservation Audit

- **Active Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`
- **Staged Changes:** 0
- **Modified Tracked Files:** 1 (`backend/app/models/__init__.py`, preserved from Phase 4)
- **Modified Untracked Files:** 0
- **Untracked Historical Artifacts:** All 20 previously untracked files/directories remain intact.
- **New Deliverables Created:** Only the two Step 3C.0 reports. Zero migrations were modified or created.

---

## 11. Deliverables Generated

- **Comprehensive Audit Report (Markdown):**  
  [supabase_rls_step3c0_privilege_hardening_design.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c0_privilege_hardening_design.md)
- **Structured Audit Report (JSON):**  
  [supabase_rls_step3c0_privilege_hardening_design.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/supabase_rls_step3c0_privilege_hardening_design.json)

---

## 12. Final Verdict

### Verdict: **`APPROVED FOR STEP 3C MIGRATION PREPARATION`**

### Verdict Justification:
1. The baseline live database revision is confirmed at `1273f18b72a2`.
2. The complete sequence and table inventories have been verified via live catalog inspection.
3. The TRUNCATE and default ACL vulnerabilities have been addressed in the proposed design.
4. The proposed revocations have been confirmed 100% non-breaking for the backend application.
5. The unified atomic upgrade strategy guarantees transactional safety with zero window of exposure.

*The engineering team is authorized to proceed to Step 3C migration authoring upon request. No live database changes have been executed.*
