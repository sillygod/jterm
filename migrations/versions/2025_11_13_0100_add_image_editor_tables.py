"""add image editor tables

Revision ID: 2025_11_13_0100
Revises: 2025_10_11_0200
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_11_13_0100'
down_revision = '2025_10_11_0200'
branch_labels = None
depends_on = None


def upgrade():
    # Create image_sessions table
    op.create_table(
        'image_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('terminal_session_id', sa.String(255), nullable=False, index=True),
        sa.Column('image_source_type', sa.String(20), nullable=False),
        sa.Column('image_source_path', sa.String(1024), nullable=True),
        sa.Column('image_format', sa.String(10), nullable=False),
        sa.Column('image_width', sa.Integer, nullable=False),
        sa.Column('image_height', sa.Integer, nullable=False),
        sa.Column('image_size_bytes', sa.Integer, nullable=False),
        sa.Column('temp_file_path', sa.String(1024), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_modified_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('is_modified', sa.Boolean, nullable=False, server_default='0'),
        sa.CheckConstraint("image_source_type IN ('file', 'clipboard', 'url')", name='valid_source_type'),
        sa.CheckConstraint("image_format IN ('png', 'jpeg', 'gif', 'webp', 'bmp')", name='valid_format'),
        sa.CheckConstraint('image_width > 0 AND image_width <= 32767', name='valid_width'),
        sa.CheckConstraint('image_height > 0 AND image_height <= 32767', name='valid_height'),
        sa.CheckConstraint('image_size_bytes <= 52428800', name='file_size_limit')
    )
    op.create_index('idx_terminal_session', 'image_sessions', ['terminal_session_id'])
    op.create_index('idx_created_at', 'image_sessions', ['created_at'])

    # Create annotation_layers table
    op.create_table(
        'annotation_layers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('image_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('canvas_json', sa.Text, nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('last_updated', sa.DateTime, nullable=False, server_default=sa.func.now())
    )

    # Create edit_operations table
    op.create_table(
        'edit_operations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('image_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('operation_type', sa.String(20), nullable=False),
        sa.Column('canvas_snapshot', sa.Text, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('position', sa.Integer, nullable=False),
        sa.CheckConstraint("operation_type IN ('draw', 'text', 'shape', 'filter', 'crop', 'resize')", name='valid_operation_type'),
        sa.CheckConstraint('position >= 0 AND position < 50', name='valid_position')
    )
    op.create_index('idx_session_position', 'edit_operations', ['session_id', 'position'])

    # Create session_history table
    op.create_table(
        'session_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('terminal_session_id', sa.String(255), nullable=False),
        sa.Column('image_path', sa.String(1024), nullable=False),
        sa.Column('image_source_type', sa.String(20), nullable=False),
        sa.Column('thumbnail_path', sa.String(1024), nullable=True),
        sa.Column('last_viewed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('view_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_edited', sa.Boolean, nullable=False, server_default='0'),
        sa.CheckConstraint("image_source_type IN ('file', 'clipboard', 'url')", name='valid_history_source_type'),
        sa.UniqueConstraint('terminal_session_id', 'image_path', name='unique_terminal_image')
    )
    op.create_index('idx_terminal_last_viewed', 'session_history', ['terminal_session_id', 'last_viewed_at'])


def downgrade():
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('idx_terminal_last_viewed', table_name='session_history')
    op.drop_table('session_history')

    op.drop_index('idx_session_position', table_name='edit_operations')
    op.drop_table('edit_operations')

    op.drop_table('annotation_layers')

    op.drop_index('idx_created_at', table_name='image_sessions')
    op.drop_index('idx_terminal_session', table_name='image_sessions')
    op.drop_table('image_sessions')
