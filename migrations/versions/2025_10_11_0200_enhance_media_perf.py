"""enhance media support and performance optimization

Revision ID: 2025_10_11_0200
Revises: 5830422f9b77
Create Date: 2025-10-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '2025_10_11_0200'
down_revision = '5830422f9b77'
branch_labels = None
depends_on = None


def upgrade():
    # Create ebook_metadata table
    op.create_table(
        'ebook_metadata',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('file_path', sa.String(512), nullable=False, index=True),
        sa.Column('file_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('file_type', sa.String(10), nullable=False),  # SQLite doesn't have ENUM, use String
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('total_pages', sa.Integer, nullable=True),
        sa.Column('is_encrypted', sa.Boolean, nullable=False, default=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_accessed', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.user_id'), nullable=False),
        sa.CheckConstraint('file_size <= 52428800', name='file_size_limit')
    )
    op.create_index('idx_ebook_user', 'ebook_metadata', ['user_id'])

    # Create performance_snapshots table
    op.create_table(
        'performance_snapshots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False, index=True),  # FK check added separately if terminal_session table exists
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        sa.Column('cpu_percent', sa.Float, nullable=False),
        sa.Column('memory_mb', sa.Float, nullable=False),
        sa.Column('active_websockets', sa.Integer, nullable=False),
        sa.Column('terminal_updates_per_sec', sa.Float, nullable=False, default=0, server_default='0'),
        sa.Column('client_fps', sa.Float, nullable=True),
        sa.Column('client_memory_mb', sa.Float, nullable=True),
        sa.CheckConstraint('cpu_percent >= 0 AND cpu_percent <= 100', name='cpu_range'),
        sa.CheckConstraint('memory_mb > 0', name='memory_positive')
    )
    op.create_index('idx_perf_session_time', 'performance_snapshots', ['session_id', 'timestamp'])

    # Extend user_profiles table
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('show_performance_metrics', sa.Boolean, nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('performance_metric_refresh_interval', sa.Integer, nullable=False, server_default='5000'))


def downgrade():
    # Drop performance_snapshots table
    op.drop_index('idx_perf_session_time', table_name='performance_snapshots')
    op.drop_table('performance_snapshots')

    # Drop ebook_metadata table
    op.drop_index('idx_ebook_user', table_name='ebook_metadata')
    op.drop_table('ebook_metadata')

    # Remove columns from user_profiles table
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.drop_column('performance_metric_refresh_interval')
        batch_op.drop_column('show_performance_metrics')
