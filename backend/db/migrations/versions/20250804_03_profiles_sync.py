"""connector profiles and sync runs

Revision ID: 20250804_03
Revises: 20250804_02
Create Date: 2025-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20250804_03"
down_revision = "20250804_02"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "connectorprofile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("connector_config", postgresql.JSONB(), nullable=True),
        sa.Column("schedule_cron", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "syncrun",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connectorprofile.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("records_synced", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("syncrun")
    op.drop_table("connectorprofile") 