"""ticket_proposals and consumed_tokens tables

Revision ID: c742f9a1e0b5
Revises: 1273f18b72a2
Create Date: 2026-11-16 21:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c742f9a1e0b5'
down_revision: Union[str, None] = '1273f18b72a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ticket_proposals
    op.create_table(
        'ticket_proposals',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('machine_id', sa.String(length=50), nullable=False),
        sa.Column('alert_id', sa.String(length=50), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('token_id', sa.String(length=100), nullable=True),
        sa.Column('ticket_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id']),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id'),
        sa.UniqueConstraint('ticket_id')
    )
    op.create_index(op.f('ix_ticket_proposals_id'), 'ticket_proposals', ['id'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_machine_id'), 'ticket_proposals', ['machine_id'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_alert_id'), 'ticket_proposals', ['alert_id'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_payload_hash'), 'ticket_proposals', ['payload_hash'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_status'), 'ticket_proposals', ['status'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_created_at'), 'ticket_proposals', ['created_at'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_expires_at'), 'ticket_proposals', ['expires_at'], unique=False)
    op.create_index(op.f('ix_ticket_proposals_token_id'), 'ticket_proposals', ['token_id'], unique=True)
    op.create_index(op.f('ix_ticket_proposals_ticket_id'), 'ticket_proposals', ['ticket_id'], unique=True)

    # 2. consumed_tokens
    op.create_table(
        'consumed_tokens',
        sa.Column('jti', sa.String(length=100), nullable=False),
        sa.Column('proposal_id', sa.String(length=50), nullable=False),
        sa.Column('approver_id', sa.String(length=100), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=False),
        sa.Column('token_exp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['ticket_proposals.id']),
        sa.PrimaryKeyConstraint('jti')
    )
    op.create_index(op.f('ix_consumed_tokens_jti'), 'consumed_tokens', ['jti'], unique=False)
    op.create_index(op.f('ix_consumed_tokens_proposal_id'), 'consumed_tokens', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_consumed_tokens_consumed_at'), 'consumed_tokens', ['consumed_at'], unique=False)


def downgrade() -> None:
    op.drop_table('consumed_tokens')
    op.drop_table('ticket_proposals')
