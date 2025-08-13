"""enhance_credential_management_and_audit

Revision ID: 20250810_07
Revises: 20250810_06_profile_checkpoint
Create Date: 2025-08-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250810_07'
down_revision = '20250810_06_profile_checkpoint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to credential table
    op.add_column('credential', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.add_column('credential', sa.Column('last_refreshed_at', sa.DateTime(), nullable=True))
    op.add_column('credential', sa.Column('refresh_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('credential', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('credential', sa.Column('encryption_key_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('credential', sa.Column('last_used_at', sa.DateTime(), nullable=True))
    op.add_column('credential', sa.Column('created_by_ip', sa.String(), nullable=True))
    op.add_column('credential', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))

    # Create credential_audit_log table
    op.create_table('credential_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credential_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['credential_id'], ['credential.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_audit_credential_time', 'credential_audit_log', ['credential_id', 'created_at'])
    op.create_index('ix_audit_org_time', 'credential_audit_log', ['organization_id', 'created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_org_time', table_name='credential_audit_log')
    op.drop_index('ix_audit_credential_time', table_name='credential_audit_log')
    
    # Drop audit log table
    op.drop_table('credential_audit_log')
    
    # Remove columns from credential table
    op.drop_column('credential', 'updated_at')
    op.drop_column('credential', 'created_by_ip')
    op.drop_column('credential', 'last_used_at')
    op.drop_column('credential', 'encryption_key_version')
    op.drop_column('credential', 'status')
    op.drop_column('credential', 'refresh_attempts')
    op.drop_column('credential', 'last_refreshed_at')
    op.drop_column('credential', 'expires_at') 