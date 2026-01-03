"""add_designation_to_directors

Revision ID: 15a133deb77a
Revises: 49e900444883
Create Date: 2025-12-17 18:42:58.401768

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15a133deb77a'
down_revision = '49e900444883'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("directors", sa.Column("designation", sa.String(), nullable=True))
    # Backfill designation from legacy 'resignation' column if present
    op.execute(
        """
        UPDATE directors
        SET designation = resignation
        WHERE designation IS NULL AND resignation IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("directors", "designation")

