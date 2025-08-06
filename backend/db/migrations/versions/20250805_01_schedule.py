"""add schedule fields

Revision ID: 20250805_01
Revises: 20250804_03
Create Date: 2025-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20250805_01"
down_revision = "20250804_03"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("connectorprofile", sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("connectorprofile", sa.Column("next_run_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("connectorprofile", "next_run_at")
    op.drop_column("connectorprofile", "interval_minutes") 