"""add_cc_pair_performance_indexes

Revision ID: 4821d79eafac
Revises: 27da2ea43768
Create Date: 2025-08-21 05:20:15.195768

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4821d79eafac'
down_revision = '27da2ea43768'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for CC-Pair architecture queries"""
    
    # Connector table indexes
    # For filtering by source and ordering by time_created
    op.create_index(
        'idx_connector_source', 
        'connector', 
        ['source'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_connector_time_created', 
        'connector', 
        ['time_created'], 
        if_not_exists=True
    )
    
    # ConnectorCredentialPair table indexes
    # For foreign key lookups and multi-tenant queries
    op.create_index(
        'idx_cc_pair_connector_id', 
        'connectorcredentialpair', 
        ['connector_id'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_cc_pair_organization_id', 
        'connectorcredentialpair', 
        ['organization_id'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_cc_pair_status', 
        'connectorcredentialpair', 
        ['status'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_cc_pair_time_created', 
        'connectorcredentialpair', 
        ['time_created'], 
        if_not_exists=True
    )
    # Composite index for scheduler queries (active pairs by org)
    op.create_index(
        'idx_cc_pair_status_org_time', 
        'connectorcredentialpair', 
        ['status', 'organization_id', 'last_successful_index_time'], 
        if_not_exists=True
    )
    
    # IndexAttempt table indexes
    # For CC-Pair relationship and status filtering
    op.create_index(
        'idx_index_attempt_cc_pair_id', 
        'indexattempt', 
        ['connector_credential_pair_id'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_index_attempt_status', 
        'indexattempt', 
        ['status'], 
        if_not_exists=True
    )
    op.create_index(
        'idx_index_attempt_time_created', 
        'indexattempt', 
        ['time_created'], 
        if_not_exists=True
    )
    # Composite index for finding latest attempts per CC-Pair
    op.create_index(
        'idx_index_attempt_cc_pair_time', 
        'indexattempt', 
        ['connector_credential_pair_id', 'time_created'], 
        if_not_exists=True
    )
    # Index for Celery task coordination
    op.create_index(
        'idx_index_attempt_celery_task_id', 
        'indexattempt', 
        ['celery_task_id'], 
        if_not_exists=True
    )
    # Composite index for active attempts monitoring
    op.create_index(
        'idx_index_attempt_status_cc_pair', 
        'indexattempt', 
        ['status', 'connector_credential_pair_id'], 
        if_not_exists=True
    )


def downgrade() -> None:
    """Remove performance indexes for CC-Pair architecture"""
    
    # Drop IndexAttempt indexes
    op.drop_index('idx_index_attempt_status_cc_pair', 'indexattempt', if_exists=True)
    op.drop_index('idx_index_attempt_celery_task_id', 'indexattempt', if_exists=True)
    op.drop_index('idx_index_attempt_cc_pair_time', 'indexattempt', if_exists=True)
    op.drop_index('idx_index_attempt_time_created', 'indexattempt', if_exists=True)
    op.drop_index('idx_index_attempt_status', 'indexattempt', if_exists=True)
    op.drop_index('idx_index_attempt_cc_pair_id', 'indexattempt', if_exists=True)
    
    # Drop ConnectorCredentialPair indexes
    op.drop_index('idx_cc_pair_status_org_time', 'connectorcredentialpair', if_exists=True)
    op.drop_index('idx_cc_pair_time_created', 'connectorcredentialpair', if_exists=True)
    op.drop_index('idx_cc_pair_status', 'connectorcredentialpair', if_exists=True)
    op.drop_index('idx_cc_pair_organization_id', 'connectorcredentialpair', if_exists=True)
    op.drop_index('idx_cc_pair_connector_id', 'connectorcredentialpair', if_exists=True)
    
    # Drop Connector indexes
    op.drop_index('idx_connector_time_created', 'connector', if_exists=True)
    op.drop_index('idx_connector_source', 'connector', if_exists=True)
