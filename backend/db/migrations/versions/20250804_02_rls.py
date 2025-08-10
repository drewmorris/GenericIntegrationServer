"""enable RLS and org isolation

Revision ID: 20250804_02
Revises: 20250804_01
Create Date: 2025-08-04
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250804_02"
down_revision = "20250804_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # enable RLS on usertoken and user tables
    op.execute('ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'CREATE POLICY org_isolation ON "user" USING (organization_id = current_setting(\'app.current_org\')::uuid);'
    )

    op.execute("ALTER TABLE usertoken ENABLE ROW LEVEL SECURITY;")
    op.execute(
        'CREATE POLICY org_isolation ON usertoken USING (user_id IN (SELECT id FROM "user" WHERE organization_id = current_setting(\'app.current_org\')::uuid));'
    )

def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS org_isolation ON "user";')
    op.execute("DROP POLICY IF EXISTS org_isolation ON usertoken;")
    op.execute("ALTER TABLE usertoken DISABLE ROW LEVEL SECURITY;")
    op.execute('ALTER TABLE "user" DISABLE ROW LEVEL SECURITY;') 