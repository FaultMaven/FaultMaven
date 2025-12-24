"""Initial schema with proper foreign keys

Revision ID: 20241221_0000
Revises:
Create Date: 2024-12-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241221_0000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables with proper FKs."""

    # Auth module tables
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.String(512)),
        sa.Column('roles', sa.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('user_metadata', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('last_login_at', sa.DateTime),
    )

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('token', sa.Text, nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('revoked_at', sa.DateTime),
    )

    # Session module tables
    op.create_table(
        'session_audits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('data', sa.JSON, nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_accessed_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('destroyed_at', sa.DateTime),
    )

    # Case module tables
    op.create_table(
        'cases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('status', sa.Enum('consulting', 'verifying', 'root_cause_analysis', 'resolved', 'closed', name='casestatus'), nullable=False, index=True),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'critical', name='casepriority'), nullable=False),
        sa.Column('context', sa.JSON, nullable=False),
        sa.Column('case_metadata', sa.JSON, nullable=False),
        sa.Column('tags', sa.JSON, nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('resolved_at', sa.DateTime),
        sa.Column('closed_at', sa.DateTime),
    )

    op.create_table(
        'hypotheses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float),
        sa.Column('validated', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('validation_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'solutions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('implementation_steps', sa.JSON, nullable=False),
        sa.Column('implemented', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('effectiveness', sa.Float),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('implemented_at', sa.DateTime),
    )

    op.create_table(
        'case_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('message_metadata', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Evidence module tables
    op.create_table(
        'evidence',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('uploaded_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('storage_path', sa.String(512), nullable=False),
        sa.Column('evidence_type', sa.Enum('log', 'screenshot', 'document', 'metric', 'code', 'configuration', 'other', name='evidencetype'), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('tags', sa.JSON, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
    )

    # Knowledge module tables
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('uploaded_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('document_type', sa.Enum('pdf', 'docx', 'txt', 'markdown', 'html', 'code', 'other', name='documenttype'), nullable=False),
        sa.Column('content', sa.Text),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('status', sa.Enum('pending', 'processing', 'indexed', 'failed', name='documentstatus'), nullable=False, index=True),
        sa.Column('storage_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('embedding_ids', sa.JSON, nullable=False),
        sa.Column('chunk_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('metadata', sa.JSON, nullable=False),
        sa.Column('tags', sa.JSON, nullable=False),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
        sa.Column('indexed_at', sa.DateTime),
        sa.Column('last_accessed_at', sa.DateTime),
    )

    op.create_table(
        'search_queries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('query_text', sa.Text, nullable=False),
        sa.Column('user_id', sa.String(36), index=True),
        sa.Column('result_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('top_result_ids', sa.JSON, nullable=False),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('created_at', sa.DateTime, nullable=False, index=True),
    )

    # Agent module tables
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), index=True),
        sa.Column('user_id', sa.String(36), index=True),
        sa.Column('status', sa.Enum('active', 'completed', 'abandoned', name='chatsessionstatus'), nullable=False),
        sa.Column('message_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Float),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime),
    )

    op.create_table(
        'llm_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), index=True),
        sa.Column('case_id', sa.String(36), index=True),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('prompt_preview', sa.Text),
        sa.Column('response_preview', sa.Text),
        sa.Column('prompt_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('cost', sa.Float),
        sa.Column('success', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False, index=True),
    )


def downgrade() -> None:
    """Downgrade schema - drop all tables."""

    # Drop in reverse order (respect FKs)
    op.drop_table('llm_requests')
    op.drop_table('chat_sessions')
    op.drop_table('search_queries')
    op.drop_table('documents')
    op.drop_table('evidence')
    op.drop_table('case_messages')
    op.drop_table('solutions')
    op.drop_table('hypotheses')
    op.drop_table('cases')
    op.drop_table('session_audits')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

    # Drop enums (PostgreSQL)
    sa.Enum(name='casestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='casepriority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='evidencetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='documenttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='documentstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='chatsessionstatus').drop(op.get_bind(), checkfirst=True)
