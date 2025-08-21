"""add_destination_to_cc_pairs

Revision ID: 361cbe5331d0
Revises: 4821d79eafac
Create Date: 2025-08-21 12:50:48.907421

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '361cbe5331d0'
down_revision = '4821d79eafac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add destination target reference to ConnectorCredentialPair for 1:1 source-destination pairing"""
    
    # Add destination_target_id column to connectorcredentialpair table
    op.add_column(
        'connectorcredentialpair',
        sa.Column(
            'destination_target_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('destinationtarget.id'),
            nullable=True  # Allow existing CC-Pairs to exist without destinations initially
        )
    )
    
    # Add index for destination target lookups
    op.create_index(
        'idx_cc_pair_destination_target_id',
        'connectorcredentialpair',
        ['destination_target_id'],
        if_not_exists=True
    )


def downgrade() -> None:
    """Remove destination target reference from ConnectorCredentialPair"""
    
    # Drop index first
    op.drop_index('idx_cc_pair_destination_target_id', 'connectorcredentialpair', if_exists=True)
    
    # Drop destination_target_id column
    op.drop_column('connectorcredentialpair', 'destination_target_id')
