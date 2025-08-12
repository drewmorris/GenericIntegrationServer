from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20250810_04_targets'
down_revision = '20250805_02'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'destinationtarget',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_destinationtarget_org', 'destinationtarget', ['organization_id'])
    op.create_unique_constraint('uq_target_org_user_name', 'destinationtarget', ['organization_id', 'user_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_target_org_user_name', 'destinationtarget', type_='unique')
    op.drop_index('ix_destinationtarget_org', table_name='destinationtarget')
    op.drop_table('destinationtarget') 