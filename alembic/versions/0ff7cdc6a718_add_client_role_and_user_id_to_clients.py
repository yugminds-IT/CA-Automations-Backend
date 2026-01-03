"""add_client_role_and_user_id_to_clients

Revision ID: 0ff7cdc6a718
Revises: 1690096c1980
Create Date: 2025-12-16 16:23:51.430321

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ff7cdc6a718'
down_revision = '1690096c1980'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: UserRole enum uses native_enum=False, so it's stored as VARCHAR
    # No need to modify PostgreSQL enum type - the application code handles enum validation
    # The CLIENT role is already added to the UserRole enum in the model
    
    # Add user_id column to clients table
    op.add_column('clients', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_clients_user_id',
        'clients', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for user_id
    op.create_index(op.f('ix_clients_user_id'), 'clients', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_clients_user_id'), table_name='clients')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_clients_user_id', 'clients', type_='foreignkey')
    
    # Drop user_id column
    op.drop_column('clients', 'user_id')
    
    # Note: UserRole enum uses native_enum=False (VARCHAR), so no enum type modification needed

