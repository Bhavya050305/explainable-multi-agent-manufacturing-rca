"""initial_tables

Revision ID: 1273f18b72a2
Revises:
Create Date: 2026-11-05 17:09:33.711271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1273f18b72a2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. machines
    op.create_table(
        'machines',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('criticality', sa.Integer(), nullable=False),
        sa.Column('production_impact', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_machines_id'), 'machines', ['id'], unique=False)

    # 2. sensor_readings
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('machine_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('vibration', sa.Float(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('pressure', sa.Float(), nullable=False),
        sa.Column('current', sa.Float(), nullable=False),
        sa.Column('rpm', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sensor_machine_time', 'sensor_readings', ['machine_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_sensor_readings_machine_id'), 'sensor_readings', ['machine_id'], unique=False)
    op.create_index(op.f('ix_sensor_readings_timestamp'), 'sensor_readings', ['timestamp'], unique=False)

    # 3. maintenance_history
    op.create_table(
        'maintenance_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('machine_id', sa.String(length=50), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('issue', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_history_date'), 'maintenance_history', ['date'], unique=False)
    op.create_index(op.f('ix_maintenance_history_machine_id'), 'maintenance_history', ['machine_id'], unique=False)

    # 4. alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('machine_id', sa.String(length=50), nullable=False),
        sa.Column('risk', sa.Float(), nullable=False),
        sa.Column('criticality', sa.Integer(), nullable=False),
        sa.Column('impact', sa.Integer(), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('shap_json', sa.JSON(), nullable=True),
        sa.Column('sensor_contrib_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_created_at'), 'alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index(op.f('ix_alerts_machine_id'), 'alerts', ['machine_id'], unique=False)
    op.create_index(op.f('ix_alerts_priority_score'), 'alerts', ['priority_score'], unique=False)
    op.create_index(op.f('ix_alerts_status'), 'alerts', ['status'], unique=False)

    # 5. tickets
    op.create_table(
        'tickets',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('alert_id', sa.String(length=50), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('approval_status', sa.String(length=50), nullable=False),
        sa.Column('approved_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_id')
    )
    op.create_index(op.f('ix_tickets_created_at'), 'tickets', ['created_at'], unique=False)
    op.create_index(op.f('ix_tickets_id'), 'tickets', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('tickets')
    op.drop_table('alerts')
    op.drop_table('maintenance_history')
    op.drop_table('sensor_readings')
    op.drop_table('machines')
