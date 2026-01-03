"""add_upload_files_table

Revision ID: 236cec118dad
Revises: c6f9c0812eed
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '236cec118dad'
down_revision = '8d15d4ee9657'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create upload_files table
    op.create_table('upload_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('stored_filename', sa.String(length=500), nullable=False),
    sa.Column('file_type', sa.String(length=100), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(length=1000), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_upload_files_id'), 'upload_files', ['id'], unique=False)
    op.create_index(op.f('ix_upload_files_stored_filename'), 'upload_files', ['stored_filename'], unique=True)
    op.create_index(op.f('ix_upload_files_user_id'), 'upload_files', ['user_id'], unique=False)
    op.create_index(op.f('ix_upload_files_organization_id'), 'upload_files', ['organization_id'], unique=False)
    op.create_index(op.f('ix_upload_files_uploaded_at'), 'upload_files', ['uploaded_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_upload_files_uploaded_at'), table_name='upload_files')
    op.drop_index(op.f('ix_upload_files_organization_id'), table_name='upload_files')
    op.drop_index(op.f('ix_upload_files_user_id'), table_name='upload_files')
    op.drop_index(op.f('ix_upload_files_stored_filename'), table_name='upload_files')
    op.drop_index(op.f('ix_upload_files_id'), table_name='upload_files')
    op.drop_table('upload_files')
