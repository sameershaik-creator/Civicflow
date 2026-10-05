"""Initial schema creation for users, complaints, and notifications

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Create users table
    if 'users' not in existing_tables:
        op.create_table(
            'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='citizen', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create complaints table
    if 'complaints' not in existing_tables:
        op.create_table(
            'complaints',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('image_url', sa.String(length=512), nullable=False),
            sa.Column('original_problem', sa.Text(), nullable=False),
            sa.Column('original_address', sa.String(length=512), nullable=True),
            sa.Column('original_latitude', sa.Float(), nullable=True),
            sa.Column('original_longitude', sa.Float(), nullable=True),
            sa.Column('ai_problem', sa.Text(), nullable=True),
            sa.Column('ai_address', sa.String(length=512), nullable=True),
            sa.Column('ai_summary', sa.Text(), nullable=True),
            sa.Column('final_problem', sa.Text(), nullable=True),
            sa.Column('final_address', sa.String(length=512), nullable=True),
            sa.Column('final_summary', sa.Text(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('place_id', sa.String(length=128), nullable=True),
            sa.Column('map_url', sa.String(length=512), nullable=True),
            sa.Column('location_status', sa.String(length=50), server_default='COORDINATES_ATTACHED', nullable=False),
            sa.Column('status', sa.String(length=30), server_default='DRAFT', nullable=False),
            sa.Column('admin_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_complaints_id'), 'complaints', ['id'], unique=False)
        op.create_index(op.f('ix_complaints_user_id'), 'complaints', ['user_id'], unique=False)
        op.create_index(op.f('ix_complaints_status'), 'complaints', ['status'], unique=False)
        op.create_index(op.f('ix_complaints_created_at'), 'complaints', ['created_at'], unique=False)
        op.create_index(op.f('ix_complaints_submitted_at'), 'complaints', ['submitted_at'], unique=False)

    # 3. Create notifications table
    if 'notifications' not in existing_tables:
        op.create_table(
            'notifications',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('complaint_id', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('is_read', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
        op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
        op.create_index(op.f('ix_notifications_complaint_id'), 'notifications', ['complaint_id'], unique=False)
        op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
        op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('complaints')
    op.drop_table('users')
