from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = '20250810_05_credentials'
down_revision = '20250810_04_targets'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'credential',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('connector_name', sa.String(), nullable=False),
        sa.Column('provider_key', sa.String(), nullable=False),
        sa.Column('credential_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_unique_constraint('uq_cred_org_user_name_key', 'credential', ['organization_id', 'user_id', 'connector_name', 'provider_key'])


def downgrade() -> None:
    op.drop_constraint('uq_cred_org_user_name_key', 'credential', type_='unique')
    op.drop_table('credential') 