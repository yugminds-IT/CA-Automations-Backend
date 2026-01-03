"""add_encrypted_plain_password_to_users

Revision ID: 8d15d4ee9657
Revises: c6f9c0812eed
Create Date: 2026-01-02 15:21:15.849499

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d15d4ee9657'
down_revision = 'c6f9c0812eed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add encrypted_plain_password column to users table
    # This stores the encrypted plain password for client accounts
    # It's cleared when the client changes their password
    op.add_column('users', sa.Column('encrypted_plain_password', sa.String(), nullable=True))


def downgrade() -> None:
    # Drop encrypted_plain_password column
    op.drop_column('users', 'encrypted_plain_password')

