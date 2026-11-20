"""harden least privilege grants on public tables and sequences

Revision ID: f3a9082b1c42
Revises: e4b19082a5c1
Create Date: 2026-11-18 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3a9082b1c42'
down_revision: Union[str, None] = 'e4b19082a5c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Explicit, schema-qualified target tables (8 tables total:
# 6 domain/versioning tables + 2 ticket proposal tables from c742f9a1e0b5)
TARGET_TABLES: list[str] = [
    "public.machines",
    "public.sensor_readings",
    "public.alembic_version",
    "public.maintenance_history",
    "public.alerts",
    "public.tickets",
    "public.ticket_proposals",
    "public.consumed_tokens",
]

# Explicit, schema-qualified target sequences (2 sequences in public schema)
TARGET_SEQUENCES: list[str] = [
    "public.sensor_readings_id_seq",
    "public.maintenance_history_id_seq",
]


def upgrade() -> None:
    """
    Harden database-level permissions by removing broad privileges from Supabase
    API roles (anon, authenticated) and preventing future default privilege inheritance.

    Security Hardening Scope:
    1. Revoke all table-level privileges (SELECT, INSERT, UPDATE, DELETE, TRUNCATE,
       REFERENCES, TRIGGER, MAINTAIN) from 'anon' and 'authenticated' across all 8 tables.
       This explicitly eliminates the TRUNCATE vulnerability that Row Level Security
       does not protect against.
    2. Revoke all sequence privileges (USAGE, SELECT, UPDATE) from 'anon' and 'authenticated'
       on both public sequences, preventing sequence enumeration or exhaustion.
    3. Alter future default table privileges for objects created by 'postgres' in schema
       'public' to revoke ALL from 'anon' and 'authenticated'.
    4. Alter future default sequence privileges for objects created by 'postgres' in schema
       'public' to revoke ALL from 'anon' and 'authenticated'.

    Invariants & Compatibility:
    - Zero privileges are revoked from 'postgres' or 'service_role'.
    - Table ownership and sequence ownership remain unchanged (postgres).
    - The backend application connects as 'postgres' via SQLAlchemy over TCP,
      guaranteeing zero operational disruption.
    """
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
