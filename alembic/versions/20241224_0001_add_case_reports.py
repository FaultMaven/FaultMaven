"""Add case_reports table and update case status enum

Revision ID: 20241224_0001
Revises: 20241221_0000
Create Date: 2024-12-24 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241224_0001'
down_revision: Union[str, None] = '20241221_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add case_reports table."""

    op.create_table(
        'case_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('report_type', sa.Enum('incident_report', 'runbook', 'post_mortem', name='reporttype'), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=False, server_default=''),
        sa.Column('format', sa.String(20), nullable=False, server_default='markdown'),
        # FIXED: Enum values must match ORM (pending/completed, not draft/ready)
        sa.Column('status', sa.Enum('pending', 'generating', 'completed', 'failed', name='reportstatus'), nullable=False, index=True),
        sa.Column('generation_time_ms', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_current', sa.Boolean, nullable=False, server_default='1', index=True),
        sa.Column('linked_to_closure', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('report_metadata', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('generated_at', sa.DateTime, nullable=True),
    )

    # Add index for finding current reports by type
    op.create_index(
        'ix_case_reports_case_type_current',
        'case_reports',
        ['case_id', 'report_type', 'is_current'],
    )


def downgrade() -> None:
    """Remove case_reports table."""
    op.drop_index('ix_case_reports_case_type_current', table_name='case_reports')
    op.drop_table('case_reports')

    # Drop enums (PostgreSQL)
    sa.Enum(name='reporttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reportstatus').drop(op.get_bind(), checkfirst=True)
