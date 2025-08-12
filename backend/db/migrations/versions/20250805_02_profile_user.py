"""add user_id to connectorprofile

Revision ID: 20250805_02
Revises: 20250805_01
Create Date: 2025-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20250805_02"
down_revision = "20250805_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("connectorprofile", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key('fk_connectorprofile_user', "connectorprofile", "user", ["user_id"], ["id"])  # type: ignore[call-arg]
    # optional credential_id for connector credentials linkage
    op.add_column("connectorprofile", sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("connectorprofile", "credential_id")
    op.drop_constraint('fk_connectorprofile_user', "connectorprofile", type_="foreignkey")
    op.drop_column("connectorprofile", "user_id") 