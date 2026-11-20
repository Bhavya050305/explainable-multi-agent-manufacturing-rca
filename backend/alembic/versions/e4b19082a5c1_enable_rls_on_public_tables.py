"""enable standard rls on eight public tables

Revision ID: e4b19082a5c1
Revises: c742f9a1e0b5
Create Date: 2026-11-18 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e4b19082a5c1'
down_revision: Union[str, None] = 'c742f9a1e0b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Explicit, fixed schema-qualified target tables (8 tables total:
# 6 original domain/versioning tables + 2 ticket proposal tables from c742f9a1e0b5)
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


def upgrade() -> None:
    """
    Enable standard Row Level Security (RLS) on all eight public tables in Supabase:
    1. public.machines
    2. public.sensor_readings
    3. public.alembic_version
    4. public.maintenance_history
    5. public.alerts
    6. public.tickets
    7. public.ticket_proposals
    8. public.consumed_tokens

    Security Guarantees:
    - Standard RLS is enabled; FORCE ROW LEVEL SECURITY remains strictly disabled.
    - No permissive or deny-all RLS policies are created; PostgreSQL default-deny applies
      to non-bypass roles (anon, authenticated) through the PostgREST Data API.
    - Zero GRANT or REVOKE operations are executed; existing grant baseline is preserved.
    - The backend connects as 'postgres' which holds rolbypassrls=True and owns all eight tables,
      guaranteeing zero disruption to direct backend queries.
    """
    for table_name in TARGET_TABLES:
        op.execute(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    """
    Disable standard Row Level Security on all eight public tables in reverse order:
    1. public.consumed_tokens
    2. public.ticket_proposals
    3. public.tickets
    4. public.alerts
    5. public.maintenance_history
    6. public.alembic_version
    7. public.sensor_readings
    8. public.machines

    SECURITY WARNING:
    Downgrading disables RLS and reopens the previous RLS-disabled exposure for roles
    with existing table privileges (anon, authenticated). It must only be executed
    with explicit authorization and a security review.

    Invariants:
    - Zero GRANT or REVOKE operations are executed.
    - No broad permissions are restored (specifically prohibiting GRANT ALL TO anon/authenticated).
    - FORCE ROW LEVEL SECURITY is not used.
    - No policies are created or dropped.
    """
    for table_name in reversed(TARGET_TABLES):
        op.execute(f"ALTER TABLE public.{table_name} DISABLE ROW LEVEL SECURITY;")
