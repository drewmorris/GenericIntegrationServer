"""add_multi_tenant_integration_server

Revision ID: 20250901193400
Revises: zzz_placeholder_will_update
Create Date: 2025-09-01 19:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '20250901193400'
down_revision = "da42808081e3"  # Latest LegacyCode migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add multi-tenant integration server support
    
    Adds:
    1. DestinationTarget table for routing documents to external destinations
    2. organization_id and destination_target_id columns to ConnectorCredentialPair
    """
    
    # 1. Create DestinationTarget table
    op.create_table(
        'destinationtarget',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('config', sa.dialects.postgresql.JSONB(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Add unique constraint for org/user/name combination
    op.create_unique_constraint(
        'uq_target_org_user_name',
        'destinationtarget',
        ['organization_id', 'user_id', 'name']
    )
    
    # Add indexes for efficient querying
    op.create_index(
        'idx_destination_target_org_id',
        'destinationtarget',
        ['organization_id'],
    )
    op.create_index(
        'idx_destination_target_user_id', 
        'destinationtarget',
        ['user_id'],
    )
    
    # 2. Add multi-tenant columns to ConnectorCredentialPair
    op.add_column(
        'connector_credential_pair',
        sa.Column(
            'organization_id',
            UUID(as_uuid=True),
            sa.ForeignKey('user.id'),
            nullable=True,  # Allow existing CC-Pairs without organizations initially
            index=True
        )
    )
    
    op.add_column(
        'connector_credential_pair',
        sa.Column(
            'destination_target_id',
            UUID(as_uuid=True),
            sa.ForeignKey('destinationtarget.id'),
            nullable=True,  # Allow existing CC-Pairs without destinations initially
            index=True
        )
    )


def downgrade() -> None:
    """Remove multi-tenant integration server support"""
    
    # Remove columns from ConnectorCredentialPair (indexes are dropped automatically)
    op.drop_column('connector_credential_pair', 'destination_target_id')
    op.drop_column('connector_credential_pair', 'organization_id')
    
    # Drop DestinationTarget table (constraints and indexes are dropped automatically)  
    op.drop_table('destinationtarget')
