from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250810_06_profile_checkpoint'
down_revision = '20250810_05_credentials'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('connectorprofile', sa.Column('checkpoint_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('connectorprofile', 'checkpoint_json') 