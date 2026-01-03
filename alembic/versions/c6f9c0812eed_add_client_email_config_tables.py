"""add_client_email_config_tables

Revision ID: c6f9c0812eed
Revises: 2c74e207a0c4
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6f9c0812eed'
down_revision = '2c74e207a0c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create client_email_configs table
    op.create_table('client_email_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('config_data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    op.create_index(op.f('ix_client_email_configs_client_id'), 'client_email_configs', ['client_id'], unique=True)
    op.create_index(op.f('ix_client_email_configs_id'), 'client_email_configs', ['id'], unique=False)
    
    # Create scheduled_emails table
    op.create_table('scheduled_emails',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('recipient_emails', sa.JSON(), nullable=False),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('scheduled_time', sa.Time(), nullable=False),
    sa.Column('scheduled_datetime', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
    sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('recurrence_end_date', sa.Date(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['template_id'], ['email_templates.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheduled_emails_client_id'), 'scheduled_emails', ['client_id'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_id'), 'scheduled_emails', ['id'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_is_recurring'), 'scheduled_emails', ['is_recurring'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_scheduled_date'), 'scheduled_emails', ['scheduled_date'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_scheduled_datetime'), 'scheduled_emails', ['scheduled_datetime'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_status'), 'scheduled_emails', ['status'], unique=False)
    op.create_index(op.f('ix_scheduled_emails_template_id'), 'scheduled_emails', ['template_id'], unique=False)
    
    # Create composite index for efficient querying of pending emails
    op.create_index('ix_scheduled_emails_status_datetime', 'scheduled_emails', ['status', 'scheduled_datetime'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_scheduled_emails_status_datetime', table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_template_id'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_status'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_scheduled_datetime'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_scheduled_date'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_is_recurring'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_id'), table_name='scheduled_emails')
    op.drop_index(op.f('ix_scheduled_emails_client_id'), table_name='scheduled_emails')
    op.drop_table('scheduled_emails')
    op.drop_index(op.f('ix_client_email_configs_id'), table_name='client_email_configs')
    op.drop_index(op.f('ix_client_email_configs_client_id'), table_name='client_email_configs')
    op.drop_table('client_email_configs')

