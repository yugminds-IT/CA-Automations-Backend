"""add_org_id_to_clients_table

Revision ID: 49e900444883
Revises: 0ff7cdc6a718
Create Date: 2025-12-16 20:15:46.426706

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49e900444883'
down_revision = '0ff7cdc6a718'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add org_id column to clients table (nullable first for existing data)
    op.add_column('clients', sa.Column('org_id', sa.Integer(), nullable=True))
    
    # For existing clients with user_id, set org_id from the user's org_id
    op.execute("""
        UPDATE clients 
        SET org_id = (
            SELECT org_id 
            FROM users 
            WHERE users.id = clients.user_id
        )
        WHERE clients.user_id IS NOT NULL
    """)
    
    # For clients without user_id, set org_id to the first organization
    # (This is a fallback - ideally these should be assigned to the correct org)
    op.execute("""
        UPDATE clients 
        SET org_id = (SELECT id FROM organizations ORDER BY id LIMIT 1)
        WHERE clients.org_id IS NULL
        AND EXISTS (SELECT 1 FROM organizations)
    """)
    
    # Delete clients that still have NULL org_id (no organizations exist)
    op.execute("""
        DELETE FROM clients WHERE org_id IS NULL
    """)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_clients_org_id',
        'clients', 'organizations',
        ['org_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index
    op.create_index(op.f('ix_clients_org_id'), 'clients', ['org_id'], unique=False)
    
    # Now make org_id NOT NULL (all clients should have org_id now)
    op.alter_column('clients', 'org_id', nullable=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_clients_org_id'), table_name='clients')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_clients_org_id', 'clients', type_='foreignkey')
    
    # Drop org_id column
    op.drop_column('clients', 'org_id')

